import pandas as pd

from src.etl.validator import (
    validate_all,
    validate_balance_sheet,
    validate_bse_balance,
    validate_company_coverage,
    validate_company_year_pk,
    validate_dividend_cap,
    validate_duplicates,
    validate_eps_sign,
    validate_fk_integrity,
    validate_net_cash,
    validate_opm,
    validate_pk_uniqueness,
    validate_required_fields,
    validate_sales_positive,
    validate_tax_rate,
    validate_urls,
    validate_year_coverage,
)


# ============================================================
# DQ-01: Primary-key uniqueness
# ============================================================

def test_dq01_company_id_duplicate():
    df = pd.DataFrame({"company_id": [1, 1, 2]})
    failures = []

    validate_pk_uniqueness(
        df,
        ["company_id"],
        "companies",
        failures,
    )

    assert any(f["rule_id"] == "DQ-01" for f in failures)


def test_dq01_no_duplicate_company_id():
    df = pd.DataFrame({"company_id": [1, 2, 3]})
    failures = []

    validate_pk_uniqueness(
        df,
        ["company_id"],
        "companies",
        failures,
    )

    assert not any(f["rule_id"] == "DQ-01" for f in failures)


# ============================================================
# DQ-02: (company_id, year) uniqueness
# ============================================================

def test_dq02_company_year_duplicate():
    df = pd.DataFrame(
        {
            "company_id": [1, 1, 2],
            "year": [2024, 2024, 2024],
        }
    )
    failures = []

    validate_company_year_pk(
        df,
        "profitandloss",
        failures,
    )

    assert any(f["rule_id"] == "DQ-02" for f in failures)


def test_dq02_no_duplicate_company_year():
    df = pd.DataFrame(
        {
            "company_id": [1, 1, 2],
            "year": [2023, 2024, 2024],
        }
    )
    failures = []

    validate_company_year_pk(
        df,
        "profitandloss",
        failures,
    )

    assert not any(f["rule_id"] == "DQ-02" for f in failures)


# ============================================================
# DQ-03: Foreign-key integrity
# ============================================================

def test_dq03_invalid_foreign_key():
    child = pd.DataFrame({"company_id": [1, 2, 99]})
    parent = pd.DataFrame({"company_id": [1, 2, 3]})
    failures = []

    validate_fk_integrity(
        child,
        parent,
        "profitandloss",
        failures,
    )

    assert any(f["rule_id"] == "DQ-03" for f in failures)


def test_dq03_valid_foreign_keys():
    child = pd.DataFrame({"company_id": [1, 2]})
    parent = pd.DataFrame({"company_id": [1, 2, 3]})
    failures = []

    validate_fk_integrity(
        child,
        parent,
        "profitandloss",
        failures,
    )

    assert not any(f["rule_id"] == "DQ-03" for f in failures)


# ============================================================
# DQ-04: Balance-sheet balance < 1%
# ============================================================

def test_dq04_unbalanced_balance_sheet():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "total_assets": [1000],
            "total_liabilities": [600],
            "total_equity": [300],
        }
    )
    failures = []

    validate_balance_sheet(
        df,
        "balancesheet",
        failures,
    )

    assert any(f["rule_id"] == "DQ-04" for f in failures)


def test_dq04_balanced_balance_sheet():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "total_assets": [1000],
            "total_liabilities": [600],
            "total_equity": [400],
        }
    )
    failures = []

    validate_balance_sheet(
        df,
        "balancesheet",
        failures,
    )

    assert not any(f["rule_id"] == "DQ-04" for f in failures)


# ============================================================
# DQ-05: Operating profit margin cross-check
# ============================================================

def test_dq05_opm_mismatch():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "sales": [1000],
            "operating_profit": [200],
            "opm": [50],
        }
    )
    failures = []

    validate_opm(
        df,
        "profitandloss",
        failures,
    )

    assert any(f["rule_id"] == "DQ-05" for f in failures)


def test_dq05_correct_opm():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "sales": [1000],
            "operating_profit": [200],
            "opm": [20],
        }
    )
    failures = []

    validate_opm(
        df,
        "profitandloss",
        failures,
    )

    assert not any(f["rule_id"] == "DQ-05" for f in failures)


