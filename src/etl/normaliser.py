"""
Data normalization utilities for the N100 Financial Intelligence Platform.

Functions:
    normalize_year()   -> converts year values into a standard integer year
    normalize_ticker() -> cleans and standardizes stock ticker symbols
"""

import re
from typing import Any, Optional


def normalize_year(value: Any) -> Optional[int]:
    """
    Normalize financial year/date values into a four-digit integer.

    Examples:
        2024       -> 2024
        "2024"     -> 2024
        "FY2024"   -> 2024
        "Dec 2012" -> 2012
        "Mar 2014" -> 2014
        "Mar-13"   -> 2013
        "Mar-14"   -> 2014
        None       -> None
    """
    if value is None:
        return None

    if isinstance(value, float) and value != value:
        return None

    text = str(value).strip()

    if not text:
        return None

    # Full four-digit year.
    match = re.search(r"(19|20)\d{2}", text)
    if match:
        return int(match.group(0))
    # Financial data often uses values such as Mar-13 / Dec-12.
    match = re.search(
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[-_ ](\d{2})$",
        text,
        re.IGNORECASE,
    )

    if match:
        short_year = int(match.group(1))
        return 2000 + short_year

    # TTM = Trailing Twelve Months; it has no single calendar year.
    if text.upper() == "TTM":
        return None

    raise ValueError(f"Invalid year value: {value!r}")
    


def normalize_ticker(value: Any) -> Optional[str]:
    """
    Normalize a stock ticker symbol.

    Examples:
        "RELIANCE"     -> "RELIANCE"
        " reliance "   -> "RELIANCE"
        "RELIANCE.NS"  -> "RELIANCE"
        "TCS.BO"       -> "TCS"
        "MM"           -> "M&M"
        None           -> None
        ""             -> None
    """
    if value is None:
        return None

    text = str(value).strip().upper()

    if not text:
        return None

    # Remove common exchange suffixes.
    text = re.sub(r"\.(NS|BO|BSE|NSE)$", "", text)

    # Source-data ticker aliases.
    ticker_aliases = {
        "MM": "M&M",
    }

    text = ticker_aliases.get(text, text)

    # Keep letters, numbers, ampersand, hyphens and underscores.
    text = re.sub(r"[^A-Z0-9&_-]", "", text)

    return text or None