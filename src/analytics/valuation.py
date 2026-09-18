from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "nifty100.db"
OUTPUT_DIR = ROOT_DIR / "output"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load valuation, FCF, and sector data from SQLite."""

    with sqlite3.connect(str(DB_PATH)) as conn:

        market = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                market_cap_crore,
                pe_ratio,
                pb_ratio,
                ev_ebitda
            FROM market_cap
            """,
            conn,
        )

        ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                free_cash_flow_cr
            FROM financial_ratios
            """,
            conn,
        )

        sectors = pd.read_sql_query(
            """
            SELECT
                company_id,
                broad_sector
            FROM sectors
            """,
            conn,
        )

    return market, ratios, sectors


def calculate_valuation() -> pd.DataFrame:
    """
    Calculate valuation metrics and sector-relative P/E flags
    for the latest available year.
    """

    market, ratios, sectors = load_data()

    # -----------------------------------------------------
    # Numeric conversion
    # -----------------------------------------------------
    for column in [
        "market_cap_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
    ]:
        market[column] = pd.to_numeric(
            market[column],
            errors="coerce",
        )

    ratios["free_cash_flow_cr"] = pd.to_numeric(
        ratios["free_cash_flow_cr"],
        errors="coerce",
    )

    market["year"] = pd.to_numeric(
        market["year"],
        errors="coerce",
    )

    ratios["year"] = pd.to_numeric(
        ratios["year"],
        errors="coerce",
    )

    # -----------------------------------------------------
    # Latest market data
    # -----------------------------------------------------
    latest_year = int(market["year"].max())

    latest_market = market[market["year"] == latest_year].copy()

    # -----------------------------------------------------
    # Latest FCF for each company/year
    # -----------------------------------------------------
    latest_fcf = ratios[ratios["year"] == latest_year][
        [
            "company_id",
            "free_cash_flow_cr",
        ]
    ].copy()

    # -----------------------------------------------------
    # Sector mapping
    # -----------------------------------------------------
    sectors = sectors[
        [
            "company_id",
            "broad_sector",
        ]
    ].drop_duplicates("company_id")

    # -----------------------------------------------------
    # Build latest-company dataset
    # -----------------------------------------------------
    result = latest_market.merge(
        latest_fcf,
        on="company_id",
        how="left",
    )

    result = result.merge(
        sectors,
        on="company_id",
        how="left",
    )

    # -----------------------------------------------------
    # Company name
    # -----------------------------------------------------
    with sqlite3.connect(str(DB_PATH)) as conn:
        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            """,
            conn,
        )

    result = result.merge(
        companies,
        on="company_id",
        how="left",
    )

    # -----------------------------------------------------
    # FCF Yield
    # -----------------------------------------------------
    result["fcf_yield_pct"] = (
        result["free_cash_flow_cr"] / result["market_cap_crore"] * 100.0
    )

    result.loc[
        result["market_cap_crore"] <= 0,
        "fcf_yield_pct",
    ] = pd.NA

    # -----------------------------------------------------
    # Five-year median P/E
    #
    # Uses the latest 5 available years including latest year.
    # For 2024 this is 2020–2024.
    # -----------------------------------------------------
    five_year_start = latest_year - 4

    five_year_market = market[
        market["year"].between(
            five_year_start,
            latest_year,
        )
    ].copy()

    five_year_pe = (
        five_year_market.groupby("company_id")["pe_ratio"]
        .median()
        .rename("5yr_median_PE")
        .reset_index()
    )

    result = result.merge(
        five_year_pe,
        on="company_id",
        how="left",
    )

    # -----------------------------------------------------
    # Sector median P/E
    # -----------------------------------------------------
    sector_medians = (
        result.groupby("broad_sector")["pe_ratio"]
        .median()
        .rename("sector_median_pe")
        .reset_index()
    )

    result = result.merge(
        sector_medians,
        on="broad_sector",
        how="left",
    )

    # -----------------------------------------------------
    # P/E vs sector median
    # -----------------------------------------------------
    result["PE_vs_sector_median_pct"] = (
        (result["pe_ratio"] / result["sector_median_pe"]) - 1
    ) * 100.0

    # -----------------------------------------------------
    # Valuation flags
    # -----------------------------------------------------
    def valuation_flag(row) -> str:
        pe = row["pe_ratio"]
        sector_median = row["sector_median_pe"]

        if pd.isna(pe) or pd.isna(sector_median):
            return "Fair"

        if sector_median <= 0 or pe <= 0:
            return "Fair"

        if pe > sector_median * 1.5:
            return "Caution"

        if pe < sector_median * 0.7:
            return "Discount"

        return "Fair"

    result["flag"] = result.apply(
        valuation_flag,
        axis=1,
    )

    # -----------------------------------------------------
    # Final output columns
    # -----------------------------------------------------
    result = result[
        [
            "company_id",
            "company_name",
            "broad_sector",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "fcf_yield_pct",
            "5yr_median_PE",
            "PE_vs_sector_median_pct",
            "flag",
        ]
    ].copy()

    result = result.rename(
        columns={
            "pe_ratio": "P/E",
            "pb_ratio": "P/B",
            "ev_ebitda": "EV/EBITDA",
            "broad_sector": "sector",
        }
    )

    return result


def save_outputs(result: pd.DataFrame) -> None:
    """Save Excel summary and Caution/Discount CSV."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    excel_path = OUTPUT_DIR / "valuation_summary.xlsx"
    csv_path = OUTPUT_DIR / "valuation_flags.csv"

    # Full valuation summary
    result.to_excel(
        excel_path,
        index=False,
    )

    # Only non-Fair companies
    flags = result[
        result["flag"].isin(
            [
                "Caution",
                "Discount",
            ]
        )
    ].copy()

    flags.to_csv(
        csv_path,
        index=False,
    )

    print(f"Saved: {excel_path}")
    print(f"Saved: {csv_path}")
    print(f"Summary rows: {len(result)}")
    print(f"Flagged rows: {len(flags)}")


def main() -> None:
    """Run valuation calculation and export outputs."""

    result = calculate_valuation()

    print("\nValuation Summary")
    print("=" * 60)

    print(f"Companies: {result['company_id'].nunique()}")
    print(f"Rows: {len(result)}")

    print("\nFlags:")
    print(result["flag"].value_counts(dropna=False))

    print("\nTop FCF Yield:")
    print(
        result[
            [
                "company_id",
                "fcf_yield_pct",
                "flag",
            ]
        ]
        .sort_values(
            "fcf_yield_pct",
            ascending=False,
        )
        .head(10)
        .to_string(index=False)
    )

    save_outputs(result)


if __name__ == "__main__":
    main()
