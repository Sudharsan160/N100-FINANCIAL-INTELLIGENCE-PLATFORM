from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"

CAPITAL_FILE = OUTPUT_DIR / "capital_allocation.csv"
CASHFLOW_FILE = OUTPUT_DIR / "cashflow_intelligence.xlsx"
PATTERN_CHANGES_FILE = OUTPUT_DIR / "pattern_changes.csv"


PATTERN_MAP = {
    "+--": "Self-Funded Growth",
    "+-+": "Growth + External Funding",
    "++-": "Shareholder Returns",
    "+++": "Cash Accumulator",
    "-+-": "Distress / Funding Need",
    "-++": "Asset Monetisation",
    "--+": "Cash Burn",
    "---": "Restructuring",
}


def load_capital_allocation() -> pd.DataFrame:
    if not CAPITAL_FILE.exists():
        raise FileNotFoundError(f"Missing file: {CAPITAL_FILE}")

    df = pd.read_csv(CAPITAL_FILE)

    required = {
        "company_id",
        "year",
        "cfo_cr",
        "cfi_cr",
        "cff_cr",
        "free_cash_flow_cr",
        "pattern_code",
        "pattern_label",
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"capital_allocation.csv is missing columns: {sorted(missing)}"
        )

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    return df


def classify_eight_pattern(row: pd.Series) -> str:
    """
    Classify the sign pattern into the Sprint 5 eight-pattern framework.
    """

    cfo = row["cfo_cr"]
    cfi = row["cfi_cr"]
    cff = row["cff_cr"]

    if pd.isna(cfo) or pd.isna(cfi) or pd.isna(cff):
        return "Data Unavailable"

    signs = (
        "+" if cfo > 0 else "-" if cfo < 0 else "0",
        "+" if cfi > 0 else "-" if cfi < 0 else "0",
        "+" if cff > 0 else "-" if cff < 0 else "0",
    )

    code = "".join(signs)

    # Explicit handling for zero cases.
    if "0" in code:
        if cfo > 0 and cfi < 0 and cff == 0:
            return "Self-Funded Growth"
        if cfo > 0 and cfi > 0 and cff == 0:
            return "Cash Accumulator"
        if cfo > 0 and cfi == 0 and cff > 0:
            return "Growth + External Funding"
        if cfo < 0 and cfi < 0 and cff > 0:
            return "Distress / Funding Need"
        return "Data Unavailable"

    return PATTERN_MAP.get(code, "Data Unavailable")


def build_latest_patterns(capital: pd.DataFrame) -> pd.DataFrame:
    latest_year = capital["year"].max()

    latest = capital[capital["year"] == latest_year].copy().sort_values("company_id")

    latest["capital_allocation"] = latest.apply(
        classify_eight_pattern,
        axis=1,
    )

    return latest


def build_pattern_changes(capital: pd.DataFrame) -> pd.DataFrame:
    """
    Compare each company's two most recent available observations.
    This avoids assuming every company has a complete historical series.
    """

    records = []

    capital = capital.sort_values(["company_id", "year"]).copy()

    for company_id, group in capital.groupby("company_id", sort=True):
        group = group.dropna(subset=["year"]).sort_values("year")

        if len(group) < 2:
            continue

        previous = group.iloc[-2]
        latest = group.iloc[-1]

        previous_pattern = classify_eight_pattern(previous)
        latest_pattern = classify_eight_pattern(latest)

        records.append(
            {
                "company_id": company_id,
                "previous_year": int(previous["year"]),
                "latest_year": int(latest["year"]),
                "previous_pattern": previous_pattern,
                "latest_pattern": latest_pattern,
                "pattern_changed": previous_pattern != latest_pattern,
                "previous_pattern_code": previous.get("pattern_code", None),
                "latest_pattern_code": latest.get("pattern_code", None),
            }
        )

    return pd.DataFrame(records)


