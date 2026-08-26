from __future__ import annotations

from typing import Optional


Number = float | int | None


def safe_divide(
    numerator: Number,
    denominator: Number,
) -> Optional[float]:
    """Safely divide two values."""
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


def growth_percentage(
    current: Number,
    previous: Number,
) -> Optional[float]:
    """
    Calculate year-over-year growth percentage.

    Policy:
    - Missing current/previous value -> None
    - Previous value <= 0 -> None
    - Otherwise: (current - previous) / previous * 100

    This avoids misleading percentages for zero or negative
    prior-period values, including negative-to-positive turnarounds.
    """
    if current is None or previous is None:
        return None

    if float(previous) <= 0:
        return None

    return (
        (float(current) - float(previous))
        / float(previous)
    ) * 100.0

def net_profit_margin(
    net_profit: Number,
    sales: Number,
) -> Optional[float]:
    return percentage(net_profit, sales)


def operating_profit_margin(
    operating_profit: Number,
    sales: Number,
) -> Optional[float]:
    return percentage(operating_profit, sales)


def return_on_equity(
    net_profit: Number,
    equity: Number,
) -> Optional[float]:
    return percentage(net_profit, equity)


def return_on_assets(
    net_profit: Number,
    total_assets: Number,
) -> Optional[float]:
    return percentage(net_profit, total_assets)


def pretax_margin(
    profit_before_tax: Number,
    sales: Number,
) -> Optional[float]:
    return percentage(profit_before_tax, sales)


def operating_cash_flow_margin(
    operating_cash_flow: Number,
    sales: Number,
) -> Optional[float]:
    return percentage(operating_cash_flow, sales)


def cash_flow_to_net_profit(
    operating_cash_flow: Number,
    net_profit: Number,
) -> Optional[float]:
    return safe_divide(operating_cash_flow, net_profit)


def debt_to_equity(
    total_debt: Number,
    equity: Number,
) -> Optional[float]:
    return safe_divide(total_debt, equity)


def debt_ratio(
    total_debt: Number,
    total_assets: Number,
) -> Optional[float]:
    return safe_divide(total_debt, total_assets)


def equity_ratio(
    equity: Number,
    total_assets: Number,
) -> Optional[float]:
    return safe_divide(equity, total_assets)


def financial_leverage(
    total_assets: Number,
    equity: Number,
) -> Optional[float]:
    return safe_divide(total_assets, equity)


def interest_coverage(
    operating_profit: Number,
    interest: Number,
) -> Optional[float]:
    return safe_divide(operating_profit, interest)


def asset_turnover(
    sales: Number,
    total_assets: Number,
) -> Optional[float]:
    return safe_divide(sales, total_assets)


def free_cash_flow(
    operating_cash_flow: Number,
    capital_expenditure: Number,
) -> Optional[float]:
    if operating_cash_flow is None or capital_expenditure is None:
        return None

    return float(operating_cash_flow) - abs(float(capital_expenditure))


def revenue_growth(
    current_sales: Number,
    previous_sales: Number,
) -> Optional[float]:
    return growth_percentage(current_sales, previous_sales)


def operating_profit_growth(
    current_operating_profit: Number,
    previous_operating_profit: Number,
) -> Optional[float]:
    return growth_percentage(
        current_operating_profit,
        previous_operating_profit,
    )


def net_profit_growth(
    current_net_profit: Number,
    previous_net_profit: Number,
) -> Optional[float]:
    return growth_percentage(
        current_net_profit,
        previous_net_profit,
    )


def eps_growth(
    current_eps: Number,
    previous_eps: Number,
) -> Optional[float]:
    return growth_percentage(current_eps, previous_eps)

def cfo_to_total_debt(
    operating_cash_flow: Number,
    total_debt: Number,
) -> Optional[float]:
    """Operating cash flow / total debt."""
    return safe_divide(operating_cash_flow, total_debt)


def free_cash_flow_margin(
    free_cash_flow_value: Number,
    sales: Number,
) -> Optional[float]:
    """Free cash flow as a percentage of sales."""
    return percentage(free_cash_flow_value, sales)


def investing_cash_flow_to_cfo(
    investing_cash_flow: Number,
    operating_cash_flow: Number,
) -> Optional[float]:
    """Investing cash flow / operating cash flow."""
    return safe_divide(investing_cash_flow, operating_cash_flow)


def financing_cash_flow_to_cfo(
    financing_cash_flow: Number,
    operating_cash_flow: Number,
) -> Optional[float]:
    """Financing cash flow / operating cash flow."""
    return safe_divide(financing_cash_flow, operating_cash_flow)


def cash_conversion_ratio(
    operating_cash_flow: Number,
    operating_profit: Number,
) -> Optional[float]:
    """Operating cash flow / operating profit."""
    return safe_divide(operating_cash_flow, operating_profit)


def capital_expenditure_intensity(
    capital_expenditure: Number,
    sales: Number,
) -> Optional[float]:
    """Absolute capital expenditure as a percentage of sales."""
    if capital_expenditure is None:
        return None

    return percentage(abs(float(capital_expenditure)), sales)