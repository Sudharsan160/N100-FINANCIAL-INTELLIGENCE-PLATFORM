from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DB_PATH = PROJECT_ROOT / "nifty100.db"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "screener_config.yaml"


class ScreenerEngine:
    """
    N100 Financial Intelligence Platform
    Sprint 3 — Day 15 Screener Engine

    Responsibilities:
    - Load latest-year financial data
    - Derive 3Y / 5Y CAGR metrics
    - Derive CFO/PAT ratio
    - Apply 15 screener filters
    - Apply Financials D/E carve-out for D/E max
    - Treat debt-free ICR as infinity
    - Calculate sector-relative composite quality score
    - Sort results by composite score
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        config_path: str | Path = DEFAULT_CONFIG_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.config_path = Path(config_path)

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.db_path}"
            )

        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Config not found: {self.config_path}"
            )

        self.config = self._load_config()

    # ============================================================
    # CONFIG
    # ============================================================

    def _load_config(self) -> dict[str, Any]:
        """Load screener_config.yaml."""

        with self.config_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            config = yaml.safe_load(file)

        if not isinstance(config, dict):
            raise ValueError(
                "screener_config.yaml must contain a YAML mapping."
            )

        return config

    # ============================================================
    # DATABASE HELPERS
    # ============================================================

    @staticmethod
    def _read_table(
        conn: sqlite3.Connection,
        table_name: str,
    ) -> pd.DataFrame:
        """Read an allowed SQLite table."""

        allowed_tables = {
            "financial_ratios",
            "profitandloss",
            "cashflow",
            "market_cap",
            "sectors",
            "companies",
        }

        if table_name not in allowed_tables:
            raise ValueError(
                f"Unsupported table: {table_name}"
            )

        return pd.read_sql_query(
            f"SELECT * FROM {table_name}",
            conn,
        )

    @staticmethod
    def _to_numeric(
        df: pd.DataFrame,
        columns: list[str],
    ) -> pd.DataFrame:
        """Convert available columns to numeric."""

        result = df.copy()

        for column in columns:
            if column in result.columns:
                result[column] = pd.to_numeric(
                    result[column],
                    errors="coerce",
                )

        return result

    # ============================================================
    # CAGR
    # ============================================================

    @staticmethod
    def _calculate_cagr_table(
        history: pd.DataFrame,
        value_column: str,
        output_column: str,
        years: int,
    ) -> pd.DataFrame:
        """
        Calculate CAGR using exactly N years.

        Rules:
        - Positive base + positive end -> CAGR
        - Positive base + negative end -> NaN
        - Negative base -> NaN
        - Zero base -> NaN
        - Insufficient history -> NaN
        """

        required = {
            "company_id",
            "year",
            value_column,
        }

        missing = required - set(history.columns)

        if missing:
            raise KeyError(
                f"Missing columns for CAGR calculation: {sorted(missing)}"
            )

        data = history[
            [
                "company_id",
                "year",
                value_column,
            ]
        ].copy()

        data["year"] = pd.to_numeric(
            data["year"],
            errors="coerce",
        )

        data[value_column] = pd.to_numeric(
            data[value_column],
            errors="coerce",
        )

        data = data.dropna(
            subset=[
                "company_id",
                "year",
                value_column,
            ]
        )

        data = data.drop_duplicates(
            subset=[
                "company_id",
                "year",
            ],
            keep="last",
        )

        data = data.sort_values(
            [
                "company_id",
                "year",
            ]
        )

        rows: list[dict[str, Any]] = []

        for company_id, group in data.groupby(
            "company_id",
            sort=False,
        ):
            group = group.set_index("year")

            for end_year in group.index:

                start_year = end_year - years

                if start_year not in group.index:
                    continue

                start_value = float(
                    group.loc[
                        start_year,
                        value_column,
                    ]
                )

                end_value = float(
                    group.loc[
                        end_year,
                        value_column,
                    ]
                )

                if not np.isfinite(start_value):
                    continue

                if not np.isfinite(end_value):
                    continue

                if start_value <= 0:
                    continue

                if end_value <= 0:
                    continue

                cagr = (
                    (
                        end_value
                        / start_value
                    )
                    ** (1.0 / years)
                    - 1.0
                ) * 100.0

                rows.append(
                    {
                        "company_id": company_id,
                        "year": int(end_year),
                        output_column: cagr,
                    }
                )

        return pd.DataFrame(rows)

    # ============================================================
    # LOAD SCREENING DATA
    # ============================================================

    def load_data(
        self,
        year: int | str = "latest",
    ) -> pd.DataFrame:
        """
        Load and construct the latest-year screening universe.
        """

        with sqlite3.connect(self.db_path) as conn:

            ratios = self._read_table(
                conn,
                "financial_ratios",
            )

            pnl = self._read_table(
                conn,
                "profitandloss",
            )

            cashflow = self._read_table(
                conn,
                "cashflow",
            )

            market = self._read_table(
                conn,
                "market_cap",
            )

            sectors = self._read_table(
                conn,
                "sectors",
            )

            companies = self._read_table(
                conn,
                "companies",
            )

        # --------------------------------------------------------
        # Year cleanup
        # --------------------------------------------------------

        for frame in [
            ratios,
            pnl,
            cashflow,
            market,
        ]:
            frame["year"] = pd.to_numeric(
                frame["year"],
                errors="coerce",
            )

        if ratios.empty:
            raise ValueError(
                "financial_ratios table is empty."
            )

        if year == "latest":
            selected_year = int(
                ratios["year"].max()
            )
        else:
            selected_year = int(year)

        # --------------------------------------------------------
        # Remove duplicate records
        # --------------------------------------------------------

        ratios = ratios.drop_duplicates(
            subset=[
                "company_id",
                "year",
            ],
            keep="last",
        )

        pnl = pnl.drop_duplicates(
            subset=[
                "company_id",
                "year",
            ],
            keep="last",
        )

        cashflow = cashflow.drop_duplicates(
            subset=[
                "company_id",
                "year",
            ],
            keep="last",
        )

        market = market.drop_duplicates(
            subset=[
                "company_id",
                "year",
            ],
            keep="last",
        )

        sectors = sectors.drop_duplicates(
            subset=[
                "company_id",
            ],
            keep="last",
        )

        companies = companies.drop_duplicates(
            subset=[
                "id",
            ],
            keep="last",
        )

        # --------------------------------------------------------
        # Numeric source columns
        # --------------------------------------------------------

        pnl = self._to_numeric(
            pnl,
            [
                "sales",
                "net_profit",
                "eps",
                "operating_profit",
                "opm_percentage",
                "other_income",
                "interest",
            ],
        )

        cashflow = self._to_numeric(
            cashflow,
            [
                "operating_activity",
                "investing_activity",
                "financing_activity",
            ],
        )

        ratios = self._to_numeric(
            ratios,
            [
                "net_profit_margin_pct",
                "operating_profit_margin_pct",
                "return_on_equity_pct",
                "debt_to_equity",
                "interest_coverage",
                "asset_turnover",
                "free_cash_flow_cr",
                "capex_cr",
                "earnings_per_share",
                "book_value_per_share",
                "dividend_payout_ratio_pct",
                "total_debt_cr",
                "cash_from_operations_cr",
                "roce_pct",
            ],
        )

        market = self._to_numeric(
            market,
            [
                "market_cap_crore",
                "enterprise_value_crore",
                "pe_ratio",
                "pb_ratio",
                "ev_ebitda",
                "dividend_yield_pct",
            ],
        )

        # --------------------------------------------------------
        # FCF history
        # --------------------------------------------------------

        cashflow["free_cash_flow"] = (
            cashflow["operating_activity"].fillna(0)
            + cashflow["investing_activity"].fillna(0)
        )

        # --------------------------------------------------------
        # CAGR tables
        # --------------------------------------------------------

        revenue_cagr_3 = self._calculate_cagr_table(
            pnl,
            value_column="sales",
            output_column="revenue_cagr_3yr",
            years=3,
        )

        revenue_cagr_5 = self._calculate_cagr_table(
            pnl,
            value_column="sales",
            output_column="revenue_cagr_5yr",
            years=5,
        )

        pat_cagr_3 = self._calculate_cagr_table(
            pnl,
            value_column="net_profit",
            output_column="pat_cagr_3yr",
            years=3,
        )

        pat_cagr_5 = self._calculate_cagr_table(
            pnl,
            value_column="net_profit",
            output_column="pat_cagr_5yr",
            years=5,
        )

        eps_cagr_5 = self._calculate_cagr_table(
            pnl,
            value_column="eps",
            output_column="eps_cagr_5yr",
            years=5,
        )

        fcf_cagr_5 = self._calculate_cagr_table(
            cashflow,
            value_column="free_cash_flow",
            output_column="fcf_cagr_5yr",
            years=5,
        )

        # --------------------------------------------------------
        # Latest year tables
        # --------------------------------------------------------

        latest_ratios = ratios.loc[
            ratios["year"] == selected_year
        ].copy()

        latest_pnl = pnl.loc[
            pnl["year"] == selected_year
        ].copy()

        latest_cashflow = cashflow.loc[
            cashflow["year"] == selected_year
        ].copy()

        latest_market = market.loc[
            market["year"] == selected_year
        ].copy()

        # --------------------------------------------------------
        # P&L columns
        # --------------------------------------------------------

        pnl_columns = [
            "company_id",
            "year",
            "sales",
            "net_profit",
            "operating_profit",
            "eps",
        ]

        latest_pnl = latest_pnl[
            [
                column
                for column in pnl_columns
                if column in latest_pnl.columns
            ]
        ]

        # --------------------------------------------------------
        # Cashflow columns
        # --------------------------------------------------------

        cashflow_columns = [
            "company_id",
            "year",
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "free_cash_flow",
        ]

        latest_cashflow = latest_cashflow[
            [
                column
                for column in cashflow_columns
                if column in latest_cashflow.columns
            ]
        ]

        # --------------------------------------------------------
        # Market columns
        # --------------------------------------------------------

        market_columns = [
            "company_id",
            "year",
            "market_cap_crore",
            "enterprise_value_crore",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield_pct",
        ]

        latest_market = latest_market[
            [
                column
                for column in market_columns
                if column in latest_market.columns
            ]
        ]

        # --------------------------------------------------------
        # Merge
        # --------------------------------------------------------

        data = latest_ratios.merge(
            latest_pnl,
            on=[
                "company_id",
                "year",
            ],
            how="left",
            suffixes=(
                "",
                "_pnl",
            ),
        )

        data = data.merge(
            latest_cashflow,
            on=[
                "company_id",
                "year",
            ],
            how="left",
            suffixes=(
                "",
                "_cf",
            ),
        )

        data = data.merge(
            latest_market,
            on=[
                "company_id",
                "year",
            ],
            how="left",
        )

        # --------------------------------------------------------
        # Sector
        # --------------------------------------------------------

        sector_columns = [
            "company_id",
            "broad_sector",
            "sub_sector",
        ]

        sectors = sectors[
            [
                column
                for column in sector_columns
                if column in sectors.columns
            ]
        ]

        data = data.merge(
            sectors,
            on="company_id",
            how="left",
        )

        # --------------------------------------------------------
        # Company
        # --------------------------------------------------------

        companies = companies.rename(
            columns={
                "id": "company_id",
            }
        )

        company_columns = [
            "company_id",
            "company_name",
        ]

        companies = companies[
            [
                column
                for column in company_columns
                if column in companies.columns
            ]
        ]

        data = data.merge(
            companies,
            on="company_id",
            how="left",
        )

        # --------------------------------------------------------
        # CAGR merges
        # --------------------------------------------------------

        for cagr_table in [
            revenue_cagr_3,
            revenue_cagr_5,
            pat_cagr_3,
            pat_cagr_5,
            eps_cagr_5,
            fcf_cagr_5,
        ]:

            if cagr_table.empty:
                continue

            data = data.merge(
                cagr_table,
                on=[
                    "company_id",
                    "year",
                ],
                how="left",
            )

        # --------------------------------------------------------
        # CFO / PAT
        # --------------------------------------------------------

        data["cfo_pat_ratio"] = np.where(
            data["net_profit"].notna()
            & data["net_profit"].ne(0),
            data["operating_activity"]
            / data["net_profit"],
            np.nan,
        )

        # --------------------------------------------------------
        # Ensure FCF
        # --------------------------------------------------------

        if "free_cash_flow_cr" not in data.columns:
            data["free_cash_flow_cr"] = (
                data["free_cash_flow"]
            )

        # --------------------------------------------------------
        # ICR STANDARDIZATION
        # --------------------------------------------------------

        data["interest_coverage"] = pd.to_numeric(
            data["interest_coverage"],
            errors="coerce",
        )

        # Older representation:
        # 999 = Debt Free
        data["interest_coverage"] = data[
            "interest_coverage"
        ].replace(
            [999, 999.0],
            np.inf,
        )

        # Current database representation:
        # zero D/E or zero total debt = Debt Free.
        # Debt-free companies should always pass any
        # finite ICR threshold.
        debt_free = (
            data["debt_to_equity"].eq(0)
            | data["total_debt_cr"].eq(0)
        )

        data.loc[
            debt_free,
            "interest_coverage",
        ] = np.inf

        # --------------------------------------------------------
        # Sector cleanup
        # --------------------------------------------------------

        if "broad_sector" not in data.columns:
            data["broad_sector"] = "Unknown"

        data["broad_sector"] = (
            data["broad_sector"]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
        )

        # --------------------------------------------------------
        # Final numeric cleanup
        # --------------------------------------------------------

        numeric_columns = [
            "year",
            "return_on_equity_pct",
            "roce_pct",
            "net_profit_margin_pct",
            "operating_profit_margin_pct",
            "debt_to_equity",
            "interest_coverage",
            "asset_turnover",
            "free_cash_flow_cr",
            "market_cap_crore",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield_pct",
            "dividend_payout_ratio_pct",
            "sales",
            "net_profit",
            "eps",
            "revenue_cagr_3yr",
            "revenue_cagr_5yr",
            "pat_cagr_3yr",
            "pat_cagr_5yr",
            "eps_cagr_5yr",
            "fcf_cagr_5yr",
            "cfo_pat_ratio",
        ]

        data = self._to_numeric(
            data,
            numeric_columns,
        )

        # --------------------------------------------------------
        # Final duplicate safety
        # --------------------------------------------------------

        data = data.drop_duplicates(
            subset=[
                "company_id",
                "year",
            ],
            keep="last",
        )

        return data.reset_index(
            drop=True
        )

    # ============================================================
    # NORMALIZATION
    # ============================================================

    @staticmethod
    def _winsor_score(
        series: pd.Series,
        inverse: bool = False,
    ) -> pd.Series:
        """
        Winsorize at P10/P90 and scale to 0–100.
        """

        values = pd.to_numeric(
            series,
            errors="coerce",
        )

        if values.notna().sum() == 0:
            return pd.Series(
                np.nan,
                index=series.index,
                dtype=float,
            )

        p10 = values.quantile(0.10)
        p90 = values.quantile(0.90)

        clipped = values.clip(
            lower=p10,
            upper=p90,
        )

        if pd.isna(p10) or pd.isna(p90):
            return pd.Series(
                np.nan,
                index=series.index,
                dtype=float,
            )

        if np.isclose(
            p10,
            p90,
        ):
            scores = pd.Series(
                50.0,
                index=series.index,
                dtype=float,
            )
        else:
            scores = (
                (
                    clipped - p10
                )
                / (p90 - p10)
                * 100.0
            )

        if inverse:
            scores = 100.0 - scores

        return scores.clip(
            0,
            100,
        )

    def _sector_score(
        self,
        data: pd.DataFrame,
        column: str,
        inverse: bool = False,
    ) -> pd.Series:
        """
        P10/P90 normalization inside broad sectors.
        """

        result = pd.Series(
            np.nan,
            index=data.index,
            dtype=float,
        )

        if column not in data.columns:
            return result

        sectors = (
            data["broad_sector"]
            .fillna("Unknown")
            .astype(str)
        )

        for sector_name in sectors.unique():

            indices = data.index[
                sectors == sector_name
            ]

            values = data.loc[
                indices,
                column,
            ]

            result.loc[indices] = (
                self._winsor_score(
                    values,
                    inverse=inverse,
                )
            )

        return result

    # ============================================================
    # LEVERAGE SCORING
    # ============================================================

    @staticmethod
    def _de_score(
        series: pd.Series,
    ) -> pd.Series:
        """Convert D/E into the project score."""

        de = pd.to_numeric(
            series,
            errors="coerce",
        )

        return pd.Series(
            np.select(
                [
                    de <= 0,
                    de <= 0.5,
                    de <= 1,
                    de <= 2,
                    de > 5,
                ],
                [
                    100,
                    85,
                    70,
                    50,
                    0,
                ],
                default=25,
            ),
            index=series.index,
            dtype=float,
        )

    @staticmethod
    def _icr_score(
        series: pd.Series,
    ) -> pd.Series:
        """Convert ICR into the project score."""

        icr = pd.to_numeric(
            series,
            errors="coerce",
        )

        return pd.Series(
            np.select(
                [
                    np.isinf(icr),
                    icr > 10,
                    icr >= 5,
                    icr >= 3,
                    icr < 1.5,
                ],
                [
                    100,
                    100,
                    75,
                    50,
                    0,
                ],
                default=25,
            ),
            index=series.index,
            dtype=float,
        )

    # ============================================================
    # COMPOSITE QUALITY SCORE
    # ============================================================

    def add_composite_quality_score(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate sector-relative composite quality score.

        Profitability = 35%
        Cash Quality  = 30%
        Growth        = 20%
        Leverage      = 15%
        """

        result = data.copy()

        # --------------------------------------------------------
        # Profitability — 35%
        # --------------------------------------------------------

        roe_score = self._sector_score(
            result,
            "return_on_equity_pct",
        )

        roce_score = self._sector_score(
            result,
            "roce_pct",
        )

        npm_score = self._sector_score(
            result,
            "net_profit_margin_pct",
        )

        profitability_score = (
            roe_score * 0.15
            + roce_score * 0.10
            + npm_score * 0.10
        )

        # --------------------------------------------------------
        # Cash Quality — 30%
        # --------------------------------------------------------

        fcf_cagr_score = self._sector_score(
            result,
            "fcf_cagr_5yr",
        )

        cfo_pat_score = self._sector_score(
            result,
            "cfo_pat_ratio",
        )

        fcf_positive_score = pd.Series(
            np.where(
                result["free_cash_flow_cr"] > 0,
                100.0,
                0.0,
            ),
            index=result.index,
            dtype=float,
        )

        cash_quality_score = (
            fcf_cagr_score * 0.15
            + cfo_pat_score * 0.10
            + fcf_positive_score * 0.05
        )

        # --------------------------------------------------------
        # Growth — 20%
        # --------------------------------------------------------

        revenue_growth_score = self._sector_score(
            result,
            "revenue_cagr_5yr",
        )

        pat_growth_score = self._sector_score(
            result,
            "pat_cagr_5yr",
        )

        growth_score = (
            revenue_growth_score * 0.10
            + pat_growth_score * 0.10
        )

        # --------------------------------------------------------
        # Leverage — 15%
        # --------------------------------------------------------

        de_score = self._de_score(
            result["debt_to_equity"]
        )

        icr_score = self._icr_score(
            result["interest_coverage"]
        )

        leverage_score = (
            de_score * 0.10
            + icr_score * 0.05
        )

        # --------------------------------------------------------
        # Final score
        # --------------------------------------------------------

        result["profitability_score"] = (
            profitability_score
        )

        result["cash_quality_score"] = (
            cash_quality_score
        )

        result["growth_score"] = (
            growth_score
        )

        result["leverage_score"] = (
            leverage_score
        )

        result["composite_quality_score"] = (
            profitability_score
            + cash_quality_score
            + growth_score
            + leverage_score
        ).clip(
            0,
            100,
        ).round(2)

        return result

    # ============================================================
    # FILTER
    # ============================================================

    @staticmethod
    def _apply_numeric_filter(
        data: pd.DataFrame,
        column: str,
        operator: str,
        value: float,
    ) -> pd.Series:
        """Apply one numeric filter."""

        if column not in data.columns:
            raise KeyError(
                f"Screener column not found: {column}"
            )

        series = pd.to_numeric(
            data[column],
            errors="coerce",
        )

        if operator == ">":
            mask = series > value

        elif operator == ">=":
            mask = series >= value

        elif operator == "<":
            mask = series < value

        elif operator == "<=":
            mask = series <= value

        elif operator == "==":
            mask = np.isclose(
                series,
                value,
                atol=1e-9,
                equal_nan=False,
            )

        else:
            raise ValueError(
                f"Unsupported operator: {operator}"
            )

        return pd.Series(
            mask,
            index=data.index,
        ).fillna(False)

    def apply_filters(
        self,
        data: pd.DataFrame,
        thresholds: dict[str, Any],
    ) -> pd.DataFrame:
        """
        Apply custom threshold filters.

        Special rules:
        - Financials are exempt from D/E max.
        - Debt-free companies have infinite ICR.
        - D/E declining compares current vs previous year.
        """

        result = data.copy()

        if result.empty:
            return result

        mask = pd.Series(
            True,
            index=result.index,
        )

        filter_config = self.config.get(
            "filters",
            {},
        )

        # --------------------------------------------------------
        # Standard filters
        # --------------------------------------------------------

        for metric, threshold in thresholds.items():

            if threshold is None:
                continue

            if metric in {
                "de_exact",
                "de_declining",
                "revenue_cagr_3yr_min",
                "dividend_payout_max",
            }:
                continue

            if metric not in filter_config:
                raise KeyError(
                    f"Unknown screener filter: {metric}"
                )

            definition = filter_config[
                metric
            ]

            column = definition[
                "column"
            ]

            operator = definition[
                "operator"
            ]

            current_mask = (
                self._apply_numeric_filter(
                    result,
                    column,
                    operator,
                    float(threshold),
                )
            )

            # IMPORTANT:
            # Only D/E MAX receives the Financials carve-out.
            if metric == "de_max":

                financials = (
                    result["broad_sector"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .str.casefold()
                    .eq("financials")
                )

                current_mask = (
                    current_mask
                    | financials
                )

            mask &= current_mask

        # --------------------------------------------------------
        # Dividend payout max
        # --------------------------------------------------------

        if "dividend_payout_max" in thresholds:

            current_mask = (
                self._apply_numeric_filter(
                    result,
                    "dividend_payout_ratio_pct",
                    "<=",
                    float(
                        thresholds[
                            "dividend_payout_max"
                        ]
                    ),
                )
            )

            mask &= current_mask

        # --------------------------------------------------------
        # Revenue CAGR 3Y
        # --------------------------------------------------------

        if "revenue_cagr_3yr_min" in thresholds:

            current_mask = (
                self._apply_numeric_filter(
                    result,
                    "revenue_cagr_3yr",
                    ">=",
                    float(
                        thresholds[
                            "revenue_cagr_3yr_min"
                        ]
                    ),
                )
            )

            mask &= current_mask

        # --------------------------------------------------------
        # D/E exactly zero
        # --------------------------------------------------------

        if "de_exact" in thresholds:

            current_mask = (
                self._apply_numeric_filter(
                    result,
                    "debt_to_equity",
                    "==",
                    float(
                        thresholds["de_exact"]
                    ),
                )
            )

            # NO Financials exemption here.
            # Debt-Free Blue Chip really means D/E = 0.
            mask &= current_mask

        # --------------------------------------------------------
        # D/E declining YoY
        # --------------------------------------------------------

        if thresholds.get(
            "de_declining",
            False,
        ):

            with sqlite3.connect(
                self.db_path
            ) as conn:

                history = pd.read_sql_query(
                    """
                    SELECT
                        company_id,
                        year,
                        debt_to_equity
                    FROM financial_ratios
                    ORDER BY company_id, year
                    """,
                    conn,
                )

            history["year"] = pd.to_numeric(
                history["year"],
                errors="coerce",
            )

            history["debt_to_equity"] = pd.to_numeric(
                history["debt_to_equity"],
                errors="coerce",
            )

            history = history.drop_duplicates(
                subset=[
                    "company_id",
                    "year",
                ],
                keep="last",
            )

            history = history.sort_values(
                [
                    "company_id",
                    "year",
                ]
            )

            history["previous_de"] = (
                history
                .groupby("company_id")[
                    "debt_to_equity"
                ]
                .shift(1)
            )

            latest_year = int(
                history["year"].max()
            )

            latest_history = history.loc[
                history["year"] == latest_year
            ].copy()

            latest_history["is_declining"] = (
                latest_history["debt_to_equity"]
                <
                latest_history["previous_de"]
            )

            decline_map = latest_history.set_index(
                "company_id"
            )["is_declining"]

            current_mask = (
                result["company_id"]
                .map(decline_map)
                .fillna(False)
            )

            mask &= current_mask

        # --------------------------------------------------------
        # Final
        # --------------------------------------------------------

        return result.loc[
            mask
        ].copy()

    # ============================================================
    # SCREEN
    # ============================================================

    def screen(
        self,
        thresholds: dict[str, Any] | None = None,
        year: int | str = "latest",
    ) -> pd.DataFrame:
        """Run a custom screener."""

        data = self.load_data(
            year=year
        )

        data = self.add_composite_quality_score(
            data
        )

        if thresholds:
            data = self.apply_filters(
                data,
                thresholds,
            )

        return data.sort_values(
            by="composite_quality_score",
            ascending=False,
            na_position="last",
        ).reset_index(
            drop=True
        )

    # ============================================================
    # PRESET
    # ============================================================

    def preset(
        self,
        preset_name: str,
        year: int | str = "latest",
    ) -> pd.DataFrame:
        """Run a YAML-defined preset."""

        presets = self.config.get(
            "presets",
            {},
        )

        if preset_name not in presets:
            raise KeyError(
                f"Unknown preset '{preset_name}'. "
                f"Available presets: {list(presets.keys())}"
            )

        preset_config = presets[
            preset_name
        ]

        thresholds = preset_config.get(
            "thresholds",
            {},
        )

        result = self.screen(
            thresholds=thresholds,
            year=year,
        )

        sort_by = preset_config.get(
            "sort_by",
            "composite_quality_score",
        )

        ascending = bool(
            preset_config.get(
                "ascending",
                False,
            )
        )

        if sort_by in result.columns:
            result = result.sort_values(
                by=sort_by,
                ascending=ascending,
                na_position="last",
            )

        return result.reset_index(
            drop=True
        )


# ================================================================
# CONVENIENCE FUNCTION
# ================================================================

def run_screener(
    thresholds: dict[str, Any],
    db_path: str | Path = DEFAULT_DB_PATH,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> pd.DataFrame:
    """Convenience wrapper for a custom screener."""

    engine = ScreenerEngine(
        db_path=db_path,
        config_path=config_path,
    )

    return engine.screen(
        thresholds=thresholds,
    )