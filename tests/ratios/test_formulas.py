from src.ratios.formulas import (
    asset_turnover,
    debt_to_equity,
    free_cash_flow,
    interest_coverage,
    net_profit_margin,
    operating_profit_margin,
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