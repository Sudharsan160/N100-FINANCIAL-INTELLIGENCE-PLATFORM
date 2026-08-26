from __future__ import annotations

from typing import Any

from src.ratios.formulas import (
    asset_turnover,
    capital_expenditure_intensity,
    cash_conversion_ratio,
    cash_flow_to_net_profit,
    cfo_to_total_debt,
    debt_ratio,
    debt_to_equity,
    eps_growth,
    equity_ratio,
    financial_leverage,
    financing_cash_flow_to_cfo,
    free_cash_flow,
    free_cash_flow_margin,
    interest_coverage,
    investing_cash_flow_to_cfo,
    net_profit_growth,
    net_profit_margin,
    operating_cash_flow_margin,
    operating_profit_growth,
    operating_profit_margin,
    pretax_margin,
    revenue_growth,
    return_on_assets,
    return_on_capital_employed,
    return_on_equity,
)


BANK_COMPANIES = {
    "AXISBANK",
    "BANKBARODA",
    "CANBK",
    "HDFCBANK",
    "ICICIBANK",
    "INDUSINDBK",
    "KOTAKBANK",
    "PNB",
    "SBIN",
}


def _is_zero_record(record: dict[str, Any]) -> bool:
    """
    Return True when all financial values in a source record are zero/None.

    company_id and year are ignored.
    """
    ignored = {"id", "company_id", "year"}

    for key, value in record.items():
        if key in ignored:
            continue

        if value is None:
            continue

        try:
            if float(value) != 0:
                return False
        except (TypeError, ValueError):
            return False

    return True


def _record_signature(record: dict[str, Any]) -> tuple:
    """Create a comparable signature for deduplication."""
    return tuple(
        (key, record[key])
        for key in sorted(record)
        if key != "id"
    )