# ============================================================
# DQ-06: Positive sales
# ============================================================

def test_dq06_negative_sales():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "sales": [-100],
        }
    )
    failures = []

    validate_sales_positive(
        df,
        "profitandloss",
        failures,
    )

    assert any(f["rule_id"] == "DQ-06" for f in failures)


def test_dq06_positive_sales():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "sales": [100],
        }
    )
    failures = []

    validate_sales_positive(
        df,
        "profitandloss",
        failures,
    )

    assert not any(f["rule_id"] == "DQ-06" for f in failures)


# ============================================================
# DQ-07: Net cash consistency
# ============================================================

def test_dq07_net_cash_mismatch():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "cash": [500],
            "debt": [100],
            "net_cash": [999],
        }
    )
    failures = []

    validate_net_cash(
        df,
        "cashflow",
        failures,
    )

    assert any(f["rule_id"] == "DQ-07" for f in failures)


def test_dq07_correct_net_cash():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "cash": [500],
            "debt": [100],
            "net_cash": [400],
        }
    )
    failures = []

    validate_net_cash(
        df,
        "cashflow",
        failures,
    )

    assert not any(f["rule_id"] == "DQ-07" for f in failures)


# ============================================================
# DQ-08: Tax-rate sanity
# ============================================================

def test_dq08_invalid_tax_rate():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "tax_rate": [150],
        }
    )
    failures = []

    validate_tax_rate(
        df,
        "profitandloss",
        failures,
    )

    assert any(f["rule_id"] == "DQ-08" for f in failures)


def test_dq08_valid_tax_rate():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "tax_rate": [25],
        }
    )
    failures = []

    validate_tax_rate(
        df,
        "profitandloss",
        failures,
    )

    assert not any(f["rule_id"] == "DQ-08" for f in failures)


# ============================================================
# DQ-09: Dividend cap
# ============================================================

def test_dq09_dividend_cap():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "dividend_payout_ratio": [125],
        }
    )
    failures = []

    validate_dividend_cap(
        df,
        "analysis",
        failures,
    )

    assert any(f["rule_id"] == "DQ-09" for f in failures)


def test_dq09_valid_dividend_ratio():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "dividend_payout_ratio": [50],
        }
    )
    failures = []

    validate_dividend_cap(
        df,
        "analysis",
        failures,
    )

    assert not any(f["rule_id"] == "DQ-09" for f in failures)


# ============================================================
# DQ-10: URL validity
# ============================================================

def test_dq10_invalid_url():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "url": ["example.com"],
        }
    )
    failures = []

    validate_urls(
        df,
        "companies",
        failures,
    )

    assert any(f["rule_id"] == "DQ-10" for f in failures)


def test_dq10_valid_url():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "url": ["https://example.com"],
        }
    )
    failures = []

    validate_urls(
        df,
        "companies",
        failures,
    )

    assert not any(f["rule_id"] == "DQ-10" for f in failures)


# ============================================================
# DQ-11: EPS sign consistency
# ============================================================

def test_dq11_eps_sign_mismatch():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "eps": [10],
            "net_profit": [-100],
        }
    )
    failures = []

    validate_eps_sign(
        df,
        "profitandloss",
        failures,
    )

    assert any(f["rule_id"] == "DQ-11" for f in failures)


def test_dq11_eps_sign_consistent():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "eps": [10],
            "net_profit": [100],
        }
    )
    failures = []

    validate_eps_sign(
        df,
        "profitandloss",
        failures,
    )

    assert not any(f["rule_id"] == "DQ-11" for f in failures)


# ============================================================
# DQ-12: BSE balance check
# ============================================================

def test_dq12_negative_bse_balance():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "bse_assets": [-100],
            "bse_liabilities": [50],
        }
    )
    failures = []

    validate_bse_balance(
        df,
        "balancesheet",
        failures,
    )

    assert any(f["rule_id"] == "DQ-12" for f in failures)


