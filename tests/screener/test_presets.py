import pytest

from src.screener.engine import ScreenerEngine


@pytest.fixture
def engine():
    return ScreenerEngine()


PRESETS = [
    "quality_compounder",
    "value_pick",
    "growth_accelerator",
    "dividend_champion",
    "debt_free_blue_chip",
    "turnaround_watch",
]


def test_all_six_presets_exist(engine):
    presets = engine.config["presets"]

    for preset in PRESETS:
        assert preset in presets


@pytest.mark.parametrize("preset_name", PRESETS)
def test_preset_returns_dataframe(engine, preset_name):
    result = engine.preset(preset_name)

    assert result is not None
    assert hasattr(result, "columns")


def test_quality_compounder(engine):
    result = engine.preset("quality_compounder")

    assert len(result) == 22
    assert (result["return_on_equity_pct"] > 15).all()
    assert (result["free_cash_flow_cr"] > 0).all()
    assert (result["revenue_cagr_5yr"] > 10).all()

    non_financials = result[
        ~result["broad_sector"]
        .str.casefold()
        .eq("financials")
    ]

    assert (
        non_financials["debt_to_equity"] < 1
    ).all()


def test_value_pick_conditions(engine):
    result = engine.preset("value_pick")

    assert len(result) == 2
    assert (result["pe_ratio"] < 20).all()
    assert (result["pb_ratio"] < 3).all()
    assert (result["dividend_yield_pct"] > 1).all()

    non_financials = result[
        ~result["broad_sector"]
        .str.casefold()
        .eq("financials")
    ]

    assert (
        non_financials["debt_to_equity"] < 2
    ).all()


def test_growth_accelerator(engine):
    result = engine.preset("growth_accelerator")

    assert len(result) == 19
    assert (result["pat_cagr_5yr"] > 20).all()
    assert (result["revenue_cagr_5yr"] > 15).all()

    non_financials = result[
        ~result["broad_sector"]
        .str.casefold()
        .eq("financials")
    ]

    assert (
        non_financials["debt_to_equity"] < 2
    ).all()


def test_dividend_champion(engine):
    result = engine.preset("dividend_champion")

    assert len(result) == 29
    assert (result["dividend_yield_pct"] > 2).all()
    assert (
        result["dividend_payout_ratio_pct"] < 80
    ).all()
    assert (result["free_cash_flow_cr"] > 0).all()


def test_debt_free_blue_chip(engine):
    result = engine.preset("debt_free_blue_chip")

    assert len(result) == 2
    assert (result["debt_to_equity"] == 0).all()
    assert (result["return_on_equity_pct"] > 12).all()
    assert (result["sales"] > 5000).all()


def test_turnaround_watch(engine):
    result = engine.preset("turnaround_watch")

    assert len(result) == 32
    assert (result["revenue_cagr_3yr"] > 10).all()
    assert (result["free_cash_flow_cr"] > 0).all()


def test_presets_are_sorted(engine):
    for preset_name in PRESETS:
        result = engine.preset(preset_name)

        scores = result[
            "composite_quality_score"
        ].dropna()

        assert scores.is_monotonic_decreasing