def deduplicate_records(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Resolve duplicate records for a single company/year.

    Rules:
    1. Remove exact duplicates.
    2. Remove all-zero duplicate records when a non-zero record exists.
    3. If multiple conflicting non-zero records remain, use the first
       deterministic record ordered by source id.
    """
    if not records:
        return []

    unique: dict[tuple, dict[str, Any]] = {}

    for record in sorted(records, key=lambda item: item.get("id") or 0):
        unique.setdefault(_record_signature(record), record)

    records = list(unique.values())

    non_zero = [
        record
        for record in records
        if not _is_zero_record(record)
    ]

    if non_zero:
        records = non_zero

    records.sort(key=lambda item: item.get("id") or 0)

    return [records[0]]


def calculate_ratio_row(
    profit_loss: dict[str, Any],
    balance_sheet: dict[str, Any],
    cash_flow: dict[str, Any] | None = None,
    previous_profit_loss: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Calculate the Day 08 + Day 09 + Day 11 + Day 13 ratio set.

    Growth metrics use the previous available P&L record
    for the same company.
    """
    company_id = profit_loss["company_id"]
    is_bank = company_id in BANK_COMPANIES

    sales = profit_loss.get("sales")
    operating_profit = profit_loss.get("operating_profit")
    net_profit = profit_loss.get("net_profit")
    profit_before_tax = profit_loss.get("profit_before_tax")
    interest = profit_loss.get("interest")
    eps = profit_loss.get("eps")
    dividend_payout = profit_loss.get("dividend_payout")

    equity_capital = balance_sheet.get("equity_capital")
    reserves = balance_sheet.get("reserves")
    borrowings = balance_sheet.get("borrowings")
    total_assets = balance_sheet.get("total_assets")

    equity = None

    if equity_capital is not None or reserves is not None:
        equity = float(equity_capital or 0) + float(reserves or 0)

    cash_from_operations = None
    capex = None
    free_cf = None
    investing_cash_flow = None
    financing_cash_flow = None

    if cash_flow is not None:
        cash_from_operations = cash_flow.get("operating_activity")
        investing_cash_flow = cash_flow.get("investing_activity")
        financing_cash_flow = cash_flow.get("financing_activity")

        if investing_cash_flow is not None:
            capex = abs(float(investing_cash_flow))

        free_cf = free_cash_flow(
            cash_from_operations,
            capex,
        )

    book_value_per_share = None

    face_value = profit_loss.get("face_value")

    if (
        equity is not None
        and equity_capital is not None
        and equity_capital != 0
        and face_value is not None
        and face_value != 0
    ):
        shares_outstanding = (
            float(equity_capital) / float(face_value)
        )

        book_value_per_share = share_divide(
            equity,
            shares_outstanding,
        )

    previous_sales = None
    previous_operating_profit = None
    previous_net_profit = None
    previous_eps = None

    if previous_profit_loss is not None:
        previous_sales = previous_profit_loss.get("sales")
        previous_operating_profit = previous_profit_loss.get(
            "operating_profit"
        )
        previous_net_profit = previous_profit_loss.get("net_profit")
        previous_eps = previous_profit_loss.get("eps")

    return {
        # Day 08 — Core ratios
        "company_id": company_id,
        "year": int(profit_loss["year"]),
        "net_profit_margin_pct": net_profit_margin(
            net_profit,
            sales,
        ),
        "operating_profit_margin_pct": operating_profit_margin(
            operating_profit,
            sales,
        ),
        "return_on_equity_pct": return_on_equity(
            net_profit,
            equity,
        ),
        "debt_to_equity": debt_to_equity(
            borrowings,
            equity,
        ),
        "interest_coverage": interest_coverage(
            operating_profit,
            interest,
        ),
        "asset_turnover": asset_turnover(
            sales,
            total_assets,
        ),
        "free_cash_flow_cr": free_cf,
        "capex_cr": capex,
        "earnings_per_share": eps,
        "book_value_per_share": book_value_per_share,
        "dividend_payout_ratio_pct": dividend_payout,
        "total_debt_cr": borrowings,
        "cash_from_operations_cr": cash_from_operations,

        # Day 09 — Profitability
        "return_on_assets_pct": return_on_assets(
            net_profit,
            total_assets,
        ),
        "pretax_margin_pct": pretax_margin(
            profit_before_tax,
            sales,
        ),

        # Day 09 — Cash flow
        "operating_cash_flow_margin_pct": operating_cash_flow_margin(
            cash_from_operations,
            sales,
        ),
        "cash_flow_to_net_profit": cash_flow_to_net_profit(
            cash_from_operations,
            net_profit,
        ),

        # Day 09 — Leverage
        "debt_ratio": debt_ratio(
            borrowings,
            total_assets,
        ),
        "equity_ratio": equity_ratio(
            equity,
            total_assets,
        ),
        "financial_leverage": financial_leverage(
            total_assets,
            equity,
        ),

        # Day 09 — Growth
        "revenue_growth_pct": revenue_growth(
            sales,
            previous_sales,
        ),
        "operating_profit_growth_pct": operating_profit_growth(
            operating_profit,
            previous_operating_profit,
        ),
        "net_profit_growth_pct": net_profit_growth(
            net_profit,
            previous_net_profit,
        ),
        "eps_growth_pct": eps_growth(
            eps,
            previous_eps,
        ),

        # Day 11 — Cash Flow & Capital Allocation
        "cfo_to_total_debt": cfo_to_total_debt(
            cash_from_operations,
            borrowings,
        ),
        "free_cash_flow_margin_pct": free_cash_flow_margin(
            free_cf,
            sales,
        ),
        "investing_cash_flow_to_cfo": investing_cash_flow_to_cfo(
            investing_cash_flow,
            cash_from_operations,
        ),
        "financing_cash_flow_to_cfo": financing_cash_flow_to_cfo(
            financing_cash_flow,
            cash_from_operations,
        ),
        "cash_conversion_ratio": cash_conversion_ratio(
            cash_from_operations,
            operating_profit,
        ),
        "capital_expenditure_intensity_pct": capital_expenditure_intensity(
            capex,
            sales,
        ),

        # Day 13 — ROCE with bank carve-out
        "roce_pct": return_on_capital_employed(
            operating_profit,
            equity,
            borrowings,
            is_bank,
        ),
    }


def safe_share_count(
    net_profit: float | int | None,
    eps: float | int | None,
) -> float | None:
    """
    Estimate outstanding shares from Net Profit / EPS.
    """
    if net_profit is None or eps is None or eps == 0:
        return None

    return float(net_profit) / float(eps)


def share_divide(
    numerator: float | int | None,
    denominator: float | int | None,
) -> float | None:
    """Safely calculate per-share value."""
    if numerator is None or denominator is None or denominator == 0:
        return None

    return float(numerator) / float(denominator)