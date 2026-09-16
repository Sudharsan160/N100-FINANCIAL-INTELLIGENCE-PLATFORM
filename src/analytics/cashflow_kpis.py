from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "nifty100.db"
OUTPUT_DIR = ROOT_DIR / "output"

INTELLIGENCE_PATH = OUTPUT_DIR / "cashflow_intelligence.xlsx"
DISTRESS_PATH = OUTPUT_DIR / "distress_alerts.csv"


Number = float | int | None


def safe_divide(
    numerator: Number,
    denominator: Number,
) -> Optional[float]:
    """Safely divide two numeric values."""
    if numerator is None or denominator is None:
        return None

    try:
        numerator = float(numerator)
        denominator = float(denominator)
    except (TypeError, ValueError):
        return None

    if denominator == 0:
        return None

    return numerator / denominator


def cfo_quality(
    operating_cash_flow: Number,
    net_profit: Number,
) -> Optional[float]:
    """CFO / PAT."""
    return safe_divide(
        operating_cash_flow,
        net_profit,
    )


def capex_intensity(
    capital_expenditure: Number,
    revenue: Number,
) -> Optional[float]:
    """|CapEx| / Revenue × 100."""
    if capital_expenditure is None:
        return None

    value = safe_divide(
        abs(float(capital_expenditure)),
        revenue,
    )

    return None if value is None else value * 100.0


def free_cash_flow_conversion(
    free_cash_flow: Number,
    ebitda: Number,
) -> Optional[float]:
    """FCF / EBITDA × 100."""
    value = safe_divide(
        free_cash_flow,
        ebitda,
    )

    return None if value is None else value * 100.0


def classify_cfo_quality(score: Number) -> str:
    """Classify average 5Y CFO/PAT."""
    if score is None or pd.isna(score):
        return "N/A"

    score = float(score)

    if score > 1.0:
        return "High Quality"
    if score >= 0.5:
        return "Moderate"
    return "Accrual Risk"


def classify_capex_intensity(value: Number) -> str:
    """Classify CapEx intensity."""
    if value is None or pd.isna(value):
        return "N/A"

    value = float(value)

    if value < 3:
        return "Asset Light"
    if value <= 8:
        return "Moderate"
    return "Capital Intensive"


def classify_capital_allocation(
    cfo: Number,
    cfi: Number,
    cff: Number,
) -> str:
    """
    Eight cash-flow sign patterns.

    + CFO, - CFI, - CFF -> Self-Funded Growth
    + CFO, - CFI, + CFF -> Growth + External Funding
    + CFO, + CFI, - CFF -> Shareholder Returns
    + CFO, + CFI, + CFF -> Cash Accumulator
    - CFO, - CFI, + CFF -> Distress / Funding Need
    - CFO, + CFI, + CFF -> Asset Monetisation
    - CFO, - CFI, - CFF -> Cash Burn
    - CFO, + CFI, - CFF -> Restructuring
    """

    if pd.isna(cfo) or pd.isna(cfi) or pd.isna(cff):
        return "Data Unavailable"

    if cfo > 0 and cfi < 0 and cff < 0:
        return "Self-Funded Growth"

    if cfo > 0 and cfi < 0 and cff > 0:
        return "Growth + External Funding"

    if cfo > 0 and cfi > 0 and cff < 0:
        return "Shareholder Returns"

    if cfo > 0 and cfi > 0 and cff > 0:
        return "Cash Accumulator"

    if cfo < 0 and cfi < 0 and cff > 0:
        return "Distress / Funding Need"

    if cfo < 0 and cfi > 0 and cff > 0:
        return "Asset Monetisation"

    if cfo < 0 and cfi < 0 and cff < 0:
        return "Cash Burn"

    if cfo < 0 and cfi > 0 and cff < 0:
        return "Restructuring"

    return "Mixed"


