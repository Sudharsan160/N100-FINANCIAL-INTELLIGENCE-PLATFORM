from src.analytics.cagr import (
    calculate_cagr,
    cagr_status,
    eps_cagr,
    profit_cagr,
    revenue_cagr,
)

from src.analytics.cashflow_kpis import (
    capex_intensity,
    cash_flow_to_debt,
    cfo_quality,
    financing_to_cfo,
    free_cash_flow_conversion,
    free_cash_flow_margin,
    investing_to_cfo,
)

from src.analytics.ratios import (
    asset_turnover,
    debt_to_equity,
    net_profit_margin,
    return_on_assets,
    return_on_equity,
)


def test_net_profit_margin():
    assert net_profit_margin(100, 1000) == 10.0


def test_return_on_equity():
    assert return_on_equity(100, 500) == 20.0


def test_return_on_assets():
    assert return_on_assets(100, 1000) == 10.0


def test_debt_to_equity():
    assert debt_to_equity(200, 400) == 0.5


def test_asset_turnover():
    assert asset_turnover(1000, 500) == 2.0


def test_revenue_cagr():
    assert round(revenue_cagr(100, 121, 2), 6) == 10.0


def test_profit_cagr():
    assert round(profit_cagr(100, 144, 2), 6) == 20.0


def test_eps_cagr():
    assert round(eps_cagr(4, 9, 3), 6) == round(
        ((9 / 4) ** (1 / 3) - 1) * 100,
        6,
    )


def test_cagr_missing_value():
    assert calculate_cagr(None, 100, 3) is None


def test_cagr_zero_start():
    assert calculate_cagr(0, 100, 3) is None


def test_cagr_negative_start():
    assert calculate_cagr(-100, 200, 3) is None


def test_cagr_negative_end():
    assert calculate_cagr(100, -200, 3) is None


def test_cagr_invalid_period():
    assert calculate_cagr(100, 200, 0) is None


def test_cfo_quality():
    assert cfo_quality(200, 100) == 2.0


def test_capex_intensity():
    assert capex_intensity(-100, 1000) == 10.0


def test_free_cash_flow_conversion():
    assert free_cash_flow_conversion(200, 100) == 2.0


def test_free_cash_flow_margin():
    assert free_cash_flow_margin(200, 1000) == 20.0


def test_cash_flow_to_debt():
    assert cash_flow_to_debt(200, 1000) == 0.2


def test_investing_to_cfo():
    assert investing_to_cfo(-100, 500) == -0.2


def test_financing_to_cfo():
    assert financing_to_cfo(100, 500) == 0.2
