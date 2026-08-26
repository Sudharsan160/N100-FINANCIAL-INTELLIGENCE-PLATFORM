from src.ratios.calculator import (
    calculate_ratio_row,
    deduplicate_records,
)


def test_deduplicate_identical_records():
    records = [
        {
            "id": 1,
            "company_id": "PNB",
            "year": 2024,
            "borrowings": 100,
            "reserves": 200,
        },
        {
            "id": 2,
            "company_id": "PNB",
            "year": 2024,
            "borrowings": 100,
            "reserves": 200,
        },
    ]

    result = deduplicate_records(records)

    assert len(result) == 1
    assert result[0]["id"] == 1


def test_deduplicate_zero_placeholder():
    records = [
        {
            "id": 1,
            "company_id": "ABB",
            "year": 2014,
            "operating_activity": 155,
            "investing_activity": -144,
        },
        {
            "id": 2,
            "company_id": "ABB",
            "year": 2014,
            "operating_activity": 0,
            "investing_activity": 0,
        },
    ]

    result = deduplicate_records(records)

    assert len(result) == 1
    assert result[0]["id"] == 1


def test_calculate_ratio_row():
    profit_loss = {
        "company_id": "TEST",
        "year": 2024,
        "sales": 1000,
        "operating_profit": 200,
        "net_profit": 100,
        "interest": 50,
        "eps": 10,
        "dividend_payout": 20,
        "face_value": 10,
    }

    balance_sheet = {
        "company_id": "TEST",
        "year": 2024,
        "equity_capital": 100,
        "reserves": 400,
        "borrowings": 200,
        "total_assets": 1000,
    }

    cash_flow = {
        "company_id": "TEST",
        "year": 2024,
        "operating_activity": 300,
        "investing_activity": -100,
    }

    result = calculate_ratio_row(
        profit_loss,
        balance_sheet,
        cash_flow,
    )

    assert result["company_id"] == "TEST"
    assert result["year"] == 2024

    assert result["net_profit_margin_pct"] == 10.0
    assert result["operating_profit_margin_pct"] == 20.0
    assert result["return_on_equity_pct"] == 20.0
    assert result["debt_to_equity"] == 0.4
    assert result["interest_coverage"] == 4.0
    assert result["asset_turnover"] == 1.0

    assert result["free_cash_flow_cr"] == 200.0
    assert result["capex_cr"] == 100.0
    assert result["earnings_per_share"] == 10
    assert result["book_value_per_share"] == 50.0
    assert result["dividend_payout_ratio_pct"] == 20
    assert result["total_debt_cr"] == 200
    assert result["cash_from_operations_cr"] == 300


def test_negative_equity_is_preserved():
    profit_loss = {
        "company_id": "TEST",
        "year": 2024,
        "sales": 1000,
        "operating_profit": 100,
        "net_profit": 50,
        "interest": 25,
        "eps": 5,
        "dividend_payout": 0,
    }

    balance_sheet = {
        "company_id": "TEST",
        "year": 2024,
        "equity_capital": 100,
        "reserves": -300,
        "borrowings": 200,
        "total_assets": 500,
    }

    result = calculate_ratio_row(
        profit_loss,
        balance_sheet,
        None,
    )

    assert result["return_on_equity_pct"] == -25.0
    assert result["debt_to_equity"] == -1.0