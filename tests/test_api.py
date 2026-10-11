import pytest
from fastapi.testclient import TestClient

from app import main
from app.articles import ARTICLES
from app.calculators import CALCULATORS

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_limiter():
    main.limiter.reset()
    yield
    main.limiter.reset()


@pytest.mark.parametrize("path", ["/", "/privacy"] + [c.url for c in CALCULATORS] + [a.url for a in ARTICLES])
def test_pages_ok(path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.text.count("<h1") == 1


@pytest.mark.parametrize("calc", CALCULATORS, ids=lambda c: c.slug)
def test_calculator_page_seo(calc):
    html = client.get(calc.url).text
    assert f"<title>{calc.title}</title>" in html
    assert f'<link rel="canonical" href="{main.settings.SITE_URL}{calc.url}">' in html
    assert 'property="og:title"' in html
    for schema_type in ("BreadcrumbList", "FAQPage", "WebApplication"):
        assert schema_type in html
    assert "Расчёт справочный и не является налоговой консультацией" in html
    assert "Рассчитать" in html


def test_404_page():
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert "Страница не найдена" in response.text
    assert client.get("/kalkulyator-unknown").status_code == 404


def test_sitemap_lists_all_pages():
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    for item in CALCULATORS + ARTICLES:
        assert f"<loc>{main.settings.SITE_URL}{item.url}</loc>" in response.text


def test_robots():
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "Sitemap: " in response.text
    assert "Disallow: /api/" in response.text


def test_static_cache_and_gzip():
    response = client.get("/static/css/site.css", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert "max-age=31536000" in response.headers["cache-control"]
    page = client.get("/", headers={"Accept-Encoding": "gzip"})
    assert page.headers.get("content-encoding") == "gzip"


def test_static_url_has_mtime_version():
    assert main.static_url("css/site.css").startswith("/static/css/site.css?v=")
    assert not main.static_url("css/site.css").endswith("?v=0")


@pytest.mark.parametrize("calc", CALCULATORS, ids=lambda c: c.slug)
def test_api_example_ok(calc):
    response = client.post(f"/api/calc/{calc.slug}", json=calc.example)
    assert response.status_code == 200
    result = response.json()["result"]
    for value in result.values():
        if isinstance(value, float):
            assert round(value, 2) == value


def test_api_npd_values():
    response = client.post(
        "/api/calc/nalog-samozanyatogo",
        json={"income_individuals": "12345.67", "income_legal": 0, "deduction_left": 0},
    )
    assert response.status_code == 200
    assert response.json()["result"]["tax_total"] == pytest.approx(493.83)


def test_api_validation_error():
    response = client.post("/api/calc/zarplata-na-ruki", json={"gross_monthly": -5})
    assert response.status_code == 422
    assert "gross_monthly" in response.json()["fields"]

    response = client.post("/api/calc/zarplata-na-ruki", json={"gross_monthly": "10000000000000"})
    assert response.status_code == 422


def test_api_bad_json_and_unknown_slug():
    assert client.post("/api/calc/zarplata-na-ruki", content=b"not json").status_code == 400
    assert client.post("/api/calc/unknown", json={}).status_code == 404


def test_api_rate_limit(monkeypatch):
    monkeypatch.setattr(main.limiter, "limit", 3)
    for _ in range(3):
        assert client.post("/api/calc/zarplata-na-ruki", json={"gross_monthly": 1}).status_code == 200
    response = client.post("/api/calc/zarplata-na-ruki", json={"gross_monthly": 1})
    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_rate_limit_uses_x_forwarded_for(monkeypatch):
    monkeypatch.setattr(main.limiter, "limit", 1)
    url = "/api/calc/zarplata-na-ruki"
    body = {"gross_monthly": 1}
    assert client.post(url, json=body, headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert client.post(url, json=body, headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429
    assert client.post(url, json=body, headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 200