def test_dq12_valid_bse_balance():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "bse_assets": [100],
            "bse_liabilities": [50],
        }
    )
    failures = []

    validate_bse_balance(
        df,
        "balancesheet",
        failures,
    )

    assert not any(f["rule_id"] == "DQ-12" for f in failures)


# ============================================================
# DQ-13: Year coverage
# ============================================================

def test_dq13_insufficient_year_coverage():
    df = pd.DataFrame(
        {
            "company_id": [1, 1, 1],
            "year": [2022, 2023, 2024],
        }
    )
    failures = []

    validate_year_coverage(
        df,
        "profitandloss",
        failures,
        minimum_years=5,
    )

    assert any(f["rule_id"] == "DQ-13" for f in failures)


def test_dq13_sufficient_year_coverage():
    df = pd.DataFrame(
        {
            "company_id": [1, 1, 1, 1, 1],
            "year": [2020, 2021, 2022, 2023, 2024],
        }
    )
    failures = []

    validate_year_coverage(
        df,
        "profitandloss",
        failures,
        minimum_years=5,
    )

    assert not any(f["rule_id"] == "DQ-13" for f in failures)


# ============================================================
# DQ-14: Company coverage
# ============================================================

def test_dq14_missing_company():
    df = pd.DataFrame(
        {
            "company_id": [1, 2],
        }
    )
    failures = []

    validate_company_coverage(
        df,
        expected_company_ids={1, 2, 3},
        table="profitandloss",
        failures=failures,
    )

    assert any(f["rule_id"] == "DQ-14" for f in failures)


def test_dq14_all_companies_present():
    df = pd.DataFrame(
        {
            "company_id": [1, 2, 3],
        }
    )
    failures = []

    validate_company_coverage(
        df,
        expected_company_ids={1, 2, 3},
        table="profitandloss",
        failures=failures,
    )

    assert not any(f["rule_id"] == "DQ-14" for f in failures)


# ============================================================
# DQ-15: Duplicate records
# ============================================================

def test_dq15_duplicate_rows():
    df = pd.DataFrame(
        {
            "company_id": [1, 1],
            "year": [2024, 2024],
            "sales": [1000, 1000],
        }
    )
    failures = []

    validate_duplicates(
        df,
        "profitandloss",
        failures,
    )

    assert any(f["rule_id"] == "DQ-15" for f in failures)


def test_dq15_no_duplicate_rows():
    df = pd.DataFrame(
        {
            "company_id": [1, 2],
            "year": [2024, 2024],
            "sales": [1000, 2000],
        }
    )
    failures = []

    validate_duplicates(
        df,
        "profitandloss",
        failures,
    )

    assert not any(f["rule_id"] == "DQ-15" for f in failures)


# ============================================================
# DQ-16: Required-field completeness
# ============================================================

def test_dq16_required_field_null():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "sales": [None],
        }
    )
    failures = []

    validate_required_fields(
        df,
        required_columns=["company_id", "year", "sales"],
        table="profitandloss",
        failures=failures,
    )

    assert any(f["rule_id"] == "DQ-16" for f in failures)


def test_dq16_required_fields_present():
    df = pd.DataFrame(
        {
            "company_id": [1],
            "year": [2024],
            "sales": [1000],
        }
    )
    failures = []

    validate_required_fields(
        df,
        required_columns=["company_id", "year", "sales"],
        table="profitandloss",
        failures=failures,
    )

    assert not any(f["rule_id"] == "DQ-16" for f in failures)


# ============================================================
# Integration test
# ============================================================

def test_valid_data_has_no_basic_failures():
    datasets = {
        "companies": pd.DataFrame(
            {
                "company_id": [1, 2],
            }
        ),
        "profitandloss": pd.DataFrame(
            {
                "company_id": [1, 2],
                "year": [2024, 2024],
                "sales": [1000, 2000],
                "operating_profit": [100, 200],
                "opm": [10, 10],
            }
        ),
    }

    result = validate_all(datasets)

    assert isinstance(result, pd.DataFrame)
    assert "rule_id" in result.columns
    assert "severity" in result.columns
    assert "table" in result.columns
    assert "message" in result.columns