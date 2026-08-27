from __future__ import annotations

from typing import Optional


Number = float | int | None


def safe_divide(
    numerator: Number,
    denominator: Number,
) -> Optional[float]:
    """Safely divide two numeric values."""
    if numerator is None or denominator is None:
        return None

    denominator = float(denominator)

    if denominator == 0:
        return None

    return float(numerator) / denominator


def cfo_quality(
    operating_cash_flow: Number,
    net_profit: Number,
) -> Optional[float]:
    """
    CFO quality = Operating Cash Flow / Net Profit.

    Higher positive values generally indicate stronger cash conversion.
    """
    return safe_divide(
        operating_cash_flow,
        net_profit,
    )


def capex_intensity(
    capital_expenditure: Number,
    revenue: Number,
) -> Optional[float]:
    """
    CapEx intensity (%) = |CapEx| / Revenue × 100.
    """
    if capital_expenditure is None:
        return None

    value = safe_divide(
        abs(float(capital_expenditure)),
        revenue,
    )

    return None if value is None else value * 100.0


def free_cash_flow_conversion(
    free_cash_flow: Number,
    net_profit: Number,
) -> Optional[float]:
    """
    FCF conversion = Free Cash Flow / Net Profit.
    """
    return safe_divide(
        free_cash_flow,
        net_profit,
    )


def free_cash_flow_margin(
    free_cash_flow: Number,
    revenue: Number,
) -> Optional[float]:
    """
    FCF margin (%) = Free Cash Flow / Revenue × 100.
    """
    value = safe_divide(
        free_cash_flow,
        revenue,
    )

    return None if value is None else value * 100.0


def cash_flow_to_debt(
    operating_cash_flow: Number,
    total_debt: Number,
) -> Optional[float]:
    """
    CFO / Total Debt.
    """
    return safe_divide(
        operating_cash_flow,
        total_debt,
    )


def investing_to_cfo(
    investing_cash_flow: Number,
    operating_cash_flow: Number,
) -> Optional[float]:
    """
    Investing Cash Flow / CFO.
    """
    return safe_divide(
        investing_cash_flow,
        operating_cash_flow,
    )


def financing_to_cfo(
    financing_cash_flow: Number,
    operating_cash_flow: Number,
) -> Optional[float]:
    """
    Financing Cash Flow / CFO.
    """
    return safe_divide(
        financing_cash_flow,
        operating_cash_flow,
    )
