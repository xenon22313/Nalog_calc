"""All tax rates, limits and constants used by the calculators.

Values below are PLACEHOLDERS. Verify every number against official sources
before publishing the site.
"""

from datetime import date

# TODO: проверить по официальному источнику (ФНС / закон)
RATES_UPDATED = date(2026, 1, 1)

# Professional income tax for self-employed (NPD), Federal Law 422-FZ.
NPD = {
    # TODO: проверить по официальному источнику (ФНС / закон)
    "rate_individuals": 0.04,
    # TODO: проверить по официальному источнику (ФНС / закон)
    "rate_legal": 0.06,
    # One-time tax deduction, RUB.
    # TODO: проверить по официальному источнику (ФНС / закон)
    "deduction_total": 10_000,
    # Deduction reduces the rate by this amount for income from individuals.
    # TODO: проверить по официальному источнику (ФНС / закон)
    "deduction_rate_individuals": 0.01,
    # Deduction reduces the rate by this amount for income from companies / IP.
    # TODO: проверить по официальному источнику (ФНС / закон)
    "deduction_rate_legal": 0.02,
    # Annual income limit, RUB.
    # TODO: проверить по официальному источнику (ФНС / закон)
    "annual_income_limit": 2_400_000,
}

# Personal income tax (NDFL) progressive scale for residents.
# Each bracket: (upper bound of annual income in RUB or None for "no limit", rate).
NDFL = {
    # TODO: проверить по официальному источнику (ФНС / закон)
    "brackets": [
        (2_400_000, 0.13),
        (5_000_000, 0.15),
        (20_000_000, 0.18),
        (50_000_000, 0.20),
        (None, 0.22),
    ],
}

# Simplified tax system "Income" (USN 6%) for individual entrepreneurs.
USN_INCOME = {
    # Base rate; regions may set a lower one.
    # TODO: проверить по официальному источнику (ФНС / закон)
    "rate": 0.06,
    # Fixed insurance contributions of an IP for the year, RUB.
    # TODO: проверить по официальному источнику (ФНС / закон)
    "fixed_contributions": 57_390,  # 2026, ст. 430 НК РФ
    # Additional contribution: rate on income above the threshold.
    # TODO: проверить по официальному источнику (ФНС / закон)
    "extra_contribution_rate": 0.01,
    # TODO: проверить по официальному источнику (ФНС / закон)
    "extra_contribution_threshold": 300_000,
    # Maximum additional contribution, RUB.
    # TODO: проверить по официальному источнику (ФНС / закон)
    "extra_contribution_cap": 321_818,  # 2026, ст. 430 НК РФ
    # With employees the tax can be reduced by contributions by at most this share.
    # TODO: проверить по официальному источнику (ФНС / закон)
    "employer_reduction_cap": 0.5,
    # Annual income limit for USN, RUB.
    # TODO: проверить по официальному источнику (ФНС / закон)
    "income_limit": 490_500_000,  # 2026: 450 млн × 1,09 (425-ФЗ)
}


def rates_for_template() -> dict:
    """Rates exposed to templates (for 'how it is calculated' texts)."""
    return {
        "updated": RATES_UPDATED,
        "npd": NPD,
        "ndfl": NDFL,
        "usn_income": USN_INCOME,
    }
