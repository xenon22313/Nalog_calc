import time
from collections import deque
from datetime import date
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.gzip import GZipMiddleware

from app import tax_rates
from app.articles import ARTICLES, get_article
from app.calculators import CALCULATORS, get_calculator
from app.config import settings

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(GZipMiddleware, minimum_size=500)


class CachedStaticFiles(StaticFiles):
    """Static files with long-lived cache headers; URLs carry ?v=<mtime>."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code in (200, 304):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


app.mount("/static", CachedStaticFiles(directory=STATIC_DIR), name="static")


# --- Templates ---------------------------------------------------------------

templates = Jinja2Templates(directory=BASE_DIR / "templates")

RU_MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def static_url(path: str) -> str:
    try:
        version = int((STATIC_DIR / path).stat().st_mtime)
    except FileNotFoundError:
        version = 0
    return f"/static/{path}?v={version}"


def format_money(value) -> str:
    value = Decimal(str(value))
    text = f"{value:,.0f}" if value == value.to_integral_value() else f"{value:,.2f}"
    return text.replace(",", "\u00a0").replace(".", ",") + "\u00a0₽"


def format_percent(value) -> str:
    text = format((Decimal(str(value)) * 100).normalize(), "f")
    return text.replace(".", ",") + "%"


def format_date(value: date) -> str:
    return f"{value.day} {RU_MONTHS[value.month - 1]} {value.year}"


templates.env.globals.update(static_url=static_url, settings=settings, calculators=CALCULATORS)
templates.env.filters.update(money=format_money, percent=format_percent, ru_date=format_date)


def absolute_url(path: str) -> str:
    return settings.SITE_URL + path


def breadcrumbs_ld(crumbs: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": absolute_url(url)}
            for i, (name, url) in enumerate(crumbs, start=1)
        ],
    }


def render(request: Request, template: str, *, title: str, description: str, path: str,
           status_code: int = 200, **context) -> HTMLResponse:
    context.update(title=title, description=description, canonical=absolute_url(path))
    return templates.TemplateResponse(request, template, context, status_code=status_code)


# --- Rate limit ----------------------------------------------------------------


class RateLimiter:
    """In-memory sliding window limiter. Works per process: run uvicorn with one worker
    or move limiting to nginx / Redis."""

    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self.hits: dict[str, deque] = {}

    def hit(self, key: str) -> bool:
        now = time.monotonic()
        if len(self.hits) > 10_000:
            self._purge(now)
        queue = self.hits.setdefault(key, deque())
        while queue and queue[0] <= now - self.window:
            queue.popleft()
        if len(queue) >= self.limit:
            return False
        queue.append(now)
        return True

    def _purge(self, now: float) -> None:
        stale = [k for k, q in self.hits.items() if not q or q[-1] <= now - self.window]
        for key in stale:
            del self.hits[key]

    def reset(self) -> None:
        self.hits.clear()


limiter = RateLimiter(settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW)


def client_ip(request: Request) -> str:
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # The rightmost address is the one added by our own proxy (nginx).
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


# --- Pages ---------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return render(
        request, "index.html",
        title=f"Онлайн-калькуляторы налогов для самозанятых, ИП и сотрудников — {settings.SITE_NAME}",
        description="Бесплатные онлайн-калькуляторы: налог самозанятых (НПД), УСН «Доходы» для ИП, зарплата на руки после НДФЛ.",
        path="/",
        articles=ARTICLES,
    )


@app.get("/kalkulyator-{slug}", response_class=HTMLResponse)
def calculator_page(request: Request, slug: str):
    calc = get_calculator(slug)
    if calc is None:
        raise HTTPException(status_code=404)

    example_input = calc.input_model(**calc.example)
    crumbs = [("Главная", "/"), (calc.h1, calc.url)]
    json_ld = [
        breadcrumbs_ld(crumbs),
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in calc.faq
            ],
        },
        {
            "@context": "https://schema.org",
            "@type": "WebApplication",
            "name": calc.h1,
            "url": absolute_url(calc.url),
            "description": calc.description,
            "applicationCategory": "FinanceApplication",
            "operatingSystem": "Any",
            "inLanguage": "ru",
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "RUB"},
        },
    ]
    return render(
        request, "calculator.html",
        title=calc.title, description=calc.description, path=calc.url,
        calc=calc,
        related=[c for c in map(get_calculator, calc.related) if c],
        rates=tax_rates.rates_for_template(),
        rates_updated=tax_rates.RATES_UPDATED,
        example_input=example_input,
        example_result=calc.func(example_input),
        crumbs=crumbs,
        json_ld=json_ld,
    )


@app.get("/stati/{slug}", response_class=HTMLResponse)
def article_page(request: Request, slug: str):
    article = get_article(slug)
    if article is None:
        raise HTTPException(status_code=404)

    crumbs = [("Главная", "/"), (article.h1, article.url)]
    json_ld = [
        breadcrumbs_ld(crumbs),
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": article.h1,
            "description": article.description,
            "datePublished": article.published.isoformat(),
            "dateModified": article.updated.isoformat(),
            "inLanguage": "ru",
            "mainEntityOfPage": absolute_url(article.url),
        },
    ]
    return render(
        request, "article.html",
        title=f"{article.title} — {settings.SITE_NAME}", description=article.description, path=article.url,
        article=article, crumbs=crumbs, json_ld=json_ld, og_type="article",
    )


@app.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    crumbs = [("Главная", "/"), ("Политика конфиденциальности", "/privacy")]
    return render(
        request, "privacy.html",
        title=f"Политика конфиденциальности — {settings.SITE_NAME}",
        description=f"Политика конфиденциальности сайта {settings.SITE_NAME}.",
        path="/privacy",
        crumbs=crumbs, json_ld=[breadcrumbs_ld(crumbs)],
    )


# --- API -----------------------------------------------------------------------

ERROR_MESSAGES = {
    "greater_than_equal": "Значение должно быть не меньше {ge}",
    "less_than_equal": "Значение должно быть не больше {le}",
    "missing": "Заполните поле",
}


def format_number(value) -> str:
    value = Decimal(str(value)).normalize()
    text = f"{value:,.0f}" if value == value.to_integral_value() else f"{value:,f}"
    return text.replace(",", "\u00a0").replace(".", ",")


def field_errors(exc: ValidationError) -> dict[str, str]:
    errors = {}
    for err in exc.errors():
        name = str(err["loc"][-1]) if err["loc"] else "_"
        template = ERROR_MESSAGES.get(err["type"], "Введите корректное число")
        ctx = {k: format_number(v) for k, v in (err.get("ctx") or {}).items() if k in ("ge", "le")}
        errors[name] = template.format(**ctx)
    return errors


@app.post("/api/calc/{slug}")
async def api_calc(slug: str, request: Request):
    if not limiter.hit(client_ip(request)):
        return JSONResponse(
            {"error": "Слишком много запросов. Попробуйте через минуту."},
            status_code=429,
            headers={"Retry-After": str(limiter.window)},
        )

    calc = get_calculator(slug)
    if calc is None:
        return JSONResponse({"error": "Калькулятор не найден"}, status_code=404)

    try:
        payload = await request.json()
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        return JSONResponse({"error": "Некорректный запрос"}, status_code=400)

    try:
        data = calc.input_model.model_validate(payload)
    except ValidationError as exc:
        return JSONResponse(
            {"error": "Проверьте введённые значения", "fields": field_errors(exc)},
            status_code=422,
        )

    result = calc.func(data)
    return {"result": {k: float(v) if isinstance(v, Decimal) else v for k, v in result.items()}}


# --- Technical SEO ---------------------------------------------------------------


@app.get("/sitemap.xml")
def sitemap():
    entries = [("/", None), ("/privacy", None)]
    entries += [(calc.url, tax_rates.RATES_UPDATED) for calc in CALCULATORS]
    entries += [(article.url, article.updated) for article in ARTICLES]

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, lastmod in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(absolute_url(path))}</loc>")
        if lastmod:
            lines.append(f"    <lastmod>{lastmod.isoformat()}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return Response("\n".join(lines), media_type="application/xml")


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        f"Sitemap: {absolute_url('/sitemap.xml')}\n"
    )


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and not request.url.path.startswith(("/api/", "/static/")):
        return render(
            request, "404.html",
            title=f"Страница не найдена — {settings.SITE_NAME}",
            description="Запрошенная страница не найдена.",
            path=request.url.path,
            status_code=404,
            noindex=True,
        )
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))
