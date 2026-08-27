from __future__ import annotations

from typing import Optional


Number = float | int | None


def safe_divide(
    numerator: Number,
    denominator: Number,
) -> Optional[float]:
    """Safely divide two numbers."""
    if numerator is None or denominator is None:
        return None

    denominator = float(denominator)

    if denominator == 0:
        return None

    return float(numerator) / denominator


def net_profit_margin(
    net_profit: Number,
    revenue: Number,
) -> Optional[float]:
    """Net profit margin (%) = Net Profit / Revenue × 100."""
    value = safe_divide(net_profit, revenue)

    return None if value is None else value * 100.0


def operating_profit_margin(
    operating_profit: Number,
    revenue: Number,
) -> Optional[float]:
    """Operating profit margin (%) = Operating Profit / Revenue × 100."""
    value = safe_divide(operating_profit, revenue)

    return None if value is None else value * 100.0


def return_on_equity(
    net_profit: Number,
    equity: Number,
) -> Optional[float]:
    """ROE (%) = Net Profit / Equity × 100."""
    value = safe_divide(net_profit, equity)

    return None if value is None else value * 100.0


def return_on_assets(
    net_profit: Number,
    total_assets: Number,
) -> Optional[float]:
    """ROA (%) = Net Profit / Total Assets × 100."""
    value = safe_divide(net_profit, total_assets)

    return None if value is None else value * 100.0


def debt_to_equity(
    debt: Number,
    equity: Number,
) -> Optional[float]:
    """Debt-to-equity = Total Debt / Equity."""
    return safe_divide(debt, equity)


def debt_ratio(
    debt: Number,
    total_assets: Number,
) -> Optional[float]:
    """Debt ratio = Total Debt / Total Assets."""
    return safe_divide(debt, total_assets)


def equity_ratio(
    equity: Number,
    total_assets: Number,
) -> Optional[float]:
    """Equity ratio = Equity / Total Assets."""
    return safe_divide(equity, total_assets)


def financial_leverage(
    total_assets: Number,
    equity: Number,
) -> Optional[float]:
    """Financial leverage = Total Assets / Equity."""
    return safe_divide(total_assets, equity)


def asset_turnover(
    revenue: Number,
    total_assets: Number,
) -> Optional[float]:
    """Asset turnover = Revenue / Total Assets."""
    return safe_divide(revenue, total_assets)


def interest_coverage(
    operating_profit: Number,
    interest: Number,
) -> Optional[float]:
    """Interest coverage = Operating Profit / Interest."""
    return safe_divide(operating_profit, interest)


def pretax_margin(
    profit_before_tax: Number,
    revenue: Number,
) -> Optional[float]:
    """Pretax margin (%) = PBT / Revenue × 100."""
    value = safe_divide(profit_before_tax, revenue)

    return None if value is None else value * 100.0


def operating_cash_flow_margin(
    operating_cash_flow: Number,
    revenue: Number,
) -> Optional[float]:
    """Operating cash flow margin (%) = CFO / Revenue × 100."""
    value = safe_divide(operating_cash_flow, revenue)

    return None if value is None else value * 100.0


def cash_flow_to_net_profit(
    operating_cash_flow: Number,
    net_profit: Number,
) -> Optional[float]:
    """Cash flow to net profit = CFO / Net Profit."""
    return safe_divide(operating_cash_flow, net_profit)


def return_on_capital_employed(
    operating_profit: Number,
    equity: Number,
    total_debt: Number,
    is_bank: bool = False,
) -> Optional[float]:
    """
    ROCE (%) = Operating Profit / Capital Employed × 100.

    Banks are explicitly excluded.
    """
    if is_bank:
        return None

    if operating_profit is None:
        return None

    if equity is None and total_debt is None:
        return None

    capital_employed = float(equity or 0) + float(total_debt or 0)

    if capital_employed == 0:
        return None

    return (float(operating_profit) / capital_employed) * 100.0
