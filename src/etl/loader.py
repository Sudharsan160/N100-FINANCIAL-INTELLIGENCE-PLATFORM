"""
Excel loader for the N100 Financial Intelligence Platform.

Loads the 12 supplied N100 Excel source files and normalizes:
- company_id
- year
- ticker/company identifiers
"""

from pathlib import Path
from typing import Optional

import pandas as pd
import os
import sqlite3

from src.etl.normaliser import normalize_ticker, normalize_year


RAW_DATA_DIR = Path("data/raw")

# These workbooks have a title/description row before the real headers.
HEADER_ROW_1 = {
    "analysis.xlsx": 1,
    "balancesheet.xlsx": 1,
    "cashflow.xlsx": 1,
    "companies.xlsx": 1,
    "documents.xlsx": 1,
    "profitandloss.xlsx": 1,
    "prosandcons.xlsx": 1,
}

# These workbooks already have the real header on row 1.
HEADER_ROW_0 = {
    "financial_ratios.xlsx": 0,
    "market_cap.xlsx": 0,
    "peer_groups.xlsx": 0,
    "sectors.xlsx": 0,
    "stock_prices.xlsx": 0,
}


def get_header_row(file_path: str | Path) -> int:
    """Return the correct Excel header row for a source file."""
    filename = Path(file_path).name.lower()

    if filename in HEADER_ROW_1:
        return HEADER_ROW_1[filename]

    if filename in HEADER_ROW_0:
        return HEADER_ROW_0[filename]

    raise ValueError(f"Unknown source workbook: {filename}")


def load_excel(
    file_path: str | Path,
    sheet_name: Optional[str | int] = 0,
) -> pd.DataFrame:
    """
    Load one N100 Excel workbook using its correct header row.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    if path.suffix.lower() not in {".xlsx", ".xls", ".xlsm"}:
        raise ValueError(f"Unsupported Excel file type: {path.suffix}")

    header_row = get_header_row(path)

    df = pd.read_excel(
        path,
        sheet_name=sheet_name,
        header=header_row,
    )

    # Remove completely empty rows/columns.
    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")

    # Standardize column names.
    df.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in df.columns
    ]

    return df


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize known columns without changing the source DataFrame.
    """
    result = df.copy()

    # company_id in these datasets is the stock ticker.
    if "company_id" in result.columns:
        result["company_id"] = result["company_id"].apply(normalize_ticker)

    # Normalize year values such as:
    # "Dec 2012", "Mar 2014", "FY2024" -> 2012, 2014, 2024
    if "year" in result.columns:
        result["year"] = result["year"].apply(normalize_year)

    # Stock-price files contain date instead of year.
    if "date" in result.columns:
        result["date"] = pd.to_datetime(
            result["date"],
            errors="coerce",
        )

    return result


def load_and_normalize(
    file_path: str | Path,
    sheet_name: Optional[str | int] = 0,
) -> pd.DataFrame:
    """Load and normalize one workbook."""
    df = load_excel(
        file_path,
        sheet_name=sheet_name,
    )

    return normalize_dataframe(df)


def list_excel_files(
    data_dir: str | Path = RAW_DATA_DIR,
) -> list[Path]:
    """Return all supported Excel workbooks."""
    directory = Path(data_dir)

    if not directory.exists():
        raise FileNotFoundError(
            f"Data directory not found: {directory}"
        )

    if not directory.is_dir():
        raise NotADirectoryError(
            f"Not a directory: {directory}"
        )

    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".xlsx", ".xls", ".xlsm"}
    )


def load_all_sources(
    data_dir: str | Path = Path("data/raw"),
) -> dict[str, pd.DataFrame]:
    """
    Load and normalize all Excel source files.

    Returns:
        Dictionary keyed by workbook filename without extension.
    """
    datasets: dict[str, pd.DataFrame] = {}

    for path in list_excel_files(data_dir):
        key = path.stem.lower()
        datasets[key] = load_and_normalize(path)

    return datasets

def load_to_sqlite(
    db_path: str | Path = "nifty100.db",
    data_dir: str | Path = RAW_DATA_DIR,
) -> dict[str, int]:
    """
    Load all normalized source datasets into SQLite.

    Companies are loaded first, followed by dependent tables.
    Foreign keys are enabled during the load.
    """
    db_path = Path(db_path)

    if db_path.exists():
        print(f"Using existing database: {db_path}")

    datasets = load_all_sources(data_dir)

    load_order = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
        "sectors",
        "stock_prices",
        "financial_ratios",
        "market_cap",
        "peer_groups",
    ]

    connection = sqlite3.connect(db_path)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        row_counts: dict[str, int] = {}

        for table_name in load_order:
            if table_name not in datasets:
                continue

            df = datasets[table_name]

            # Replace existing rows so the load is reproducible.
            df.to_sql(
                table_name,
                connection,
                if_exists="replace",
                index=False,
            )

            row_counts[table_name] = len(df)
            print(f"{table_name}: {len(df)} rows loaded")

        connection.commit()

        return row_counts

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

if __name__ == "__main__":
    print("N100 Excel loader is ready.")

    files = list_excel_files()

    print(f"Found {len(files)} Excel source files:")

    for file_path in files:
        print(f"  - {file_path.name}")