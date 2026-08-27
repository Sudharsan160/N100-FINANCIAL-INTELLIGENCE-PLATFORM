from __future__ import annotations

import math
from typing import Optional


Number = float | int | None


def calculate_cagr(
    start_value: Number,
    end_value: Number,
    periods: Number,
) -> Optional[float]:
    """
    Calculate CAGR as a percentage.

    Edge-case policy:
    1. Missing start/end value -> None
    2. Start value == 0 -> None
    3. Start value < 0 -> None
    4. End value < 0 -> None
    5. periods <= 0 -> None
    6. Normal positive values -> CAGR %
    """
    if start_value is None or end_value is None or periods is None:
        return None

    start = float(start_value)
    end = float(end_value)
    years = float(periods)

    if not math.isfinite(start) or not math.isfinite(end):
        return None

    if not math.isfinite(years) or years <= 0:
        return None

    if start <= 0:
        return None

    if end < 0:
        return None

    return ((end / start) ** (1.0 / years) - 1.0) * 100.0


def revenue_cagr(
    start_revenue: Number,
    end_revenue: Number,
    periods: Number,
) -> Optional[float]:
    """Revenue CAGR (%) for a positive starting revenue."""
    return calculate_cagr(
        start_revenue,
        end_revenue,
        periods,
    )


def profit_cagr(
    start_profit: Number,
    end_profit: Number,
    periods: Number,
) -> Optional[float]:
    """Net-profit CAGR (%) with the same edge-case policy."""
    return calculate_cagr(
        start_profit,
        end_profit,
        periods,
    )


def eps_cagr(
    start_eps: Number,
    end_eps: Number,
    periods: Number,
) -> Optional[float]:
    """EPS CAGR (%) with the same edge-case policy."""
    return calculate_cagr(
        start_eps,
        end_eps,
        periods,
    )


def cagr_status(
    start_value: Number,
    end_value: Number,
    periods: Number,
) -> str:
    """
    Return a human-readable CAGR edge-case category.

    Categories:
    - MISSING_VALUE
    - ZERO_START
    - NEGATIVE_START
    - NEGATIVE_END
    - INVALID_PERIOD
    - VALID
    """
    if start_value is None or end_value is None or periods is None:
        return "MISSING_VALUE"

    start = float(start_value)
    end = float(end_value)
    years = float(periods)

    if not math.isfinite(start) or not math.isfinite(end):
        return "MISSING_VALUE"

    if not math.isfinite(years) or years <= 0:
        return "INVALID_PERIOD"

    if start == 0:
        return "ZERO_START"

    if start < 0:
        return "NEGATIVE_START"

    if end < 0:
        return "NEGATIVE_END"

    return "VALID"
