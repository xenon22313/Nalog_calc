"""Calculator registry. Add a new calculator by appending a Calculator to CALCULATORS."""

from dataclasses import dataclass, field
from typing import Callable

from pydantic import BaseModel

from app import formulas


@dataclass(frozen=True)
class Calculator:
    slug: str  # page URL: /kalkulyator-<slug>, API: /api/calc/<slug>
    title: str  # <title>
    h1: str
    description: str  # meta description
    keywords: str
    template: str  # partial in templates/calculators/
    input_model: type[BaseModel]
    func: Callable[[BaseModel], dict]
    menu: str = ""  # header menu label (defaults to h1)
    short: str = ""  # card text on the home page
    example: dict = field(default_factory=dict)  # input for "Пример расчёта" and form defaults
    faq: list[tuple[str, str]] = field(default_factory=list)
    related: list[str] = field(default_factory=list)  # slugs of other calculators

    @property
    def url(self) -> str:
        return f"/kalkulyator-{self.slug}"


CALCULATORS: list[Calculator] = [
    Calculator(
        slug="nalog-samozanyatogo",
        title="Калькулятор налога для самозанятых (НПД) онлайн",
        h1="Калькулятор налога для самозанятых",
        description=(
            "Рассчитайте налог на профессиональный доход (НПД) для самозанятых онлайн: "
            "ставки для доходов от физлиц и компаний, учёт налогового вычета."
        ),
        keywords="калькулятор самозанятого, налог самозанятых, НПД калькулятор",
        template="calculators/npd.html",
        input_model=formulas.NpdInput,
        func=formulas.calc_npd,
        menu="Самозанятые",
        short="Налог на профессиональный доход с учётом вычета.",
        example={"income_individuals": 80000, "income_legal": 50000, "deduction_left": 10000},
        faq=[
            (
                "Когда самозанятому нужно платить налог?",
                "Налог за месяц начисляется в приложении «Мой налог», уведомление приходит "
                "до 12-го числа следующего месяца, оплатить нужно до 28-го числа.",
            ),
            (
                "Что такое налоговый вычет для самозанятых?",
                "Это разовая сумма, за счёт которой ставка временно снижается. "
                "Вычет расходуется автоматически, пока не закончится.",
            ),
            (
                "Что будет при превышении лимита дохода?",
                "Право применять НПД теряется, нужно перейти на другой налоговый режим.",
            ),
        ],
        related=["usn-dohody", "zarplata-na-ruki"],
    ),
    Calculator(
        slug="zarplata-na-ruki",
        title="Калькулятор зарплаты на руки с учётом НДФЛ онлайн",
        h1="Калькулятор зарплаты на руки",
        description=(
            "Узнайте, сколько вы получите на руки после удержания НДФЛ: "
            "расчёт по прогрессивной шкале, налог за месяц и за год."
        ),
        keywords="зарплата на руки, калькулятор НДФЛ, расчёт зарплаты после налогов",
        template="calculators/salary.html",
        input_model=formulas.SalaryInput,
        func=formulas.calc_salary,
        menu="Зарплата на руки",
        short="Сколько останется после НДФЛ по прогрессивной шкале.",
        example={"gross_monthly": 150000},
        faq=[
            (
                "Как считается НДФЛ по прогрессивной шкале?",
                "Каждая часть годового дохода облагается по своей ставке: "
                "сумма до первого порога — по базовой ставке, превышение — по повышенной.",
            ),
            (
                "Почему НДФЛ за месяц может меняться в течение года?",
                "Работодатель считает налог нарастающим итогом. Когда доход с начала года "
                "переходит порог, ставка для оставшейся части растёт. Калькулятор показывает "
                "среднее значение за месяц.",
            ),
            (
                "Учитываются ли налоговые вычеты?",
                "Нет, расчёт выполняется без стандартных, имущественных и социальных вычетов.",
            ),
        ],
        related=["nalog-samozanyatogo", "usn-dohody"],
    ),
    Calculator(
        slug="usn-dohody",
        title="Калькулятор налога УСН «Доходы» для ИП онлайн",
        h1="Калькулятор налога УСН «Доходы»",
        description=(
            "Рассчитайте налог ИП на УСН «Доходы»: уменьшение налога на страховые взносы, "
            "взнос 1% с дохода сверх порога, ИП с работниками и без."
        ),
        keywords="калькулятор УСН доходы, налог ИП УСН 6%, страховые взносы ИП",
        template="calculators/usn_income.html",
        input_model=formulas.UsnIncomeInput,
        func=formulas.calc_usn_income,
        menu="УСН «Доходы»",
        short="Налог ИП с учётом уменьшения на страховые взносы.",
        example={"income": 2000000, "has_employees": False},
        faq=[
            (
                "Можно ли уменьшить налог УСН на страховые взносы?",
                "Да. ИП без работников может уменьшить налог на взносы полностью, "
                "ИП с работниками — не более чем наполовину.",
            ),
            (
                "Что такое взнос 1% с дохода?",
                "Дополнительный страховой взнос ИП с дохода, превышающего установленный порог за год. "
                "Сумма этого взноса ограничена максимумом.",
            ),
            (
                "Может ли ставка быть ниже базовой?",
                "Да, регионы вправе устанавливать пониженные ставки. Укажите её в поле «Ставка».",
            ),
        ],
        related=["nalog-samozanyatogo", "zarplata-na-ruki"],
    ),
]

_BY_SLUG = {calc.slug: calc for calc in CALCULATORS}


def get_calculator(slug: str) -> Calculator | None:
    return _BY_SLUG.get(slug)
