"""Reference cases for formulas.

Rates are passed explicitly, so these tests do not depend on tax_rates.py.
Replace numbers with verified ones when official values are confirmed.
"""

from decimal import Decimal

import pytest

from app.formulas import (
    NpdInput,
    SalaryInput,
    UsnIncomeInput,
    calc_npd,
    calc_salary,
    calc_usn_income,
    money,
)

D = Decimal

NPD_RATES = {
    "rate_individuals": 0.04,
    "rate_legal": 0.06,
    "deduction_total": 10_000,
    "deduction_rate_individuals": 0.01,
    "deduction_rate_legal": 0.02,
    "annual_income_limit": 2_400_000,
}

NDFL_RATES = {
    "brackets": [
        (2_400_000, 0.13),
        (5_000_000, 0.15),
        (20_000_000, 0.18),
        (50_000_000, 0.20),
        (None, 0.22),
    ],
}

USN_RATES = {
    "rate": 0.06,
    "fixed_contributions": 53_658,
    "extra_contribution_rate": 0.01,
    "extra_contribution_threshold": 300_000,
    "extra_contribution_cap": 300_888,
    "employer_reduction_cap": 0.5,
    "income_limit": 450_000_000,
}


# --- NPD ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "inp, expected",
    [
        # Individuals only, full deduction: 100000*4% - 100000*1%
        (
            {"income_individuals": 100_000, "income_legal": 0, "deduction_left": 10_000},
            {"tax_total": D("3000.00"), "deduction_used": D("1000.00"), "deduction_left_after": D("9000.00")},
        ),
        # Companies only: 100000*6% - 100000*2%
        (
            {"income_individuals": 0, "income_legal": 100_000, "deduction_left": 10_000},
            {"tax_total": D("4000.00"), "deduction_used": D("2000.00"), "deduction_left_after": D("8000.00")},
        ),
        # Deduction almost used up: only 500 left, applied to individuals first
        (
            {"income_individuals": 100_000, "income_legal": 100_000, "deduction_left": 500},
            {"tax_individuals": D("3500.00"), "tax_legal": D("6000.00"), "tax_total": D("9500.00"),
             "deduction_used": D("500.00"), "deduction_left_after": D("0.00")},
        ),
        # No deduction left, kopecks rounding: 12345.67*4% = 493.8268
        (
            {"income_individuals": "12345.67", "income_legal": 0, "deduction_left": 0},
            {"tax_total": D("493.83"), "deduction_used": D("0.00")},
        ),
    ],
)
def test_npd_reference(inp, expected):
    result = calc_npd(NpdInput(**inp), NPD_RATES)
    for key, value in expected.items():
        assert result[key] == value, key


def test_npd_over_limit():
    result = calc_npd(NpdInput(income_individuals=2_500_000, deduction_left=0), NPD_RATES)
    assert result["over_limit"] is True


# --- Salary --------------------------------------------------------------------

@pytest.mark.parametrize(
    "gross, expected",
    [
        # 1.2M/year, all in the first bracket
        (100_000, {"ndfl_year": D("156000.00"), "net_month": D("87000.00"), "effective_rate": D("13.00")}),
        # 3.6M/year: 2.4M*13% + 1.2M*15% = 312000 + 180000
        (300_000, {"ndfl_year": D("492000.00"), "ndfl_month": D("41000.00"),
                   "net_month": D("259000.00"), "effective_rate": D("13.67")}),
        # 24M/year: 312000 + 390000 + 2700000 + 800000
        (2_000_000, {"ndfl_year": D("4202000.00"), "ndfl_month": D("350166.67"),
                     "net_month": D("1649833.33"), "effective_rate": D("17.51")}),
        # Zero salary
        (0, {"ndfl_year": D("0.00"), "net_month": D("0.00"), "effective_rate": D("0.00")}),
    ],
)
def test_salary_reference(gross, expected):
    result = calc_salary(SalaryInput(gross_monthly=gross), NDFL_RATES)
    for key, value in expected.items():
        assert result[key] == value, key


# --- USN "Income" ----------------------------------------------------------------

@pytest.mark.parametrize(
    "inp, expected",
    [
        # No employees: tax 60000, own contributions 53658 + 7000 cover it fully
        (
            {"income": 1_000_000},
            {"tax_before_reduction": D("60000.00"), "own_contributions": D("60658.00"),
             "reduction": D("60000.00"), "tax_due": D("0.00")},
        ),
        # With employees: reduction limited to 50% of the tax
        (
            {"income": 1_000_000, "has_employees": True, "contributions": 100_000},
            {"tax_before_reduction": D("60000.00"), "reduction": D("30000.00"), "tax_due": D("30000.00")},
        ),
        # 5M: tax 300000, contributions 53658 + 47000
        (
            {"income": 5_000_000},
            {"extra_contribution": D("47000.00"), "own_contributions": D("100658.00"), "tax_due": D("199342.00")},
        ),
        # 1% contribution hits the cap
        (
            {"income": 50_000_000},
            {"extra_contribution": D("300888.00"), "own_contributions": D("354546.00"), "tax_due": D("2645454.00")},
        ),
        # Regional reduced rate 1%
        (
            {"income": 1_000_000, "rate_percent": 1},
            {"rate_percent": D("1.00"), "tax_before_reduction": D("10000.00"), "tax_due": D("0.00")},
        ),
    ],
)
def test_usn_income_reference(inp, expected):
    result = calc_usn_income(UsnIncomeInput(**inp), USN_RATES)
    for key, value in expected.items():
        assert result[key] == value, key


def test_money_rounds_half_up():
    assert money("0.005") == D("0.01")
    assert money("1.234") == D("1.23")
