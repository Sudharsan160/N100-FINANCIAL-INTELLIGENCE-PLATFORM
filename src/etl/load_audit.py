import sqlite3
from pathlib import Path

import pandas as pd


TABLES = [
    "analysis",
    "balancesheet",
    "cashflow",
    "companies",
    "documents",
    "financial_ratios",
    "market_cap",
    "peer_groups",
    "profitandloss",
    "prosandcons",
    "sectors",
    "stock_prices",
]


EXPECTED_COUNTS = {
    "analysis": 20,
    "balancesheet": 1312,
    "cashflow": 1187,
    "companies": 92,
    "documents": 1585,
    "financial_ratios": 1184,
    "market_cap": 552,
    "peer_groups": 56,
    "profitandloss": 1276,
    "prosandcons": 16,
    "sectors": 92,
    "stock_prices": 5520,
}


def create_load_audit(
    db_path: str | Path = "nifty100.db",
    output_path: str | Path = "output/load_audit.csv",
) -> pd.DataFrame:
    """Compare SQLite row counts against expected source row counts."""

    connection = sqlite3.connect(db_path)

    rows = []

    try:
        for table in TABLES:
            actual = connection.execute(
                f"SELECT COUNT(*) FROM [{table}]"
            ).fetchone()[0]

            expected = EXPECTED_COUNTS[table]

            rows.append(
                {
                    "table_name": table,
                    "expected_rows": expected,
                    "actual_rows": actual,
                    "difference": actual - expected,
                    "status": "PASS" if actual == expected else "FAIL",
                }
            )
    finally:
        connection.close()

    result = pd.DataFrame(rows)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)

    return result


if __name__ == "__main__":
    audit = create_load_audit()

    print(audit.to_string(index=False))
    print()
    print("Audit file created: output/load_audit.csv")