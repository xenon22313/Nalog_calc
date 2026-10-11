"""Article registry. Article body lives in templates/articles/<slug>.html."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Article:
    slug: str
    title: str
    h1: str
    description: str
    template: str
    published: date
    updated: date

    @property
    def url(self) -> str:
        return f"/stati/{self.slug}"


ARTICLES: list[Article] = [
    Article(
        slug="kak-platit-nalog-samozanyatomu",
        title="Как самозанятому платить налог: пошаговая инструкция",
        h1="Как самозанятому платить налог",
        description="Когда и как самозанятый платит налог на профессиональный доход, что такое вычет и лимит дохода.",
        template="articles/kak-platit-nalog-samozanyatomu.html",
        published=date(2026, 1, 15),
        updated=date(2026, 1, 15),
    ),
]

_BY_SLUG = {article.slug: article for article in ARTICLES}


def get_article(slug: str) -> Article | None:
    return _BY_SLUG.get(slug)
