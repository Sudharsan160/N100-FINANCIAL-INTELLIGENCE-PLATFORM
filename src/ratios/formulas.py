from __future__ import annotations

from typing import Optional


Number = float | int | None


def safe_divide(
    numerator: Number,
    denominator: Number,
) -> Optional[float]:
    """
    Safely divide two values.

    Returns None when:
    - numerator is None
    - denominator is None
    - denominator is zero
    """
    if numerator is None or denominator is None:
        return None

    if denominator == 0:
        return None

    return float(numerator) / float(denominator)


def percentage(
    numerator: Number,
    denominator: Number,
) -> Optional[float]:
    """Return a ratio as a percentage."""
    result = safe_divide(numerator, denominator)

    if result is None:
        return None

    return result * 100.0


def net_profit_margin(
    net_profit: Number,
    sales: Number,
) -> Optional[float]:
    """Net Profit Margin (%) = Net Profit / Sales × 100."""
    return percentage(net_profit, sales)


def operating_profit_margin(
    operating_profit: Number,
    sales: Number,
) -> Optional[float]:
    """Operating Profit Margin (%) = Operating Profit / Sales × 100."""
    return percentage(operating_profit, sales)


def return_on_equity(
    net_profit: Number,
    equity: Number,
) -> Optional[float]:
    """ROE (%) = Net Profit / Equity × 100."""
    return percentage(net_profit, equity)


def debt_to_equity(
    total_debt: Number,
    equity: Number,
) -> Optional[float]:
    """Debt-to-Equity = Total Debt / Equity."""
    return safe_divide(total_debt, equity)


def interest_coverage(
    operating_profit: Number,
    interest: Number,
) -> Optional[float]:
    """Interest Coverage = Operating Profit / Interest."""
    return safe_divide(operating_profit, interest)


def asset_turnover(
    sales: Number,
    total_assets: Number,
) -> Optional[float]:
    """Asset Turnover = Sales / Total Assets."""
    return safe_divide(sales, total_assets)


def free_cash_flow(
    operating_cash_flow: Number,
    capital_expenditure: Number,
) -> Optional[float]:
    """
    Free Cash Flow = Operating Cash Flow - absolute Capital Expenditure.

    Capital expenditure may appear as a negative cash-flow value,
    so abs() prevents subtracting a negative capex twice.
    """
    if operating_cash_flow is None or capital_expenditure is None:
        return None

    return float(operating_cash_flow) - abs(float(capital_expenditure))