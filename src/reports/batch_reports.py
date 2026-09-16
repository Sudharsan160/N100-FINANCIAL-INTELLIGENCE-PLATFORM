from pathlib import Path
import sqlite3

import pandas as pd

from src.reports.tearsheet import generate_tearsheet


ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "nifty100.db"
OUTPUT_DIR = ROOT / "reports" / "tearsheets"


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

    result["financial_years"] = (
        result["financial_years"]
        .fillna(0)
        .astype(int)
    )

    return result


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    companies = load_companies()

    skipped = companies[
        companies["financial_years"] < 3
    ].copy()

    eligible = companies[
        companies["financial_years"] >= 3
    ].copy()

    skipped_file = ROOT / "output" / "skipped_tearsheets.csv"

    if skipped.empty:
        skipped.to_csv(
            skipped_file,
            index=False,
        )
    else:
        skipped.to_csv(
            skipped_file,
            index=False,
        )

    print("=== DAY 34 TEARSHEET BATCH ===")
    print(f"Total companies: {len(companies)}")
    print(f"Eligible companies: {len(eligible)}")
    print(f"Skipped companies: {len(skipped)}")

    if not skipped.empty:
        print("\nSkipped:")
        print(
            skipped[
                [
                    "company_id",
                    "company_name",
                    "financial_years",
                ]
            ].to_string(index=False)
        )

    success = []
    failures = []

    print("\nGenerating PDFs...\n")

    for _, row in eligible.iterrows():
        ticker = str(row["company_id"])

        try:
            output = generate_tearsheet(ticker)

            success.append(ticker)

            print(
                f"[OK] {ticker}: {output.name}"
            )

        except Exception as exc:
            failures.append(
                {
                    "company_id": ticker,
                    "error": str(exc),
                }
            )

            print(
                f"[ERROR] {ticker}: {exc}"
            )

    failure_file = (
        ROOT
        / "output"
        / "tearsheet_failures.csv"
    )

    pd.DataFrame(
        failures
    ).to_csv(
        failure_file,
        index=False,
    )

    print("\n=== FINAL BATCH RESULT ===")
    print(f"Generated: {len(success)}")
    print(f"Failed: {len(failures)}")
    print(f"Skipped: {len(skipped)}")

    print(
        f"\nSkipped file: {skipped_file}"
    )

    print(
        f"Failure file: {failure_file}"
    )


if __name__ == "__main__":
    main()