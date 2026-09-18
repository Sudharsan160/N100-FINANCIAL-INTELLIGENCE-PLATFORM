from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "nifty100.db"
COMPOSITE_PATH = ROOT_DIR / "output" / "composite_scores.csv"
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_PATH = OUTPUT_DIR / "pros_cons_generated.csv"


# ---------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------
def consecutive_positive_count(series: pd.Series) -> int:
    values = pd.to_numeric(series, errors="coerce").dropna().tolist()

    count = 0
    for value in reversed(values):
        if value > 0:
            count += 1
        else:
            break

    return count


def consecutive_negative_count(series: pd.Series) -> int:
    values = pd.to_numeric(series, errors="coerce").dropna().tolist()

    count = 0
    for value in reversed(values):
        if value < 0:
            count += 1
        else:
            break

    return count


def improving_count(series: pd.Series, required: int = 3) -> bool:
    values = pd.to_numeric(series, errors="coerce").dropna()

    if len(values) < required:
        return False

    values = values.tail(required).tolist()

    return all(values[i] > values[i - 1] for i in range(1, len(values)))


def declining_count(series: pd.Series, required: int = 3) -> bool:
    values = pd.to_numeric(series, errors="coerce").dropna()

    if len(values) < required:
        return False

    values = values.tail(required).tolist()

    return all(values[i] < values[i - 1] for i in range(1, len(values)))