def add_capital_allocation_to_cashflow(
    cashflow: pd.DataFrame,
    latest_patterns: pd.DataFrame,
) -> pd.DataFrame:

    if "company_id" not in cashflow.columns:
        raise ValueError("cashflow_intelligence.xlsx must contain company_id")

    allocation_map = latest_patterns[
        ["company_id", "capital_allocation"]
    ].drop_duplicates("company_id")

    result = cashflow.drop(
        columns=["capital_allocation"],
        errors="ignore",
    ).merge(
        allocation_map,
        on="company_id",
        how="left",
    )

    return result


def validate_results(
    capital: pd.DataFrame,
    latest_patterns: pd.DataFrame,
    cashflow: pd.DataFrame,
    pattern_changes: pd.DataFrame,
) -> None:

    total_companies = capital["company_id"].nunique()
    latest_year = int(capital["year"].max())
    latest_companies = latest_patterns["company_id"].nunique()

    print("\n=== DAY 32 VALIDATION ===")
    print(f"Historical rows: {len(capital)}")
    print(f"Historical companies: {total_companies}")
    print(f"Latest year: {latest_year}")
    print(f"Latest-year companies: {latest_companies}")

    print("\nCompany coverage by year:")
    coverage = capital.groupby("year")["company_id"].nunique().sort_index()
    print(coverage.to_string())

    expected_companies = 92

    if total_companies != expected_companies:
        raise ValueError(f"Expected 92 companies, found {total_companies}")

    if latest_companies != expected_companies:
        raise ValueError(
            f"Latest year should contain 92 companies, " f"found {latest_companies}"
        )

    print("\nLatest-year pattern distribution:")
    print(latest_patterns["capital_allocation"].value_counts(dropna=False).to_string())

    print("\nCashflow intelligence rows:", len(cashflow))

    if "capital_allocation" not in cashflow.columns:
        raise ValueError("capital_allocation column was not added")

    missing_allocations = int(cashflow["capital_allocation"].isna().sum())

    print(
        "Companies without capital allocation:",
        missing_allocations,
    )

    if missing_allocations:
        missing_ids = cashflow.loc[
            cashflow["capital_allocation"].isna(),
            "company_id",
        ].tolist()

        print("Missing company IDs:", missing_ids)

    print(
        "\nPattern-change rows:",
        len(pattern_changes),
    )

    print(
        "Pattern changes:",
        (
            int(pattern_changes["pattern_changed"].sum())
            if not pattern_changes.empty
            else 0
        ),
    )

    print(
        "No pattern changes:",
        (
            int((~pattern_changes["pattern_changed"]).sum())
            if not pattern_changes.empty
            else 0
        ),
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    capital = load_capital_allocation()

    # Day 32 requirement:
    # Use all available historical observations and document
    # coverage instead of creating fake missing rows.
    coverage = (
        capital.groupby("year")["company_id"]
        .nunique()
        .rename("company_count")
        .reset_index()
    )

    coverage.to_csv(
        OUTPUT_DIR / "capital_allocation_coverage.csv",
        index=False,
    )

    latest_patterns = build_latest_patterns(capital)

    # Read the Day 31 workbook.
    if not CASHFLOW_FILE.exists():
        raise FileNotFoundError(f"Missing file: {CASHFLOW_FILE}")

    cashflow = pd.read_excel(CASHFLOW_FILE)

    updated_cashflow = add_capital_allocation_to_cashflow(
        cashflow,
        latest_patterns,
    )

    # Preserve the same Excel file with the new column.
    updated_cashflow.to_excel(
        CASHFLOW_FILE,
        index=False,
    )

    pattern_changes = build_pattern_changes(capital)

    pattern_changes.to_csv(
        PATTERN_CHANGES_FILE,
        index=False,
    )

    validate_results(
        capital,
        latest_patterns,
        updated_cashflow,
        pattern_changes,
    )

    print("\nSaved:")
    print(f"- {CASHFLOW_FILE}")
    print(f"- {PATTERN_CHANGES_FILE}")
    print(f"- {OUTPUT_DIR / 'capital_allocation_coverage.csv'}")


if __name__ == "__main__":
    main()
