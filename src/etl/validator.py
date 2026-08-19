"""
Data quality validator for the N100 Financial Intelligence Platform.

DQ-01  Primary-key uniqueness
DQ-02  (company_id, year) uniqueness
DQ-03  Foreign-key integrity
DQ-04  Balance-sheet balance < 1%
DQ-05  Operating profit margin cross-check
DQ-06  Positive sales
DQ-07  Net cash consistency
DQ-08  Tax-rate sanity
DQ-09  Dividend cap
DQ-10  URL validity
DQ-11  EPS sign consistency
DQ-12  BSE balance check
DQ-13  Year coverage
DQ-14  Company coverage
DQ-15  Duplicate records
DQ-16  Required-field completeness
"""

from pathlib import Path
from typing import Any

import pandas as pd


CRITICAL = "CRITICAL"
WARNING = "WARNING"


def add_failure(
    failures: list[dict[str, Any]],
    rule_id: str,
    severity: str,
    table: str,
    message: str,
    company_id: Any = None,
    year: Any = None,
) -> None:
    """Append one validation failure."""
    failures.append(
        {
            "rule_id": rule_id,
            "severity": severity,
            "table": table,
            "company_id": company_id,
            "year": year,
            "message": message,
        }
    )


def validate_pk_uniqueness(
    df: pd.DataFrame,
    key_columns: list[str],
    table: str,
    failures: list[dict[str, Any]],
) -> None:
    """DQ-01: Check primary-key uniqueness."""
    if not all(column in df.columns for column in key_columns):
        return

    duplicates = df[df.duplicated(subset=key_columns, keep=False)]

    for _, row in duplicates.iterrows():
        add_failure(
            failures,
            "DQ-01",
            CRITICAL,
            table,
            f"Duplicate primary key: {[row[column] for column in key_columns]}",
        )


def validate_company_year_pk(
    df: pd.DataFrame,
    table: str,
    failures: list[dict[str, Any]],
) -> None:
    """DQ-02: Check company_id + year uniqueness."""
    required = {"company_id", "year"}

    if not required.issubset(df.columns):
        return

    duplicates = df[df.duplicated(["company_id", "year"], keep=False)]

    for _, row in duplicates.iterrows():
        add_failure(
            failures,
            "DQ-02",
            WARNING,
            table,
            "Duplicate (company_id, year) combination",
            row["company_id"],
            row["year"],
        )


def validate_fk_integrity(
    child_df: pd.DataFrame,
    parent_df: pd.DataFrame,
    child_table: str,
    failures: list[dict[str, Any]],
    child_key: str = "company_id",
    parent_key: str = "company_id",
) -> None:
    """DQ-03: Check foreign-key integrity."""
    if child_key not in child_df.columns or parent_key not in parent_df.columns:
        return

    valid_keys = set(parent_df[parent_key].dropna())
    invalid_rows = child_df[
        child_df[child_key].notna() & ~child_df[child_key].isin(valid_keys)
    ]

    for _, row in invalid_rows.iterrows():
        add_failure(
            failures,
            "DQ-03",
            WARNING,  
            child_table,
            f"Invalid foreign key: {row[child_key]}",
            row.get("company_id"),
            row.get("year"),
        )


def validate_sales_positive(
    df: pd.DataFrame,
    table: str,
    failures: list[dict[str, Any]],
    column: str = "sales",
) -> None:
    """DQ-06: Sales must be positive."""
    if column not in df.columns:
        return

    invalid_rows = df[df[column].notna() & (df[column] <= 0)]

    for _, row in invalid_rows.iterrows():
        add_failure(
            failures,
            "DQ-06",
            WARNING,
            table,
            f"Sales must be positive, found {row[column]}",
            row.get("company_id"),
            row.get("year"),
)


def validate_balance_sheet(
    df: pd.DataFrame,
    table: str,
    failures: list[dict[str, Any]],
) -> None:
    """DQ-04: Check total assets vs total liabilities + equity."""
    required = {"total_assets", "total_liabilities", "total_equity"}

    if not required.issubset(df.columns):
        return

    for _, row in df.iterrows():
        assets = row["total_assets"]
        liabilities = row["total_liabilities"]
        equity = row["total_equity"]

        if pd.isna(assets) or pd.isna(liabilities) or pd.isna(equity):
            continue

        denominator = abs(assets)

        if denominator == 0:
            continue

        difference_pct = (
            abs(assets - (liabilities + equity)) / denominator
        ) * 100

        if difference_pct >= 1:
            add_failure(
                failures,
                "DQ-04",
                CRITICAL,
                table,
                f"Balance-sheet difference is {difference_pct:.2f}%",
                row.get("company_id"),
                row.get("year"),
            )