def load_data():
    """Load all Day 31 source data."""

    with sqlite3.connect(str(DB_PATH)) as conn:
        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            ORDER BY company_name
            """,
            conn,
        )

        sectors = pd.read_sql_query(
            """
            SELECT
                company_id,
                broad_sector AS sector
            FROM sectors
            """,
            conn,
        )

        cashflow = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                operating_activity AS cfo,
                investing_activity AS cfi,
                financing_activity AS cff
            FROM cashflow
            ORDER BY company_id, year
            """,
            conn,
        )

        pnl = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                sales,
                operating_profit,
                depreciation,
                net_profit
            FROM profitandloss
            ORDER BY company_id, year
            """,
            conn,
        )

        ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                free_cash_flow_cr,
                cash_from_operations_cr,
                revenue_growth_pct,
                debt_to_equity
            FROM financial_ratios
            ORDER BY company_id, year
            """,
            conn,
        )

        balancesheet = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                borrowings
            FROM balancesheet
            ORDER BY company_id, year
            """,
            conn,
        )

    composite_path = OUTPUT_DIR / "composite_scores.csv"

    if composite_path.exists():
        composite = pd.read_csv(composite_path)
    else:
        composite = pd.DataFrame()

    return (
        companies,
        sectors,
        cashflow,
        pnl,
        ratios,
        balancesheet,
        composite,
    )


def prepare_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Convert selected columns to numeric safely."""
    result = df.copy()

    for column in columns:
        if column in result.columns:
            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            )

    return result


def latest_two(
    df: pd.DataFrame,
    company_id: str,
) -> tuple[pd.Series | None, pd.Series | None]:
    """Return latest and previous rows for a company."""
    subset = df[
        df["company_id"].astype(str) == str(company_id)
    ].copy()

    if subset.empty:
        return None, None

    subset = subset.sort_values("year")

    latest = subset.iloc[-1]

    previous = (
        subset.iloc[-2]
        if len(subset) >= 2
        else None
    )

    return latest, previous


def fcf_cagr_5yr(
    company_ratio_history: pd.DataFrame,
) -> Optional[float]:
    """
    Calculate 5Y FCF CAGR from the financial_ratios history.

    Uses latest year and the value five years earlier.
    """

    if company_ratio_history.empty:
        return None

    history = company_ratio_history.sort_values("year").copy()

    history["year"] = pd.to_numeric(
        history["year"],
        errors="coerce",
    )

    history["free_cash_flow_cr"] = pd.to_numeric(
        history["free_cash_flow_cr"],
        errors="coerce",
    )

    history = history.dropna(
        subset=["year", "free_cash_flow_cr"]
    )

    if history.empty:
        return None

    latest_year = int(history["year"].max())
    start_year = latest_year - 5

    start_rows = history[
        history["year"] == start_year
    ]

    end_rows = history[
        history["year"] == latest_year
    ]

    if start_rows.empty or end_rows.empty:
        return None

    start_value = float(
        start_rows.iloc[-1]["free_cash_flow_cr"]
    )
    end_value = float(
        end_rows.iloc[-1]["free_cash_flow_cr"]
    )

    if start_value <= 0 or end_value < 0:
        return None

    return (
        (end_value / start_value) ** (1 / 5) - 1
    ) * 100.0


