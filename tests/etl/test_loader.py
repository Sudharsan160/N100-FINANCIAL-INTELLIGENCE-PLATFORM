import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from src.etl import loader


def test_get_header_row_title_row_workbook():
    assert loader.get_header_row("analysis.xlsx") == 1


def test_get_header_row_real_header_workbook():
    assert loader.get_header_row("financial_ratios.xlsx") == 0


def test_get_header_row_unknown_workbook():
    with pytest.raises(ValueError, match="Unknown source workbook"):
        loader.get_header_row("unknown.xlsx")


def test_load_excel_missing_file():
    with pytest.raises(FileNotFoundError, match="Excel file not found"):
        loader.load_excel("does_not_exist.xlsx")


def test_load_excel_rejects_unsupported_extension(tmp_path: Path):
    path = tmp_path / "sample.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported Excel file type"):
        loader.load_excel(path)


def test_load_excel_cleans_and_normalizes_columns(monkeypatch, tmp_path: Path):
    path = tmp_path / "analysis.xlsx"
    path.write_bytes(b"placeholder")

    source = pd.DataFrame(
        {
            " Company ID ": [" TCS ", None],
            "Year": [2024, None],
            "Empty Column": [None, None],
            "Value": [10, None],
        }
    )

    monkeypatch.setattr(
        loader.pd,
        "read_excel",
        lambda *args, **kwargs: source.copy(),
    )

    result = loader.load_excel(path)

    assert list(result.columns) == ["company_id", "year", "value"]
    assert len(result) == 1
    assert result.iloc[0]["company_id"] == " TCS "


def test_normalize_dataframe_normalizes_ticker_and_year():
    source = pd.DataFrame(
        {
            "company_id": [" reliance.ns ", "TCS.BO"],
            "year": ["FY2024", "Mar-13"],
        }
    )

    result = loader.normalize_dataframe(source)

    assert result["company_id"].tolist() == ["RELIANCE", "TCS"]
    assert result["year"].tolist() == [2024, 2013]
    assert source["company_id"].tolist() == [
        " reliance.ns ",
        "TCS.BO",
    ]


def test_normalize_dataframe_parses_dates():
    source = pd.DataFrame(
        {
            "date": [
                "2024-01-15",
                "not-a-date",
                None,
            ]
        }
    )

    result = loader.normalize_dataframe(source)

    assert pd.api.types.is_datetime64_any_dtype(result["date"])
    assert result.loc[0, "date"] == pd.Timestamp("2024-01-15")
    assert pd.isna(result.loc[1, "date"])
    assert pd.isna(result.loc[2, "date"])


def test_list_excel_files_returns_only_supported_files(tmp_path: Path):
    (tmp_path / "b.xlsx").write_bytes(b"")
    (tmp_path / "a.xls").write_bytes(b"")
    (tmp_path / "c.xlsm").write_bytes(b"")
    (tmp_path / "ignore.csv").write_text(
        "a,b\n1,2\n",
        encoding="utf-8",
    )
    (tmp_path / "ignore.txt").write_text(
        "ignore",
        encoding="utf-8",
    )
    (tmp_path / "folder").mkdir()

    result = loader.list_excel_files(tmp_path)

    assert [path.name for path in result] == [
        "a.xls",
        "b.xlsx",
        "c.xlsm",
    ]


def test_load_to_sqlite_writes_all_loaded_datasets(
    monkeypatch,
    tmp_path: Path,
):
    datasets = {
        "companies": pd.DataFrame({"id": ["TCS", "INFY"]}),
        "sectors": pd.DataFrame({"company_id": ["TCS", "INFY"]}),
    }

    monkeypatch.setattr(
        loader,
        "load_all_sources",
        lambda data_dir: datasets,
    )

    db_path = tmp_path / "test.db"

    counts = loader.load_to_sqlite(
        db_path=db_path,
        data_dir=tmp_path,
    )

    assert counts == {
        "companies": 2,
        "sectors": 2,
    }

    connection = sqlite3.connect(db_path)

    try:
        companies_count = connection.execute(
            "SELECT COUNT(*) FROM companies"
        ).fetchone()[0]

        sectors_count = connection.execute("SELECT COUNT(*) FROM sectors").fetchone()[0]
    finally:
        connection.close()

    assert companies_count == 2
    assert sectors_count == 2