def validate_opm(
    df: pd.DataFrame,
    table: str,
    failures: list[dict[str, Any]],
) -> None:
    """DQ-05: Cross-check operating profit margin."""
    required = {"operating_profit", "sales", "opm"}

    if not required.issubset(df.columns):
        return

    for _, row in df.iterrows():
        sales = row["sales"]
        operating_profit = row["operating_profit"]
        reported_opm = row["opm"]

        if pd.isna(sales) or pd.isna(operating_profit) or pd.isna(reported_opm):
            continue

        if sales == 0:
            continue

        calculated_opm = (operating_profit / sales) * 100

        if abs(calculated_opm - reported_opm) > 1:
            add_failure(
                failures,
                "DQ-05",
                WARNING,
                table,
                (
                    f"OPM mismatch: reported={reported_opm:.2f}, "
                    f"calculated={calculated_opm:.2f}"
                ),
                row.get("company_id"),
                row.get("year"),
            )


def validate_net_cash(
    df: pd.DataFrame,
    table: str,
    failures: list[dict[str, Any]],
) -> None:
    """DQ-07: Check net-cash calculation when source columns exist."""
    required = {"cash", "debt", "net_cash"}

    if not required.issubset(df.columns):
        return

    for _, row in df.iterrows():
        cash = row["cash"]
        debt = row["debt"]
        net_cash = row["net_cash"]

        if any(pd.isna(value) for value in [cash, debt, net_cash]):
            continue

        calculated = cash - debt

        if abs(calculated - net_cash) > 1:
            add_failure(
                failures,
                "DQ-07",
                WARNING,
                table,
                f"Net cash mismatch: reported={net_cash}, calculated={calculated}",
                row.get("company_id"),
                row.get("year"),
            )


def validate_tax_rate(
    df: pd.DataFrame,
    table: str,
    failures: list[dict[str, Any]],
) -> None:
    """DQ-08: Tax rate should be within a reasonable range."""
    if "tax_rate" not in df.columns:
        return

    invalid_rows = df[
        df["tax_rate"].notna()
        & ((df["tax_rate"] < -100) | (df["tax_rate"] > 100))
    ]

    for _, row in invalid_rows.iterrows():
        add_failure(
            failures,
            "DQ-08",
            WARNING,
            table,
            f"Tax rate outside expected range: {row['tax_rate']}",
            row.get("company_id"),
            row.get("year"),
        )


def validate_dividend_cap(
    df: pd.DataFrame,
    table: str,
    failures: list[dict[str, Any]],
) -> None:
    """DQ-09: Dividend should not exceed a reasonable cap."""
    if "dividend_payout_ratio" not in df.columns:
        return

    invalid_rows = df[
        df["dividend_payout_ratio"].notna()
        & (df["dividend_payout_ratio"] > 100)
    ]

    for _, row in invalid_rows.iterrows():
        add_failure(
            failures,
            "DQ-09",
            WARNING,
            table,
            f"Dividend payout ratio exceeds 100%: {row['dividend_payout_ratio']}",
            row.get("company_id"),
            row.get("year"),
        )


def validate_urls(
    df: pd.DataFrame,
    table: str,
    failures: list[dict[str, Any]],
    column: str = "url",
) -> None:
    """DQ-10: Basic URL format validation."""
    if column not in df.columns:
        return

    for _, row in df.iterrows():
        value = row[column]

        if pd.isna(value) or not str(value).strip():
            continue

        text = str(value).strip().lower()

        if not text.startswith(("http://", "https://")):
            add_failure(
                failures,
                "DQ-10",
                WARNING,
                table,
                f"Invalid URL format: {value}",
                row.get("company_id"),
                row.get("year"),
            )


def validate_eps_sign(
    df: pd.DataFrame,
    table: str,
    failures: list[dict[str, Any]],
) -> None:
    """DQ-11: EPS should match the sign of net profit."""
    required = {"eps", "net_profit"}

    if not required.issubset(df.columns):
        return

    for _, row in df.iterrows():
        eps = row["eps"]
        net_profit = row["net_profit"]

        if pd.isna(eps) or pd.isna(net_profit):
            continue

        if (eps > 0 and net_profit < 0) or (eps < 0 and net_profit > 0):
            add_failure(
                failures,
                "DQ-11",
                WARNING,
                table,
                f"EPS sign inconsistent with net profit: EPS={eps}, profit={net_profit}",
                row.get("company_id"),
                row.get("year"),
            )


def validate_bse_balance(
    df: pd.DataFrame,
    table: str,
    failures: list[dict[str, Any]],
) -> None:
    """DQ-12: Validate BSE values when a BSE balance column exists."""
    required = {"bse_assets", "bse_liabilities"}

    if not required.issubset(df.columns):
        return

    for _, row in df.iterrows():
        assets = row["bse_assets"]
        liabilities = row["bse_liabilities"]

        if pd.isna(assets) or pd.isna(liabilities):
            continue

        if assets < 0 or liabilities < 0:
            add_failure(
                failures,
                "DQ-12",
                WARNING,
                table,
                "BSE balance values must not be negative",
                row.get("company_id"),
                row.get("year"),
            )


