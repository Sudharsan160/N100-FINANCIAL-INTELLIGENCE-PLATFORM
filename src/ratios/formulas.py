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
    Year-over-year growth percentage.

    Returns None when the previous value is missing or zero.
    """
    return percentage(
        None if current is None or previous is None else float(current) - float(previous),
        previous,
    )


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