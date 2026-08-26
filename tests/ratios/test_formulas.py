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
    return_on_equity,
    safe_divide,
)


def test_safe_divide():
    assert safe_divide(10, 2) == 5.0


def test_safe_divide_zero_denominator():
    assert safe_divide(10, 0) is None


def test_safe_divide_missing_value():
    assert safe_divide(None, 10) is None


def test_net_profit_margin():
    assert net_profit_margin(100, 1000) == 10.0


def test_operating_profit_margin():
    assert operating_profit_margin(200, 1000) == 20.0


def test_return_on_equity():
    assert return_on_equity(100, 500) == 20.0


def test_debt_to_equity():
    assert debt_to_equity(200, 400) == 0.5


def test_interest_coverage():
    assert interest_coverage(500, 100) == 5.0


def test_asset_turnover():
    assert asset_turnover(1000, 500) == 2.0


def test_free_cash_flow():
    assert free_cash_flow(500, -200) == 300.0


def test_negative_equity():
    assert return_on_equity(100, -500) == -20.0
    assert debt_to_equity(200, -400) == -0.5


def test_negative_profit():
    assert net_profit_margin(-100, 1000) == -10.0


def test_zero_sales():
    assert net_profit_margin(100, 0) is None


# Day 09


def test_return_on_assets():
    assert return_on_assets(100, 1000) == 10.0


def test_pretax_margin():
    assert pretax_margin(150, 1000) == 15.0


def test_operating_cash_flow_margin():
    assert operating_cash_flow_margin(200, 1000) == 20.0


def test_cash_flow_to_net_profit():
    assert cash_flow_to_net_profit(200, 100) == 2.0


def test_debt_ratio():
    assert debt_ratio(200, 1000) == 0.2


def test_equity_ratio():
    assert equity_ratio(500, 1000) == 0.5


def test_financial_leverage():
    assert financial_leverage(1000, 500) == 2.0


def test_revenue_growth():
    assert revenue_growth(1200, 1000) == 20.0


def test_operating_profit_growth():
    assert operating_profit_growth(240, 200) == 20.0


def test_net_profit_growth():
    assert net_profit_growth(120, 100) == 20.0


def test_eps_growth():
    assert eps_growth(12, 10) == 20.0


def test_growth_zero_previous():
    assert revenue_growth(100, 0) is None


def test_growth_missing_previous():
    assert net_profit_growth(100, None) is None


# Day 10


def test_growth_negative_previous_returns_none():
    assert revenue_growth(100, -50) is None


def test_growth_turnaround_returns_none():
    assert net_profit_growth(100, -50) is None


def test_growth_positive_to_positive():
    assert revenue_growth(150, 100) == 50.0


def test_growth_negative_to_negative_returns_none():
    assert net_profit_growth(-50, -100) is None


def test_zero_interest_returns_none():
    assert interest_coverage(200, 0) is None


def test_zero_debt_returns_zero():
    assert debt_to_equity(0, 500) == 0.0


def test_negative_eps_growth_from_positive_previous():
    assert eps_growth(-5, 10) == -150.0


def test_negative_eps_previous_returns_none():
    assert eps_growth(10, -5) is None


def test_zero_operating_cash_flow():
    assert free_cash_flow(0, 100) == -100.0


def test_negative_operating_cash_flow():
    assert free_cash_flow(-500, 100) == -600.0


# Day 11 — Cash Flow & Capital Allocation


def test_cfo_to_total_debt():
    assert cfo_to_total_debt(200, 1000) == 0.2


def test_free_cash_flow_margin():
    assert free_cash_flow_margin(200, 1000) == 20.0


def test_investing_cash_flow_to_cfo():
    assert investing_cash_flow_to_cfo(-100, 500) == -0.2


def test_financing_cash_flow_to_cfo():
    assert financing_cash_flow_to_cfo(100, 500) == 0.2


def test_cash_conversion_ratio():
    assert cash_conversion_ratio(300, 200) == 1.5


def test_capital_expenditure_intensity():
    assert capital_expenditure_intensity(-100, 1000) == 10.0


def test_cfo_to_zero_debt():
    assert cfo_to_total_debt(200, 0) is None


def test_investing_cash_flow_zero_cfo():
    assert investing_cash_flow_to_cfo(-100, 0) is None