def calculate_company(
    company_id: str,
    sector: str,
    cashflow: pd.DataFrame,
    pnl: pd.DataFrame,
    ratios: pd.DataFrame,
    balancesheet: pd.DataFrame,
    composite: pd.DataFrame,
) -> dict:
    """Calculate Day 31 metrics for one company."""

    company_cf = cashflow[
        cashflow["company_id"].astype(str) == str(company_id)
    ].copy()

    company_pl = pnl[
        pnl["company_id"].astype(str) == str(company_id)
    ].copy()

    company_ratios = ratios[
        ratios["company_id"].astype(str) == str(company_id)
    ].copy()

    company_bs = balancesheet[
        balancesheet["company_id"].astype(str) == str(company_id)
    ].copy()

    # -----------------------------------------------------
    # Numeric conversion
    # -----------------------------------------------------
    company_cf = prepare_numeric(
        company_cf,
        ["year", "cfo", "cfi", "cff"],
    )

    company_pl = prepare_numeric(
        company_pl,
        [
            "year",
            "sales",
            "operating_profit",
            "depreciation",
            "net_profit",
        ],
    )

    company_ratios = prepare_numeric(
        company_ratios,
        [
            "year",
            "free_cash_flow_cr",
            "cash_from_operations_cr",
            "revenue_growth_pct",
            "debt_to_equity",
        ],
    )

    company_bs = prepare_numeric(
        company_bs,
        ["year", "borrowings"],
    )

    # -----------------------------------------------------
    # 5-year CFO/PAT average
    # -----------------------------------------------------
    merged = company_cf.merge(
        company_pl[
            [
                "company_id",
                "year",
                "net_profit",
            ]
        ],
        on=["company_id", "year"],
        how="left",
    )

    merged["cfo_pat_ratio"] = merged.apply(
        lambda row: safe_divide(
            row["cfo"],
            row["net_profit"],
        ),
        axis=1,
    )

    five_year = (
        merged.sort_values("year")
        .dropna(subset=["year"])
        .tail(5)
    )

    cfo_quality_score = (
        five_year["cfo_pat_ratio"].mean()
        if not five_year.empty
        else None
    )

    cfo_quality_label = classify_cfo_quality(
        cfo_quality_score
    )

    # -----------------------------------------------------
    # Latest cash-flow year
    # -----------------------------------------------------
    latest_cf, previous_cf = latest_two(
        company_cf,
        company_id,
    )

    if latest_cf is None:
        latest_cfo = None
        latest_cfi = None
        latest_cff = None
        latest_year = None
    else:
        latest_cfo = latest_cf["cfo"]
        latest_cfi = latest_cf["cfi"]
        latest_cff = latest_cf["cff"]
        latest_year = latest_cf["year"]

    # -----------------------------------------------------
    # Latest revenue + EBITDA
    # -----------------------------------------------------
    latest_pl, _ = latest_two(
        company_pl,
        company_id,
    )

    if latest_pl is None:
        latest_sales = None
        latest_ebitda = None
        latest_net_profit = None
    else:
        latest_sales = latest_pl["sales"]
        latest_net_profit = latest_pl["net_profit"]

        operating_profit = latest_pl["operating_profit"]
        depreciation = latest_pl["depreciation"]

        if pd.notna(operating_profit):
            depreciation_value = (
                0.0
                if pd.isna(depreciation)
                else float(depreciation)
            )

            latest_ebitda = (
                float(operating_profit)
                + abs(depreciation_value)
            )
        else:
            latest_ebitda = None

    # -----------------------------------------------------
    # CapEx intensity
    #
    # Sprint specification says:
    # abs(investing_activity) / sales * 100
    # -----------------------------------------------------
    capex_intensity_pct = safe_divide(
        abs(float(latest_cfi))
        if latest_cfi is not None and pd.notna(latest_cfi)
        else None,
        latest_sales,
    )

    if capex_intensity_pct is not None:
        capex_intensity_pct *= 100.0

    capex_label = classify_capex_intensity(
        capex_intensity_pct
    )

    # -----------------------------------------------------
    # FCF conversion = FCF / EBITDA × 100
    # -----------------------------------------------------
    latest_ratio, _ = latest_two(
        company_ratios,
        company_id,
    )

    if latest_ratio is not None:
        latest_fcf = latest_ratio["free_cash_flow_cr"]
    else:
        latest_fcf = None

    fcf_conversion_pct = free_cash_flow_conversion(
        latest_fcf,
        latest_ebitda,
    )

    # -----------------------------------------------------
    # 5Y FCF CAGR
    # -----------------------------------------------------
    fcf_cagr = fcf_cagr_5yr(
        company_ratios
    )

    # Prefer existing composite 5Y FCF CAGR when available.
    if not composite.empty and "fcf_cagr_5yr_pct" in composite.columns:
        match = composite[
            composite["company_id"].astype(str) == str(company_id)
        ]

        if not match.empty:
            existing = pd.to_numeric(
                match.iloc[-1]["fcf_cagr_5yr_pct"],
                errors="coerce",
            )

            if pd.notna(existing):
                fcf_cagr = float(existing)

    # -----------------------------------------------------
    # Distress signal
    # -----------------------------------------------------
    distress_flag = bool(
        latest_cfo is not None
        and latest_cff is not None
        and pd.notna(latest_cfo)
        and pd.notna(latest_cff)
        and latest_cfo < 0
        and latest_cff > 0
    )

    # -----------------------------------------------------
    # Deleveraging
    # CFF < 0 AND borrowings declining YoY
    # -----------------------------------------------------
    latest_bs, previous_bs = latest_two(
        company_bs,
        company_id,
    )

    deleveraging_flag = False

    if (
        latest_bs is not None
        and previous_bs is not None
        and latest_cff is not None
        and pd.notna(latest_cff)
        and latest_cff < 0
    ):
        latest_borrowings = latest_bs["borrowings"]
        previous_borrowings = previous_bs["borrowings"]

        if (
            pd.notna(latest_borrowings)
            and pd.notna(previous_borrowings)
            and latest_borrowings < previous_borrowings
        ):
            deleveraging_flag = True

    # -----------------------------------------------------
    # Capital allocation pattern
    # -----------------------------------------------------
    capital_allocation_label = classify_capital_allocation(
        latest_cfo,
        latest_cfi,
        latest_cff,
    )

    return {
        "company_id": company_id,
        "sector": sector,
        "cfo_quality_score": cfo_quality_score,
        "cfo_quality_label": cfo_quality_label,
        "capex_intensity_pct": capex_intensity_pct,
        "capex_label": capex_label,
        "fcf_cagr_5yr": fcf_cagr,
        "fcf_conversion_pct": fcf_conversion_pct,
        "distress_flag": distress_flag,
        "deleveraging_flag": deleveraging_flag,
        "capital_allocation_label": capital_allocation_label,
        "_latest_cfo": latest_cfo,
        "_latest_cff": latest_cff,
        "_latest_net_profit": latest_net_profit,
        "_latest_year": latest_year,
    }


