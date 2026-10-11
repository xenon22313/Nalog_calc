# НалогКальк — онлайн-калькуляторы налогов

SEO-сайт с калькуляторами для самозанятых, ИП и сотрудников.
Стек: Python 3.12, FastAPI, Jinja2, uvicorn, Bootstrap 5 (локально, без CDN), чистый JS.

Формулы считаются **только на сервере** (`app/formulas.py`). Страница отправляет значения формы
в `POST /api/calc/<slug>` и выводит ответ. Все ставки и лимиты лежат в `app/tax_rates.py`.

## Запуск локально (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Linux / macOS:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

Сайт откроется на http://127.0.0.1:8000.

Тесты:

```powershell
.\.venv\Scripts\python -m pytest
```

## Структура

```
app/
  main.py          маршруты: страницы, API, sitemap.xml, robots.txt, 404
  config.py        настройки (домен, название, Метрика, РСЯ, rate limit)
  tax_rates.py     ВСЕ ставки, лимиты и дата их обновления
  formulas.py      формулы: pydantic-модель входа + функция расчёта
  calculators.py   реестр калькуляторов
  articles.py      реестр статей
  templates/
    base.html, index.html, calculator.html, article.html, privacy.html, 404.html
    calculators/   партиалы калькуляторов (поля формы, результат, «Как считается», пример)
    articles/      тексты статей
  static/
    vendor/bootstrap/   Bootstrap 5.3 (css + js)
    css/site.css
    js/calc.js          общий клиент для всех калькуляторов
tests/             pytest: эталонные кейсы формул и проверки страниц/API
deploy/            примеры nginx и systemd
```

## Ставки

Все значения в `app/tax_rates.py` — **заглушки** с пометкой
`TODO: проверить по официальному источнику (ФНС / закон)`. После проверки обновите
`RATES_UPDATED` — дата выводится на страницах калькуляторов и в `<lastmod>` в sitemap.

Эталонные кейсы в `tests/test_formulas.py` передают ставки в функции явно и не зависят от
`tax_rates.py`. Замените числа в них на проверенные.

## Как добавить калькулятор

Пример: калькулятор «Пени по налогу», slug `peni`.

**1. Формула** — в `app/formulas.py` добавьте модель входа и функцию:

```python
class PeniInput(BaseModel):
    debt: Decimal = Field(ge=0, le=MAX_INCOME)
    days: int = Field(ge=0, le=3650)


def calc_peni(data: PeniInput, rates: dict | None = None) -> dict:
    r = rates or tax_rates.PENI          # константы — в tax_rates.py
    peni = data.debt * to_decimal(r["daily_rate"]) * data.days
    return {"peni": money(peni)}         # деньги всегда через money()
```

Обязательно задавайте `ge`/`le` для числовых полей.

**2. Запись в реестр** — в `CALCULATORS` в `app/calculators.py`:

```python
Calculator(
    slug="peni",
    title="Калькулятор пеней по налогам онлайн",
    h1="Калькулятор пеней",
    description="...",
    keywords="...",
    template="calculators/peni.html",
    input_model=formulas.PeniInput,
    func=formulas.calc_peni,
    menu="Пени",
    short="Пени за просрочку уплаты налога.",
    example={"debt": 100000, "days": 30},
    faq=[("Вопрос?", "Ответ.")],
    related=["usn-dohody"],
),
```

**3. Партиал** — `app/templates/calculators/peni.html` с четырьмя макросами
(скопируйте любой существующий):

- `fields()` — поля формы; `name` поля = имя поля в pydantic-модели;
- `results()` — элементы `data-result="<ключ результата>"` и `data-format="money|percent"`,
  блоки `data-show-if="<булев ключ>"` показываются, только если значение истинно;
- `how()` — «Как считается» (ставки берите из `rates`, а не пишите числами);
- `example()` — «Пример расчёта» (`example_input` и `example_result` считаются автоматически
  из `example` в реестре).

Всё остальное подключится само: URL `/kalkulyator-peni`, API `/api/calc/peni`, меню,
главная, sitemap, JSON-LD, FAQ и перелинковка. JS писать не нужно. Добавьте эталонные
кейсы в `tests/test_formulas.py`.

## Статьи

Запись в `ARTICLES` в `app/articles.py` + файл с текстом в `app/templates/articles/`.
URL — `/stati/<slug>`, статья автоматически попадает в sitemap.

## Настройки

Задаются переменными окружения (см. `app/config.py`):

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `SITE_URL` | `http://127.0.0.1:8000` | домен для canonical, OG и sitemap |
| `SITE_NAME` | `НалогКальк` | название сайта |
| `CONTACT_EMAIL` | `info@example.ru` | почта на странице /privacy |
| `METRIKA_ID` | пусто (выкл.) | номер счётчика Яндекс.Метрики |
| `RSYA_BLOCK_ID` | пусто (выкл.) | ID блока РСЯ под калькулятором |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW` | `100` / `60` | лимит запросов к API на IP |
| `TRUST_PROXY_HEADERS` | `1` | брать IP клиента из `X-Forwarded-For` |

## Rate limit и IP клиента

`POST /api/calc/*` ограничен 100 запросами за 60 секунд на IP (ответ `429` с `Retry-After`).
Лимитер хранит состояние в памяти процесса, поэтому uvicorn запускается с `--workers 1`
(или перенесите лимит в nginx / Redis).

Сайт работает за nginx, поэтому IP клиента берётся из заголовка `X-Forwarded-For`
(крайний правый адрес — тот, что выставил наш nginx). Для этого:

- nginx перезаписывает заголовок: `proxy_set_header X-Forwarded-For $remote_addr;`
- uvicorn запускается с `--proxy-headers --forwarded-allow-ips=127.0.0.1`;
- в приложении `TRUST_PROXY_HEADERS=1` (по умолчанию).

Если uvicorn открыт в интернет напрямую, без nginx, выставьте `TRUST_PROXY_HEADERS=0`,
иначе клиент сможет подделать IP и обойти лимит. Дополнительно nginx ограничивает
`/api/calc/` через `limit_req` (см. `deploy/nginx.conf.example`).

## Деплой

1. Скопируйте проект в `/srv/calcsite`, создайте venv и установите зависимости.
2. `deploy/calcsite.service.example` → `/etc/systemd/system/calcsite.service`, задайте `SITE_URL`.
3. `deploy/nginx.conf.example` → `/etc/nginx/conf.d/calcsite.conf` (+ сниппет с proxy-заголовками).
4. `sudo systemctl enable --now calcsite && sudo nginx -s reload`.

## Дальнейшее развитие

- **Регистрация / БД (SQLite):** настройка `DATABASE_URL` уже заготовлена в `config.py`.
  Добавьте `app/db.py` (подключение и модели) и вынесите новые маршруты в
  `app/routers/` через `APIRouter`, подключив их в `main.py`.
- **Платежи (ЮKassa):** ключи `YOOKASSA_*` заготовлены в `config.py`; создание платежа и
  webhook — отдельный роутер `app/routers/payments.py`.
