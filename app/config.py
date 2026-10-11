"""Site settings. Every value can be overridden with an environment variable."""

import os


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    SITE_NAME: str = os.getenv("SITE_NAME", "НалогКальк")
    SITE_URL: str = os.getenv("SITE_URL", "http://127.0.0.1:8000").rstrip("/")
    CONTACT_EMAIL: str = os.getenv("CONTACT_EMAIL", "info@example.ru")

    # Yandex.Metrika counter ID, e.g. "12345678". Empty = counter is not rendered.
    METRIKA_ID: str = os.getenv("METRIKA_ID", "")
    # Yandex Advertising Network (RSYA) block ID, e.g. "R-A-123456-1". Empty = no ad block.
    RSYA_BLOCK_ID: str = os.getenv("RSYA_BLOCK_ID", "")

    # Rate limit for POST /api/calc/* per client IP.
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    # Take the client IP from X-Forwarded-For (app runs behind nginx).
    # Set to 0 if uvicorn is exposed directly, otherwise clients can spoof their IP.
    TRUST_PROXY_HEADERS: bool = _bool("TRUST_PROXY_HEADERS", True)

    # Future: registration and payments.
    # DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/site.db")
    # YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
    # YOOKASSA_SECRET_KEY: str = os.getenv("YOOKASSA_SECRET_KEY", "")


settings = Settings()
