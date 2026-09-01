import numpy as np
import pytest

from src.screener.engine import ScreenerEngine


@pytest.fixture
def engine():
    return ScreenerEngine()


def test_load_data_has_92_companies(engine):
    data = engine.load_data()

    assert len(data) == 92
    assert data["company_id"].nunique() == 92


def test_latest_year_is_2024(engine):
    data = engine.load_data()

    assert int(data["year"].max()) == 2024


def test_expected_cagr_columns_exist(engine):
    data = engine.load_data()

    expected = {
        "revenue_cagr_3yr",
        "revenue_cagr_5yr",
        "pat_cagr_3yr",
        "pat_cagr_5yr",
        "eps_cagr_5yr",
        "fcf_cagr_5yr",
        "cfo_pat_ratio",
    }

    assert expected.issubset(data.columns)


def test_composite_score_exists(engine):
    data = engine.load_data()
    result = engine.add_composite_quality_score(data)

    assert "composite_quality_score" in result.columns


def test_composite_score_range(engine):
    data = engine.load_data()
    result = engine.add_composite_quality_score(data)

    scores = result["composite_quality_score"].dropna()

    assert (scores >= 0).all()
    assert (scores <= 100).all()


def test_composite_score_sorted(engine):
    result = engine.screen({"roe_min": 15})

    scores = result["composite_quality_score"].dropna()

    assert scores.is_monotonic_decreasing


def test_roe_filter(engine):
    result = engine.screen({"roe_min": 15})

    assert (
        result["return_on_equity_pct"] >= 15
    ).all()


def test_de_filter_exempts_financials(engine):
    result = engine.screen({"de_max": 1})

    financials = result[
        result["broad_sector"]
        .str.casefold()
        .eq("financials")
    ]

    non_financials = result[
        ~result["broad_sector"]
        .str.casefold()
        .eq("financials")
    ]

    assert len(financials) > 0

    assert (
        non_financials["debt_to_equity"] <= 1
    ).all()


def test_fcf_filter(engine):
    result = engine.screen({"fcf_min": 0})

    assert (
        result["free_cash_flow_cr"] > 0
    ).all()


def test_revenue_cagr_filter(engine):
    result = engine.screen(
        {"revenue_cagr_5yr_min": 10}
    )

    assert (
        result["revenue_cagr_5yr"] >= 10
    ).all()


def test_pat_cagr_filter(engine):
    result = engine.screen(
        {"pat_cagr_5yr_min": 10}
    )

    assert (
        result["pat_cagr_5yr"] >= 10
    ).all()


def test_opm_filter(engine):
    result = engine.screen(
        {"opm_min": 10}
    )

    assert (
        result["operating_profit_margin_pct"] >= 10
    ).all()


def test_pe_filter(engine):
    result = engine.screen(
        {"pe_max": 20}
    )

    assert (
        result["pe_ratio"] <= 20
    ).all()


def test_pb_filter(engine):
    result = engine.screen(
        {"pb_max": 3}
    )

    assert (
        result["pb_ratio"] <= 3
    ).all()


def test_dividend_yield_filter(engine):
    result = engine.screen(
        {"dividend_yield_min": 1}
    )

    assert (
        result["dividend_yield_pct"] >= 1
    ).all()


def test_icr_filter(engine):
    result = engine.screen(
        {"icr_min": 10}
    )

    assert (
        result["interest_coverage"] >= 10
    ).all()


def test_market_cap_filter(engine):
    result = engine.screen(
        {"market_cap_min": 50000}
    )

    assert (
        result["market_cap_crore"] >= 50000
    ).all()


def test_net_profit_filter(engine):
    result = engine.screen(
        {"net_profit_min": 100}
    )

    assert (
        result["net_profit"] >= 100
    ).all()


def test_eps_cagr_filter(engine):
    result = engine.screen(
        {"eps_cagr_min": 5}
    )

    assert (
        result["eps_cagr_5yr"] >= 5
    ).all()


def test_asset_turnover_filter(engine):
    result = engine.screen(
        {"asset_turnover_min": 1}
    )

    assert (
        result["asset_turnover"] >= 1
    ).all()


def test_sales_filter(engine):
    result = engine.screen(
        {"sales_min": 5000}
    )

    assert (
        result["sales"] >= 5000
    ).all()


def test_debt_free_icr_is_infinity(engine):
    data = engine.load_data()

    debt_free = data[
        (
            data["debt_to_equity"] == 0
        )
        |
        (
            data["total_debt_cr"] == 0
        )
    ]

    assert len(debt_free) == 3

    assert np.isinf(
        debt_free["interest_coverage"]
    ).all()


def test_quality_compounder_range(engine):
    result = engine.screen(
        {
            "roe_min": 15,
            "de_max": 1,
            "fcf_min": 0,
            "revenue_cagr_5yr_min": 10,
        }
    )

    assert 5 <= len(result) <= 50


def test_quality_compounder_conditions(engine):
    result = engine.screen(
        {
            "roe_min": 15,
            "de_max": 1,
            "fcf_min": 0,
            "revenue_cagr_5yr_min": 10,
        }
    )

    assert (
        result["return_on_equity_pct"] >= 15
    ).all()

    non_financials = result[
        ~result["broad_sector"]
        .str.casefold()
        .eq("financials")
    ]

    assert (
        non_financials["debt_to_equity"] <= 1
    ).all()

    assert (
        result["free_cash_flow_cr"] > 0
    ).all()

    assert (
        result["revenue_cagr_5yr"] >= 10
    ).all()


def test_debt_free_blue_chip_exact_zero(engine):
    result = engine.screen(
        {
            "de_exact": 0,
            "roe_min": 12,
            "sales_min": 5000,
        }
    )

    assert (
        result["debt_to_equity"] == 0
    ).all()

    assert (
        result["return_on_equity_pct"] >= 12
    ).all()

    assert (
        result["sales"] >= 5000
    ).all()