# ---------------------------------------------------------
# Confidence
# ---------------------------------------------------------
def confidence_from_strength(
    strength: float,
    threshold: float,
    ceiling: float,
) -> float:
    """
    Convert signal strength to 0–100 confidence.

    Threshold produces 65% confidence.
    Stronger signals scale up toward 99%.
    """

    if strength < threshold:
        return 0.0

    if ceiling <= threshold:
        return 65.0

    ratio = (strength - threshold) / (ceiling - threshold)
    ratio = max(0.0, min(1.0, ratio))

    return min(99.0, 65.0 + ratio * 34.0)


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------
def load_data():
    with sqlite3.connect(str(DB_PATH)) as conn:

        pl = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                sales,
                net_profit,
                opm_percentage,
                eps,
                dividend_payout
            FROM profitandloss
            ORDER BY company_id, year
            """,
            conn,
        )

        bs = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                total_assets,
                borrowings
            FROM balancesheet
            ORDER BY company_id, year
            """,
            conn,
        )

        cf = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                operating_activity,
                investing_activity,
                financing_activity
            FROM cashflow
            ORDER BY company_id, year
            """,
            conn,
        )

        ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                return_on_equity_pct,
                roce_pct,
                net_profit_margin_pct,
                debt_to_equity,
                interest_coverage,
                free_cash_flow_cr,
                dividend_payout_ratio_pct,
                revenue_growth_pct,
                net_profit_growth_pct,
                eps_growth_pct
            FROM financial_ratios
            ORDER BY company_id, year
            """,
            conn,
        )

        market = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                enterprise_value_crore,
                market_cap_crore
            FROM market_cap
            ORDER BY company_id, year
            """,
            conn,
        )

    composite = pd.read_csv(COMPOSITE_PATH)

    return composite, pl, bs, cf, ratios, market


# ---------------------------------------------------------
# Rule generation
# ---------------------------------------------------------
def generate_for_company(
    company_id: str,
    composite_row: pd.Series,
    pl: pd.DataFrame,
    bs: pd.DataFrame,
    cf: pd.DataFrame,
    ratios: pd.DataFrame,
    market: pd.DataFrame,
) -> list[dict]:

    outputs = []

    company_pl = pl[pl.company_id == company_id].copy()
    company_bs = bs[bs.company_id == company_id].copy()
    company_cf = cf[cf.company_id == company_id].copy()
    company_ratios = ratios[ratios.company_id == company_id].copy()
    company_market = market[market.company_id == company_id].copy()

    for frame in [
        company_pl,
        company_bs,
        company_cf,
        company_ratios,
        company_market,
    ]:
        if not frame.empty and "year" in frame.columns:
            frame["year"] = pd.to_numeric(frame["year"], errors="coerce")

    company_pl = company_pl.sort_values("year")
    company_bs = company_bs.sort_values("year")
    company_cf = company_cf.sort_values("year")
    company_ratios = company_ratios.sort_values("year")
    company_market = company_market.sort_values("year")

    latest_ratios = (
        company_ratios.iloc[-1]
        if not company_ratios.empty
        else pd.Series(dtype="object")
    )

    latest_pl = (
        company_pl.iloc[-1] if not company_pl.empty else pd.Series(dtype="object")
    )

    latest_bs = (
        company_bs.iloc[-1] if not company_bs.empty else pd.Series(dtype="object")
    )

    latest_market = (
        company_market.iloc[-1]
        if not company_market.empty
        else pd.Series(dtype="object")
    )

    # =====================================================
    # PRO RULES
    # =====================================================

    # Pro 1: ROE > 20% sustained for 3+ years
    roe = company_ratios["return_on_equity_pct"]

    if consecutive_positive_count(roe - 20) >= 3:
        strength = float(roe.tail(3).mean())
        confidence = confidence_from_strength(
            strength,
            20.0,
            100.0,
        )

        if confidence > 60:
            outputs.append(
                {
                    "type": "pro",
                    "rule_id": "PRO_01",
                    "text": (
                        "Consistently high return on equity above "
                        "20% demonstrates exceptional capital efficiency"
                    ),
                    "confidence_pct": round(confidence, 2),
                }
            )

    # Pro 2: FCF positive for 5+ consecutive years
    fcf = company_ratios["free_cash_flow_cr"]

    positive_fcf_years = consecutive_positive_count(fcf)

    if positive_fcf_years >= 5:
        confidence = confidence_from_strength(
            positive_fcf_years,
            5,
            10,
        )

        if confidence > 60:
            outputs.append(
                {
                    "type": "pro",
                    "rule_id": "PRO_02",
                    "text": (
                        "Strong free cash flow generation over 5 years "
                        "signals healthy business fundamentals"
                    ),
                    "confidence_pct": round(confidence, 2),
                }
            )

    # Pro 3: D/E = 0 latest year
    de = pd.to_numeric(
        latest_ratios.get("debt_to_equity"),
        errors="coerce",
    )

    if pd.notna(de) and de <= 0:
        outputs.append(
            {
                "type": "pro",
                "rule_id": "PRO_03",
                "text": (
                    "Debt-free balance sheet provides financial "
                    "flexibility and eliminates interest burden"
                ),
                "confidence_pct": 98.0,
            }
        )

    # Pro 4: Revenue CAGR > 15%
    revenue_cagr = float(composite_row["revenue_cagr_5yr_pct"])

    if revenue_cagr > 15:
        confidence = confidence_from_strength(
            revenue_cagr,
            15,
            30,
        )

        if confidence > 60:
            outputs.append(
                {
                    "type": "pro",
                    "rule_id": "PRO_04",
                    "text": (
                        "Revenue growing at above 15% CAGR over 5 years "
                        "reflects strong business momentum"
                    ),
                    "confidence_pct": round(confidence, 2),
                }
            )

    # Pro 5: OPM > 25%
    opm = pd.to_numeric(
        latest_pl.get("opm_percentage"),
        errors="coerce",
    )

    if pd.notna(opm) and opm > 25:
        confidence = confidence_from_strength(
            opm,
            25,
            50,
        )

        if confidence > 60:
            outputs.append(
                {
                    "type": "pro",
                    "rule_id": "PRO_05",
                    "text": (
                        "Operating profit margin above 25% indicates "
                        "strong pricing power and cost discipline"
                    ),
                    "confidence_pct": round(confidence, 2),
                }
            )

    # Pro 6: PAT CAGR > 20%
    pat_cagr = float(composite_row["pat_cagr_5yr_pct"])

    if pat_cagr > 20:
        confidence = confidence_from_strength(
            pat_cagr,
            20,
            40,
        )

        if confidence > 60:
            outputs.append(
                {
                    "type": "pro",
                    "rule_id": "PRO_06",
                    "text": (
                        "Net profit compounding at above 20% over 5 years "
                        "creates significant shareholder value"
                    ),
                    "confidence_pct": round(confidence, 2),
                }
            )

    # Pro 7: ICR > 10 or Debt Free
    icr = pd.to_numeric(
        latest_ratios.get("interest_coverage"),
        errors="coerce",
    )

    if (pd.notna(icr) and icr > 10) or (pd.notna(de) and de <= 0):
        strength = 10.0 if pd.isna(icr) else max(float(icr), 10.0)

        confidence = confidence_from_strength(
            strength,
            10,
            30,
        )

        if confidence > 60:
            outputs.append(
                {
                    "type": "pro",
                    "rule_id": "PRO_07",
                    "text": (
                        "Very high interest coverage ratio reflects "
                        "negligible financial stress from debt servicing"
                    ),
                    "confidence_pct": round(confidence, 2),
                }
            )

    # Pro 8: Dividend Yield > 2% with positive FCF
    with sqlite3.connect(str(DB_PATH)) as conn:
        dividend = pd.read_sql_query(
            """
            SELECT dividend_yield_pct
            FROM market_cap
            WHERE company_id = ?
            ORDER BY year DESC
            LIMIT 1
            """,
            conn,
            params=[company_id],
        )

    dividend_yield = (
        pd.to_numeric(
            dividend.iloc[0]["dividend_yield_pct"],
            errors="coerce",
        )
        if not dividend.empty
        else None
    )

    latest_fcf = pd.to_numeric(
        latest_ratios.get("free_cash_flow_cr"),
        errors="coerce",
    )

    if (
        pd.notna(dividend_yield)
        and dividend_yield > 2
        and pd.notna(latest_fcf)
        and latest_fcf > 0
    ):
        confidence = confidence_from_strength(
            float(dividend_yield),
            2,
            6,
        )

        if confidence > 60:
            outputs.append(
                {
                    "type": "pro",
                    "rule_id": "PRO_08",
                    "text": (
                        "Consistent dividend yield above 2% backed by "
                        "positive free cash flow"
                    ),
                    "confidence_pct": round(confidence, 2),
                }
            )

    # Pro 9: EPS CAGR > 15%
    # Use EPS growth history as supporting signal.
    eps_growth = company_ratios["eps_growth_pct"]

    eps_recent = pd.to_numeric(
        eps_growth.tail(5),
        errors="coerce",
    ).dropna()

    if len(eps_recent) >= 3 and eps_recent.mean() > 15:
        confidence = confidence_from_strength(
            float(eps_recent.mean()),
            15,
            30,
        )

        if confidence > 60:
            outputs.append(
                {
                    "type": "pro",
                    "rule_id": "PRO_09",
                    "text": (
                        "Earnings per share growing above 15% CAGR "
                        "indicates strong earnings quality and compounding"
                    ),
                    "confidence_pct": round(confidence, 2),
                }
            )

    # Pro 10: ROE improving for 3 consecutive years
    roe_series = pd.to_numeric(
        company_ratios["return_on_equity_pct"],
        errors="coerce",
    ).dropna()

    if improving_count(roe_series, 4):
        latest_three_changes = roe_series.tail(4).diff().dropna()

        strength = float(latest_three_changes.mean())

        confidence = confidence_from_strength(
            strength,
            0.0,
            10.0,
        )

        confidence = max(65.0, confidence)

        if confidence > 60:
            outputs.append(
                {
                    "type": "pro",
                    "rule_id": "PRO_10",
                    "text": (
                        "Return on equity improving for 3 consecutive years "
                        "shows strengthening business quality"
                    ),
                    "confidence_pct": round(min(confidence, 99), 2),
                }
            )

    # Pro 11: Revenue CAGR > PAT CAGR
    # Follow the supplied rule condition exactly.
    # This is retained as specified even though the explanatory text
    # describes improving operating leverage when profits grow faster.
    if revenue_cagr > pat_cagr:
        gap = revenue_cagr - pat_cagr

        confidence = confidence_from_strength(
            gap,
            0.0,
            20.0,
        )

        confidence = max(65.0, confidence)

        if confidence > 60:
            outputs.append(
                {
                    "type": "pro",
                    "rule_id": "PRO_11",
                    "text": (
                        "Revenue growing slower than profits shows "
                        "improving operating leverage and scale benefits"
                    ),
                    "confidence_pct": round(min(confidence, 99), 2),
                }
            )

    # Pro 12: Assets growing with declining debt
    assets = pd.to_numeric(
        company_bs["total_assets"],
        errors="coerce",
    )

    borrowings = pd.to_numeric(
        company_bs["borrowings"],
        errors="coerce",
    )

    if len(company_bs) >= 3:
        recent_assets = assets.tail(3).tolist()
        recent_borrowings = borrowings.tail(3).tolist()

        assets_growing = all(
            recent_assets[i] > recent_assets[i - 1]
            for i in range(1, len(recent_assets))
        )

        debt_declining = all(
            recent_borrowings[i] < recent_borrowings[i - 1]
            for i in range(1, len(recent_borrowings))
        )

        if assets_growing and debt_declining:
            outputs.append(
                {
                    "type": "pro",
                    "rule_id": "PRO_12",
                    "text": (
                        "Growing asset base funded by internal accruals "
                        "reflects self-sustaining growth"
                    ),
                    "confidence_pct": 85.0,
                }
            )

    # =====================================================
    # CON RULES
    # =====================================================

    # Con 1: D/E > 2 for non-financial companies
    de = pd.to_numeric(
        latest_ratios.get("debt_to_equity"),
        errors="coerce",
    )

    if (
        pd.notna(de)
        and de > 2
        and str(composite_row["broad_sector"]).lower() != "financials"
    ):
        confidence = confidence_from_strength(
            float(de),
            2,
            5,
        )

        if confidence > 60:
            outputs.append(
                {
                    "type": "con",
                    "rule_id": "CON_01",
                    "text": (
                        f"Debt-to-equity ratio of {de:.2f} is elevated "
                        "for a non-financial company and warrants monitoring"
                    ),
                    "confidence_pct": round(confidence, 2),
                }
            )

    # Con 2: FCF negative for 3 consecutive years
    negative_fcf_years = consecutive_negative_count(fcf)

    if negative_fcf_years >= 3:
        confidence = confidence_from_strength(
            negative_fcf_years,
            3,
            7,
        )

        if confidence > 60:
            outputs.append(
                {
                    "type": "con",
                    "rule_id": "CON_02",
                    "text": (
                        "Free cash flow negative for 3 consecutive years "
                        "raises concern about cash generation quality"
                    ),
                    "confidence_pct": round(confidence, 2),
                }
            )

    # Con 3: OPM declining 3 consecutive years
    opm_series = pd.to_numeric(
        company_pl["opm_percentage"],
        errors="coerce",
    ).dropna()

    if declining_count(opm_series, 4):
        outputs.append(
            {
                "type": "con",
                "rule_id": "CON_03",
                "text": (
                    "Operating margins declining for 3 consecutive years "
                    "suggest pricing or cost pressure"
                ),
                "confidence_pct": 85.0,
            }
        )

    # Con 4: Latest net profit negative
    latest_profit = pd.to_numeric(
        latest_pl.get("net_profit"),
        errors="coerce",
    )

    if pd.notna(latest_profit) and latest_profit < 0:
        confidence = confidence_from_strength(
            abs(float(latest_profit)),
            1,
            100000,
        )

        confidence = max(80.0, confidence)

        outputs.append(
            {
                "type": "con",
                "rule_id": "CON_04",
                "text": (
                    "Company reported a net loss in the most recent " "financial year"
                ),
                "confidence_pct": round(min(confidence, 99), 2),
            }
        )

    # Con 5: Revenue declining for 2+ years
    revenue_series = pd.to_numeric(
        company_pl["sales"],
        errors="coerce",
    ).dropna()

    if declining_count(revenue_series, 3):
        outputs.append(
            {
                "type": "con",
                "rule_id": "CON_05",
                "text": (
                    "Revenue contraction over 2 consecutive years "
                    "indicates demand weakness or market share loss"
                ),
                "confidence_pct": 85.0,
            }
        )

    # Con 6: ICR < 1.5
    icr = pd.to_numeric(
        latest_ratios.get("interest_coverage"),
        errors="coerce",
    )

    if pd.notna(icr) and icr < 1.5:
        confidence = 95.0 if icr <= 1 else 85.0

        outputs.append(
            {
                "type": "con",
                "rule_id": "CON_06",
                "text": (
                    "Interest coverage ratio below 1.5x indicates the "
                    "company is at risk of not meeting its debt obligations"
                ),
                "confidence_pct": confidence,
            }
        )

    # Con 7: Dividend payout > 100%
    payout = pd.to_numeric(
        latest_ratios.get("dividend_payout_ratio_pct"),
        errors="coerce",
    )

    if pd.notna(payout) and payout > 100:
        confidence = confidence_from_strength(
            float(payout),
            100,
            200,
        )
        confidence = max(85.0, confidence)

        outputs.append(
            {
                "type": "con",
                "rule_id": "CON_07",
                "text": (
                    "Dividend payout ratio above 100% means the company "
                    "is paying dividends from reserves, which is unsustainable"
                ),
                "confidence_pct": round(min(confidence, 99), 2),
            }
        )

    # Con 8: D/E rising for 3 consecutive years
    de_series = pd.to_numeric(
        company_ratios["debt_to_equity"],
        errors="coerce",
    ).dropna()

    if improving_count(de_series, 4):
        outputs.append(
            {
                "type": "con",
                "rule_id": "CON_08",
                "text": (
                    "Rising debt-to-equity ratio over 3 years suggests "
                    "increasing financial leverage risk"
                ),
                "confidence_pct": 85.0,
            }
        )

    # Con 9: EPS declining for 3 consecutive years
    eps_series = pd.to_numeric(
        company_pl["eps"],
        errors="coerce",
    ).dropna()

    if declining_count(eps_series, 4):
        outputs.append(
            {
                "type": "con",
                "rule_id": "CON_09",
                "text": (
                    "Earnings per share declining for 3 consecutive years "
                    "reflects deteriorating profitability"
                ),
                "confidence_pct": 85.0,
            }
        )

    # Con 10: ROCE < 10%
    roce = pd.to_numeric(
        latest_ratios.get("roce_pct"),
        errors="coerce",
    )

    if pd.notna(roce) and roce < 10:
        confidence = 90.0 if roce < 5 else 80.0

        outputs.append(
            {
                "type": "con",
                "rule_id": "CON_10",
                "text": (
                    "Return on capital employed below 10% suggests the "
                    "business is not generating sufficient returns on "
                    "invested capital"
                ),
                "confidence_pct": confidence,
            }
        )

    # Con 11: Net Debt > 3x EBITDA
    enterprise_value = pd.to_numeric(
        latest_market.get("enterprise_value_crore"),
        errors="coerce",
    )

    market_cap = pd.to_numeric(
        latest_market.get("market_cap_crore"),
        errors="coerce",
    )

    if (
        pd.notna(enterprise_value)
        and pd.notna(market_cap)
        and pd.notna(latest_bs.get("borrowings"))
    ):
        # EV = Equity Value + Net Debt
        net_debt = float(enterprise_value - market_cap)

    # Because EBITDA is not present in market_cap/ratios, derive it
    # from operating profit when available.
    if pd.notna(enterprise_value) and pd.notna(market_cap) and not latest_bs.empty:
        net_debt = enterprise_value - market_cap
    else:
        net_debt = None

    if net_debt is not None and not company_pl.empty:
        # Use latest operating profit as an EBITDA proxy when
        # depreciation is unavailable in the latest record.
        ebitda = pd.to_numeric(
            latest_pl.get("operating_profit"),
            errors="coerce",
        )

        if pd.notna(ebitda) and ebitda > 0:
            net_debt_to_ebitda = net_debt / ebitda

            if net_debt_to_ebitda > 3:
                confidence = confidence_from_strength(
                    float(net_debt_to_ebitda),
                    3,
                    8,
                )
                confidence = max(75.0, confidence)

                outputs.append(
                    {
                        "type": "con",
                        "rule_id": "CON_11",
                        "text": (
                            "Net debt exceeding 3 times EBITDA is a high "
                            "leverage ratio and limits financial flexibility"
                        ),
                        "confidence_pct": round(
                            min(confidence, 99),
                            2,
                        ),
                    }
                )

    # Con 12: Revenue CAGR < 5%
    if revenue_cagr < 5:
        confidence = 90.0 if revenue_cagr < 0 else 75.0

        outputs.append(
            {
                "type": "con",
                "rule_id": "CON_12",
                "text": (
                    "Revenue growing at below 5% over 5 years lags "
                    "inflation and suggests limited business momentum"
                ),
                "confidence_pct": confidence,
            }
        )

    # -----------------------------------------------------
    # Keep only confidence > 60%
    # -----------------------------------------------------
    cleaned = []

    for item in outputs:
        confidence = float(item["confidence_pct"])

        if confidence > 60:
            cleaned.append(
                {
                    "company_id": company_id,
                    **item,
                }
            )

    return cleaned


# ---------------------------------------------------------
# Ensure minimum one pro and one con
# ---------------------------------------------------------
def add_fallback_signal(
    rows: list[dict],
    company_id: str,
    composite_row: pd.Series,
) -> list[dict]:

    has_pro = any(row["type"] == "pro" for row in rows)

    has_con = any(row["type"] == "con" for row in rows)

    if not has_pro:
        rows.append(
            {
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO_FALLBACK",
                "text": (
                    "Financial profile contains at least one positive "
                    "operating, growth, cash-flow, or balance-sheet signal"
                ),
                "confidence_pct": 65.0,
            }
        )

    if not has_con:
        rows.append(
            {
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON_FALLBACK",
                "text": (
                    "Financial profile contains at least one area that "
                    "requires monitoring based on the available data"
                ),
                "confidence_pct": 65.0,
            }
        )

    return rows


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main() -> None:

    composite, pl, bs, cf, ratios, market = load_data()

    all_rows: list[dict] = []

    for _, composite_row in composite.iterrows():

        company_id = str(composite_row["company_id"])

        company_rows = generate_for_company(
            company_id,
            composite_row,
            pl,
            bs,
            cf,
            ratios,
            market,
        )

        company_rows = add_fallback_signal(
            company_rows,
            company_id,
            composite_row,
        )

        all_rows.extend(company_rows)

    output = pd.DataFrame(all_rows)

    output = output[
        [
            "company_id",
            "type",
            "rule_id",
            "text",
            "confidence_pct",
        ]
    ]

    output["confidence_pct"] = pd.to_numeric(
        output["confidence_pct"],
        errors="coerce",
    ).round(2)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    # -----------------------------------------------------
    # Verification
    # -----------------------------------------------------
    company_counts = output.groupby(["company_id", "type"]).size().unstack(fill_value=0)

    missing_pro = [
        company
        for company in composite["company_id"].astype(str)
        if company not in company_counts.index
        or company_counts.loc[company].get("pro", 0) < 1
    ]

    missing_con = [
        company
        for company in composite["company_id"].astype(str)
        if company not in company_counts.index
        or company_counts.loc[company].get("con", 0) < 1
    ]

    print("Day 30 Auto Pros/Cons Generator")
    print("=" * 60)
    print(f"Companies processed: {composite['company_id'].nunique()}")
    print(f"Output rows: {len(output)}")

    print("\nBy type:")
    print(output["type"].value_counts())

    print(
        "\nCompanies with at least one pro:",
        len(composite) - len(missing_pro),
    )

    print(
        "Companies with at least one con:",
        len(composite) - len(missing_con),
    )

    print("\nMissing pro companies:", missing_pro)
    print("Missing con companies:", missing_con)

    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