def main() -> None:
    """Generate Day 31 cash-flow intelligence outputs."""

    (
        companies,
        sectors,
        cashflow,
        pnl,
        ratios,
        balancesheet,
        composite,
    ) = load_data()

    sector_map = (
        sectors[
            ["company_id", "sector"]
        ]
        .drop_duplicates("company_id")
    )

    companies = companies.merge(
        sector_map,
        on="company_id",
        how="left",
    )

    results = []
    distress_rows = []

    for _, company in companies.iterrows():

        company_id = str(company["company_id"])
        sector = company.get("sector", "N/A")

        result = calculate_company(
            company_id,
            sector,
            cashflow,
            pnl,
            ratios,
            balancesheet,
            composite,
        )

        results.append(result)

        if result["distress_flag"]:
            distress_rows.append(
                {
                    "company_id": company_id,
                    "sector": sector,
                    "year": result["_latest_year"],
                    "CFO": result["_latest_cfo"],
                    "CFF": result["_latest_cff"],
                    "latest_net_profit": result["_latest_net_profit"],
                }
            )

    output = pd.DataFrame(results)

    # Remove internal calculation columns.
    output = output[
        [
            "company_id",
            "sector",
            "cfo_quality_score",
            "cfo_quality_label",
            "capex_intensity_pct",
            "capex_label",
            "fcf_cagr_5yr",
            "fcf_conversion_pct",
            "distress_flag",
            "deleveraging_flag",
            "capital_allocation_label",
        ]
    ].copy()

    # Round numeric fields.
    for column in [
        "cfo_quality_score",
        "capex_intensity_pct",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
    ]:
        output[column] = pd.to_numeric(
            output[column],
            errors="coerce",
        ).round(4)

    distress = pd.DataFrame(distress_rows)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_excel(
        INTELLIGENCE_PATH,
        index=False,
    )

    distress.to_csv(
        DISTRESS_PATH,
        index=False,
    )

    print("Day 31 Cash Flow Intelligence")
    print("=" * 60)
    print(f"Companies processed: {output['company_id'].nunique()}")
    print(f"Output rows: {len(output)}")
    print(f"Distress alerts: {len(distress)}")
    print(
        f"Deleveraging companies: "
        f"{int(output['deleveraging_flag'].sum())}"
    )

    print("\nCFO Quality:")
    print(
        output["cfo_quality_label"].value_counts(
            dropna=False
        )
    )

    print("\nCapEx:")
    print(
        output["capex_label"].value_counts(
            dropna=False
        )
    )

    print("\nCapital Allocation:")
    print(
        output["capital_allocation_label"].value_counts(
            dropna=False
        )
    )

    print(f"\nSaved: {INTELLIGENCE_PATH}")
    print(f"Saved: {DISTRESS_PATH}")


if __name__ == "__main__":
    main()