import sqlite3

from src.ratios.repository import (
    build_ratio_rows,
    canonicalize_groups,
    fetch_grouped_records,
)


def test_canonicalize_identical_duplicates():
    groups = {
        ("PNB", 2024): [
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
    }

    result = canonicalize_groups(groups)

    assert len(result) == 1
    assert result[("PNB", 2024)]["id"] == 1


def test_canonicalize_prefers_nonzero_record():
    groups = {
        ("ABB", 2014): [
            {
                "id": 62,
                "company_id": "ABB",
                "year": 2014,
                "operating_activity": 155,
                "investing_activity": -144,
                "financing_activity": -42,
                "net_cash_flow": -31,
            },
            {
                "id": 73,
                "company_id": "ABB",
                "year": 2014,
                "operating_activity": 0,
                "investing_activity": 0,
                "financing_activity": 0,
                "net_cash_flow": 0,
            },
        ]
    }

    result = canonicalize_groups(groups)

    selected = result[("ABB", 2014)]

    assert selected["id"] == 62


def test_fetch_grouped_records():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE test_data (
            id INTEGER,
            company_id TEXT,
            year INTEGER,
            value REAL
        )
    """)

    conn.executemany(
        "INSERT INTO test_data VALUES (?, ?, ?, ?)",
        [
            (1, "AAA", 2024, 100),
            (2, "AAA", 2024, 200),
            (3, "BBB", 2024, 300),
        ],
    )

    groups = fetch_grouped_records(conn, "test_data")

    assert ("AAA", 2024) in groups
    assert ("BBB", 2024) in groups

    assert len(groups[("AAA", 2024)]) == 2
    assert len(groups[("BBB", 2024)]) == 1

    conn.close()


def test_build_ratio_rows_from_minimal_database():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    conn.execute("""
    CREATE TABLE companies (
        id TEXT,
        face_value REAL
    )
""")

    conn.execute("""
    INSERT INTO companies (id, face_value)
    VALUES ('TEST', 10)
""")

    conn.execute("""
        CREATE TABLE profitandloss (
            id INTEGER,
            company_id TEXT,
            year INTEGER,
            sales REAL,
            expenses REAL,
            operating_profit REAL,
            opm_percentage REAL,
            other_income REAL,
            interest REAL,
            depreciation REAL,
            profit_before_tax REAL,
            tax_percentage REAL,
            net_profit REAL,
            eps REAL,
            dividend_payout REAL
        )
    """)

    conn.execute("""
        CREATE TABLE balancesheet (
            id INTEGER,
            company_id TEXT,
            year INTEGER,
            equity_capital REAL,
            reserves REAL,
            borrowings REAL,
            other_liabilities REAL,
            total_liabilities REAL,
            fixed_assets REAL,
            cwip REAL,
            investments REAL,
            other_asset REAL,
            total_assets REAL
        )
    """)

    conn.execute("""
        CREATE TABLE cashflow (
            id INTEGER,
            company_id TEXT,
            year INTEGER,
            operating_activity REAL,
            investing_activity REAL,
            financing_activity REAL,
            net_cash_flow REAL
        )
    """)

    conn.execute("""
        INSERT INTO profitandloss VALUES
        (1, 'TEST', 2024, 1000, 800, 200, 20, 0, 50, 20, 150, 30, 100, 10, 20)
    """)

    conn.execute("""
        INSERT INTO balancesheet VALUES
        (1, 'TEST', 2024, 100, 400, 200, 100, 800, 500, 0, 0, 300, 800)
    """)

    conn.execute("""
        INSERT INTO cashflow VALUES
        (1, 'TEST', 2024, 300, -100, -50, 150)
    """)

    rows = build_ratio_rows(conn)

    assert len(rows) == 1

    row = rows[0]

    assert row["company_id"] == "TEST"
    assert row["year"] == 2024
    assert row["net_profit_margin_pct"] == 10.0
    assert row["operating_profit_margin_pct"] == 20.0
    assert row["return_on_equity_pct"] == 20.0
    assert row["debt_to_equity"] == 0.4
    assert row["interest_coverage"] == 4.0
    assert row["asset_turnover"] == 1.25
    assert row["free_cash_flow_cr"] == 200.0
    assert row["capex_cr"] == 100.0

    conn.close()