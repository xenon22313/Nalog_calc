"""Calculator formulas: one input model and one pure function per calculator.

Every function takes validated input and an optional `rates` dict
(defaults to values from tax_rates.py) and returns a dict of results.
Money values are Decimal rounded to kopecks.
"""

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, Field

from app import tax_rates

KOPECK = Decimal("0.01")
MAX_INCOME = Decimal("100000000000")  # 100 bln RUB, sanity cap for any income field


def to_decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def money(value) -> Decimal:
    return to_decimal(value).quantize(KOPECK, rounding=ROUND_HALF_UP)


# --- Self-employed tax (NPD) -------------------------------------------------


class NpdInput(BaseModel):
    income_individuals: Decimal = Field(default=Decimal(0), ge=0, le=MAX_INCOME)
    income_legal: Decimal = Field(default=Decimal(0), ge=0, le=MAX_INCOME)
    deduction_left: Decimal = Field(
        default=to_decimal(tax_rates.NPD["deduction_total"]),
        ge=0,
        le=to_decimal(tax_rates.NPD["deduction_total"]),
    )


def calc_npd(data: NpdInput, rates: dict | None = None) -> dict:
    r = rates or tax_rates.NPD
    remaining = data.deduction_left

    base_ind = data.income_individuals * to_decimal(r["rate_individuals"])
    reduction_ind = min(data.income_individuals * to_decimal(r["deduction_rate_individuals"]), remaining)
    remaining -= reduction_ind

    base_legal = data.income_legal * to_decimal(r["rate_legal"])
    reduction_legal = min(data.income_legal * to_decimal(r["deduction_rate_legal"]), remaining)
    remaining -= reduction_legal

    tax_ind = base_ind - reduction_ind
    tax_legal = base_legal - reduction_legal
    total_income = data.income_individuals + data.income_legal

    return {
        "total_income": money(total_income),
        "tax_individuals": money(tax_ind),
        "tax_legal": money(tax_legal),
        "tax_total": money(tax_ind + tax_legal),
        "deduction_used": money(reduction_ind + reduction_legal),
        "deduction_left_after": money(remaining),
        "over_limit": total_income > to_decimal(r["annual_income_limit"]),
    }


# --- Salary after NDFL ---------------------------------------------------------


class SalaryInput(BaseModel):
    gross_monthly: Decimal = Field(ge=0, le=Decimal("1000000000"))


def progressive_tax(income: Decimal, brackets: list) -> Decimal:
    tax = Decimal(0)
    lower = Decimal(0)
    for upper, rate in brackets:
        if income <= lower:
            break
        top = income if upper is None else min(income, to_decimal(upper))
        tax += (top - lower) * to_decimal(rate)
        if upper is None:
            break
        lower = to_decimal(upper)
    return tax


def calc_salary(data: SalaryInput, rates: dict | None = None) -> dict:
    r = rates or tax_rates.NDFL
    annual = data.gross_monthly * 12
    ndfl_year = progressive_tax(annual, r["brackets"])
    net_year = annual - ndfl_year
    effective = ndfl_year / annual * 100 if annual else Decimal(0)

    return {
        "gross_year": money(annual),
        "ndfl_year": money(ndfl_year),
        "net_year": money(net_year),
        "ndfl_month": money(ndfl_year / 12),
        "net_month": money(net_year / 12),
        "effective_rate": money(effective),
    }


# --- USN "Income" for IP -------------------------------------------------------


class UsnIncomeInput(BaseModel):
    income: Decimal = Field(ge=0, le=MAX_INCOME)
    has_employees: bool = False
    # Contributions actually paid; if empty, the IP's own contributions are calculated.
    contributions: Decimal | None = Field(default=None, ge=0, le=Decimal("1000000000"))
    # Regional reduced rate in percent; if empty, the base rate is used.
    rate_percent: Decimal | None = Field(
        default=None, ge=0, le=to_decimal(tax_rates.USN_INCOME["rate"]) * 100
    )


def calc_usn_income(data: UsnIncomeInput, rates: dict | None = None) -> dict:
    r = rates or tax_rates.USN_INCOME
    rate = data.rate_percent / 100 if data.rate_percent is not None else to_decimal(r["rate"])

    over_threshold = max(data.income - to_decimal(r["extra_contribution_threshold"]), Decimal(0))
    extra = min(over_threshold * to_decimal(r["extra_contribution_rate"]), to_decimal(r["extra_contribution_cap"]))
    own_contributions = to_decimal(r["fixed_contributions"]) + extra
    contributions = data.contributions if data.contributions is not None else own_contributions

    tax = data.income * rate
    reduction_cap = tax * to_decimal(r["employer_reduction_cap"]) if data.has_employees else tax
    reduction = min(contributions, reduction_cap)

    return {
        "rate_percent": money(rate * 100),
        "tax_before_reduction": money(tax),
        "extra_contribution": money(extra),
        "own_contributions": money(own_contributions),
        "contributions_used": money(contributions),
        "reduction": money(reduction),
        "tax_due": money(tax - reduction),
        "over_limit": data.income > to_decimal(r["income_limit"]),
    }
