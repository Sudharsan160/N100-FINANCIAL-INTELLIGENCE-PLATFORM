import sqlite3
from pathlib import Path

import pandas as pd

from src.reports.tearsheet import generate_tearsheet

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "nifty100.db"
OUTPUT_DIR = ROOT / "reports" / "tearsheets"
SKIPPED_FILE = ROOT / "output" / "skipped_tearsheets.csv"
FAILURE_FILE = ROOT / "output" / "tearsheet_failures.csv"


def load_companies():
    conn = sqlite3.connect(DB_PATH)

    try:
        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            ORDER BY id
            """,
            conn,
        )

        years = pd.read_sql_query(
            """
            SELECT
                company_id,
                COUNT(DISTINCT year) AS financial_years
            FROM financial_ratios
            GROUP BY company_id
            """,
            conn,
        )

    finally:
        conn.close()

    result = companies.merge(
        years,
        on="company_id",
        how="left",
    )

    result["financial_years"] = result["financial_years"].fillna(0).astype(int)

    return result


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    companies = load_companies()

    print("=== DAY 34 TEARSHEET BATCH ===")
    print(f"Total companies: {len(companies)}")
    print("Minimum-history filter: DISABLED")
    print("Generating all companies, including short-history companies.\n")

    # The original Sprint 5 implementation skipped short-history companies.
    # Current DoD explicitly requires all 92 company PDFs, so every company
    # is attempted and missing historical values are shown as N/A.

    successes = []
    failures = []

    for _, row in companies.iterrows():
        ticker = str(row["company_id"])

        try:
            output = generate_tearsheet(ticker)

            successes.append(ticker)

            print(f"[OK] {ticker}: {output.name}")

        except Exception as exc:  # noqa: BLE001
            failures.append(
                {
                    "company_id": ticker,
                    "company_name": row["company_name"],
                    "financial_years": row["financial_years"],
                    "error": str(exc),
                }
            )

            print(f"[ERROR] {ticker}: {exc}")

    # No companies are intentionally skipped in this version.
    pd.DataFrame(
        columns=[
            "company_id",
            "company_name",
            "financial_years",
            "reason",
        ]
    ).to_csv(
        SKIPPED_FILE,
        index=False,
    )

    pd.DataFrame(failures).to_csv(
        FAILURE_FILE,
        index=False,
    )

    print("\n=== FINAL BATCH RESULT ===")
    print(f"Total companies: {len(companies)}")
    print(f"Generated: {len(successes)}")
    print(f"Failed: {len(failures)}")
    print("Skipped: 0")

    print(f"\nSkipped file: {SKIPPED_FILE}")

    print(f"Failure file: {FAILURE_FILE}")


if __name__ == "__main__":
    main()
