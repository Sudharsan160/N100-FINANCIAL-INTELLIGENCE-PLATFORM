import pytest

from src.etl.normaliser import normalize_ticker, normalize_year


# =========================
# normalize_year() tests
# =========================

@pytest.mark.parametrize(
    "value, expected",
    [
        (2024, 2024),
        (2023, 2023),
        (2000, 2000),
        ("2024", 2024),
        (" 2024 ", 2024),
        ("FY2024", 2024),
        ("FY 2024", 2024),
        ("FY-2024", 2024),
        ("Financial Year 2024", 2024),
        (2024.0, 2024),
        ("2024.0", 2024),
        ("Q4 FY2024", 2024),
        ("FY2024-25", 2024),
        ("2022-23", 2022),
        ("2019 Annual", 2019),
        ("Year: 2021", 2021),
        ("  FY 2025  ", 2025),
        (None, None),
        ("", None),
        ("   ", None),
    ],
)
def test_normalize_year_valid_values(value, expected):
    assert normalize_year(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "abc",
        "FY",
        "999",
        "abcd",
    ],
)
def test_normalize_year_invalid_values(value):
    # Values containing no valid 19xx/20xx year should fail.
    with pytest.raises(ValueError):
        normalize_year(value)


def test_normalize_year_nan():
    assert normalize_year(float("nan")) is None


# =========================
# normalize_ticker() tests
# =========================

@pytest.mark.parametrize(
    "value, expected",
    [
        ("RELIANCE", "RELIANCE"),
        ("reliance", "RELIANCE"),
        (" Reliance ", "RELIANCE"),
        ("TCS", "TCS"),
        ("tcs", "TCS"),
        ("INFY", "INFY"),
        ("infy", "INFY"),
        ("RELIANCE.NS", "RELIANCE"),
        ("reliance.ns", "RELIANCE"),
        ("TCS.BO", "TCS"),
        ("INFY.NSE", "INFY"),
        ("ABC.BSE", "ABC"),
        ("ABC-123", "ABC-123"),
        ("ABC_123", "ABC_123"),
        ("ABC 123", "ABC123"),
        ("A.B.C", "ABC"),
        (None, None),
        ("", None),
        ("   ", None),
    ],
)
def test_normalize_ticker_valid_values(value, expected):
    assert normalize_ticker(value) == expected


def test_normalize_ticker_numeric_value():
    assert normalize_ticker(500325) == "500325"


def test_normalize_ticker_mixed_case():
    assert normalize_ticker("ReLiAnCe") == "RELIANCE"


def test_normalize_ticker_special_characters():
    assert normalize_ticker("ABC@#$!") == "ABC"


def test_normalize_ticker_leading_trailing_spaces():
    assert normalize_ticker("   TCS   ") == "TCS"


def test_normalize_ticker_exchange_suffix_lowercase():
    assert normalize_ticker("tcs.bo") == "TCS"


def test_normalize_ticker_multiple_spaces():
    assert normalize_ticker("A B C") == "ABC"


def test_normalize_ticker_none():
    assert normalize_ticker(None) is None