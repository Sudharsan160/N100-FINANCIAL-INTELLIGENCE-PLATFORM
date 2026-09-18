import sqlite3
import time
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

START_TIME = time.time()

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "nifty100.db"

TABLES = [
    "companies",
    "sectors",
    "financial_ratios",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "market_cap",
    "peer_groups",
    "peer_percentiles",
    "documents",
]


def get_db_row_counts():
    """Return row counts for all required database tables."""
    counts = {}

    conn = sqlite3.connect(DB_PATH)

    try:
        for table in TABLES:
            query = f"SELECT COUNT(*) FROM [{table}]"
            counts[table] = conn.execute(query).fetchone()[0]
    finally:
        conn.close()

    return counts


@router.get("/health")
def health():
    """Return API and database health information."""
    return {
        "status": "ok",
        "db_row_counts": get_db_row_counts(),
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "version": "1.0.0",
    }