def validate_year_coverage(
    df: pd.DataFrame,
    table: str,
    failures: list[dict[str, Any]],
    minimum_years: int = 5,
) -> None:
    """DQ-13: Flag companies with fewer than the required years."""
    if not {"company_id", "year"}.issubset(df.columns):
        return

    counts = df.groupby("company_id")["year"].nunique()

    for company_id, year_count in counts.items():
        if year_count < minimum_years:
            add_failure(
                failures,
                "DQ-13",
                WARNING,
                table,
                f"Company has only {year_count} years of data",
                company_id,
            )


def validate_company_coverage(
    df: pd.DataFrame,
    expected_company_ids: set[Any],
    table: str,
    failures: list[dict[str, Any]],
) -> None:
    """DQ-14: Check expected company coverage."""
    if "company_id" not in df.columns:
        return

    actual_ids = set(df["company_id"].dropna())
    missing = expected_company_ids - actual_ids

    for company_id in sorted(missing, key=str):
        add_failure(
            failures,
            "DQ-14",
            WARNING,
            table,
            "Company missing from dataset",
            company_id,
        )


def validate_duplicates(
    df: pd.DataFrame,
    table: str,
    failures: list[dict[str, Any]],
) -> None:
    """DQ-15: Detect fully duplicated rows."""
    duplicates = df[df.duplicated(keep=False)]

    for index in duplicates.index:
        row = df.loc[index]

        add_failure(
            failures,
            "DQ-15",
            WARNING,
            table,
            "Duplicate row detected",
            row.get("company_id"),
            row.get("year"),
        )


def validate_required_fields(
    df: pd.DataFrame,
    required_columns: list[str],
    table: str,
    failures: list[dict[str, Any]],
) -> None:
    """DQ-16: Check required fields for null values."""
    existing_columns = [
        column for column in required_columns if column in df.columns
    ]

    if not existing_columns:
        return

    for column in existing_columns:
        null_rows = df[df[column].isna()]

        for _, row in null_rows.iterrows():
            add_failure(
                failures,
                "DQ-16",
                CRITICAL,
                table,
                f"Required field is NULL: {column}",
                row.get("company_id"),
                row.get("year"),
            )


def validate_all(
    datasets: dict[str, pd.DataFrame],
    output_path: str | Path = "output/validation_failures.csv",
) -> pd.DataFrame:
    """
    Run the available data-quality checks.

    DQ-02 is applied only to tables where (company_id, year)
    is intended to be unique.
    """
    failures: list[dict[str, Any]] = []

    companies = datasets.get("companies")

    company_year_unique_tables = {
        "profitandloss",
        "balancesheet",
        "cashflow",
    }

    for table_name, df in datasets.items():
        # DQ-01: primary-key uniqueness for companies.
        if "id" in df.columns:
         validate_pk_uniqueness(
        df,
        ["id"],
        table_name,
        failures,
    )

        # DQ-02: company + year uniqueness only for selected tables.
        if (
            table_name in company_year_unique_tables
            and {"company_id", "year"}.issubset(df.columns)
        ):
            validate_company_year_pk(
                df,
                table_name,
                failures,
            )

        # DQ-15: duplicate full rows.
        validate_duplicates(
            df,
            table_name,
            failures,
        )

        # DQ-10: URL validation.
        validate_urls(
            df,
            table_name,
            failures,
        )

        # DQ-08: tax-rate sanity.
        validate_tax_rate(
            df,
            table_name,
            failures,
        )

        # DQ-09: dividend cap.
        validate_dividend_cap(
            df,
            table_name,
            failures,
        )

        # DQ-11: EPS sign consistency.
        validate_eps_sign(
            df,
            table_name,
            failures,
        )

        # DQ-12: BSE balance check.
        validate_bse_balance(
            df,
            table_name,
            failures,
        )

        # DQ-06 and DQ-05 for P&L.
        if table_name == "profitandloss":
            validate_sales_positive(
                df,
                table_name,
                failures,
            )

            validate_opm(
                df,
                table_name,
                failures,
            )

        # DQ-04 for balance sheet.
        if table_name == "balancesheet":
            validate_balance_sheet(
                df,
                table_name,
                failures,
            )

        # DQ-07 for cash flow.
        if table_name == "cashflow":
            validate_net_cash(
                df,
                table_name,
                failures,
            )

        # DQ-13: year coverage.
        if {"company_id", "year"}.issubset(df.columns):
            validate_year_coverage(
                df,
                table_name,
                failures,
            )

    # DQ-03 and DQ-14 against companies table.
    if companies is not None and "id" in companies.columns:
        expected_ids = set(companies["id"].dropna())

        for table_name, df in datasets.items():
            if (
                table_name != "companies"
                and "company_id" in df.columns
            ):
                validate_fk_integrity(
                    df,
                    companies,
                    table_name,
                    failures,
                    child_key="company_id",
                    parent_key="id",
                )

                validate_company_coverage(
                    df,
                    expected_ids,
                    table_name,
                    failures,
                )

    # Build the result.
    result = pd.DataFrame(
        failures,
        columns=[
            "rule_id",
            "severity",
            "table",
            "company_id",
            "year",
            "message",
        ],
    )

    output = Path(output_path)
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        output,
        index=False,
    )

    return result
    

if __name__ == "__main__":
    print("N100 data-quality validator is ready.")