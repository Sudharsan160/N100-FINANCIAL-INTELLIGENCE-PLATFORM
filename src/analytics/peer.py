from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "nifty100.db"
PEER_GROUPS_PATH = PROJECT_ROOT / "data" / "raw" / "peer_groups.xlsx"


METRIC_COLUMNS = {
    "ROE": "return_on_equity_pct",
    "ROCE": "roce_pct",
    "Net Profit Margin": "net_profit_margin_pct",
    "D/E": "debt_to_equity",
    "FCF": "free_cash_flow_cr",
    "PAT CAGR 5yr": "pat_cagr_5yr",
    "Revenue CAGR 5yr": "revenue_cagr_5yr",
    "EPS CAGR 5yr": "eps_cagr_5yr",
    "Interest Coverage": "interest_coverage",
    "Asset Turnover": "asset_turnover",
}


class PeerPercentileEngine:
    """Day 18 - Peer percentile ranking engine."""

    def __init__(
        self,
        db_path: str | Path = DB_PATH,
        peer_groups_path: str | Path = PEER_GROUPS_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.peer_groups_path = Path(peer_groups_path)

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.db_path}"
            )

        if not self.peer_groups_path.exists():
            raise FileNotFoundError(
                f"Peer groups file not found: {self.peer_groups_path}"
            )

    # ============================================================
    # LOAD PEER GROUPS
    # ============================================================

    def load_peer_groups(self) -> pd.DataFrame:
        """Load peer group assignments from Excel."""

        df = pd.read_excel(
            self.peer_groups_path
        )

        required = {
            "peer_group_name",
            "company_id",
            "is_benchmark",
        }

        missing = required - set(df.columns)

        if missing:
            raise KeyError(
                f"Missing peer group columns: {sorted(missing)}"
            )

        df = df[
            [
                "peer_group_name",
                "company_id",
                "is_benchmark",
            ]
        ].copy()

        df["company_id"] = (
            df["company_id"]
            .astype(str)
            .str.strip()
        )

        df["peer_group_name"] = (
            df["peer_group_name"]
            .astype(str)
            .str.strip()
        )

        return df

    # ============================================================
    # LOAD FINANCIAL DATA
    # ============================================================

    def load_financial_data(self) -> pd.DataFrame:
        """Load latest financial metrics and historical CAGR values."""

        with sqlite3.connect(self.db_path) as conn:

            ratios = pd.read_sql_query(
                """
                SELECT
                    company_id,
                    year,
                    return_on_equity_pct,
                    roce_pct,
                    net_profit_margin_pct,
                    debt_to_equity,
                    free_cash_flow_cr,
                    interest_coverage,
                    asset_turnover
                FROM financial_ratios
                """,
                conn,
            )

            pnl = pd.read_sql_query(
                """
                SELECT
                    company_id,
                    year,
                    sales,
                    net_profit,
                    eps
                FROM profitandloss
                """,
                conn,
            )

        ratios["year"] = pd.to_numeric(
            ratios["year"],
            errors="coerce",
        )

        pnl["year"] = pd.to_numeric(
            pnl["year"],
            errors="coerce",
        )

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

        # --------------------------------------------------------
        # Latest ratio row per company
        # --------------------------------------------------------

        latest = (
            ratios
            .sort_values(
                [
                    "company_id",
                    "year",
                ]
            )
            .groupby(
                "company_id",
                as_index=False,
            )
            .tail(1)
            .copy()
        )

        # --------------------------------------------------------
        # Calculate historical CAGRs
        # --------------------------------------------------------

        revenue_cagr = self._calculate_cagr(
            pnl,
            "sales",
            "revenue_cagr_5yr",
            5,
        )

        pat_cagr = self._calculate_cagr(
            pnl,
            "net_profit",
            "pat_cagr_5yr",
            5,
        )

        eps_cagr = self._calculate_cagr(
            pnl,
            "eps",
            "eps_cagr_5yr",
            5,
        )

        for cagr_table in [
            revenue_cagr,
            pat_cagr,
            eps_cagr,
        ]:

            latest = latest.merge(
                cagr_table,
                on=[
                    "company_id",
                    "year",
                ],
                how="left",
            )

        return latest

    # ============================================================
    # CAGR
    # ============================================================

    @staticmethod
    def _calculate_cagr(
        history: pd.DataFrame,
        value_column: str,
        output_column: str,
        years: int,
    ) -> pd.DataFrame:
        """Calculate CAGR using an exact N-year interval."""

        rows = []

        data = history[
            [
                "company_id",
                "year",
                value_column,
            ]
        ].copy()

        data[value_column] = pd.to_numeric(
            data[value_column],
            errors="coerce",
        )

        data["year"] = pd.to_numeric(
            data["year"],
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

        for company_id, group in data.groupby(
            "company_id",
            sort=False,
        ):

            group = group.sort_values(
                "year"
            ).set_index("year")

            for end_year in group.index:

                start_year = end_year - years

                if start_year not in group.index:
                    continue

                start_value = group.loc[
                    start_year,
                    value_column,
                ]

                end_value = group.loc[
                    end_year,
                    value_column,
                ]

                if pd.isna(start_value) or pd.isna(end_value):
                    continue

                if start_value <= 0 or end_value <= 0:
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
    # PERCENTILE
    # ============================================================

    @staticmethod
    def _percent_rank(
        series: pd.Series,
    ) -> pd.Series:
        """
        PERCENT_RANK equivalent.

        Formula:
            (rank - 1) / (n - 1)

        Result range:
            0.0 to 1.0
        """

        values = pd.to_numeric(
            series,
            errors="coerce",
        )

        valid = values.notna()

        result = pd.Series(
            np.nan,
            index=series.index,
            dtype=float,
        )

        n = valid.sum()

        if n == 0:
            return result

        if n == 1:
            result.loc[valid] = 1.0
            return result

        ranks = values[valid].rank(
            method="min",
            ascending=True,
        )

        result.loc[valid] = (
            (ranks - 1)
            / (n - 1)
        )

        return result

    # ============================================================
    # BUILD PERCENTILES
    # ============================================================

    def compute_percentiles(
        self,
        financial: pd.DataFrame,
        peers: pd.DataFrame,
    ) -> pd.DataFrame:
        """Compute 10 percentile metrics for every peer group."""

        merged = peers.merge(
            financial,
            on="company_id",
            how="left",
        )

        # --------------------------------------------------------
        # No peer group validation
        # --------------------------------------------------------

        if merged.empty:
            print(
                "No peer group assigned"
            )
            return pd.DataFrame(
                columns=[
                    "company_id",
                    "peer_group_name",
                    "metric",
                    "value",
                    "percentile_rank",
                    "year",
                ]
            )

        output_rows = []

        for peer_group_name, group in merged.groupby(
            "peer_group_name",
            sort=True,
        ):

            print(
                f"Processing peer group: "
                f"{peer_group_name}"
            )

            for metric_name, column_name in METRIC_COLUMNS.items():

                values = pd.to_numeric(
                    group[column_name],
                    errors="coerce",
                )

                # D/E:
                # lower is better.
                if metric_name == "D/E":
                    percentile = (
                        1.0
                        - self._percent_rank(
                            values
                        )
                    )
                else:
                    percentile = (
                        self._percent_rank(
                            values
                        )
                    )

                for idx in group.index:

                    value = values.loc[idx]
                    rank = percentile.loc[idx]

                    output_rows.append(
                        {
                            "company_id": group.loc[
                                idx,
                                "company_id",
                            ],
                            "peer_group_name": peer_group_name,
                            "metric": metric_name,
                            "value": (
                                float(value)
                                if pd.notna(value)
                                else None
                            ),
                            "percentile_rank": (
                                float(rank)
                                if pd.notna(rank)
                                else None
                            ),
                            "year": (
                                int(
                                    group.loc[
                                        idx,
                                        "year",
                                    ]
                                )
                                if pd.notna(
                                    group.loc[
                                        idx,
                                        "year",
                                    ]
                                )
                                else None
                            ),
                        }
                    )

        result = pd.DataFrame(
            output_rows
        )

        return result

    # ============================================================
    # SQLITE
    # ============================================================

    def save_to_sqlite(
        self,
        percentile_df: pd.DataFrame,
    ) -> None:
        """Create/replace peer_percentiles table."""

        with sqlite3.connect(
            self.db_path
        ) as conn:

            conn.execute(
                """
                DROP TABLE IF EXISTS peer_percentiles
                """
            )

            percentile_df.to_sql(
                "peer_percentiles",
                conn,
                if_exists="replace",
                index=False,
            )

    # ============================================================
    # RUN
    # ============================================================

    def run(self) -> pd.DataFrame:
        """Run the complete Day 18 pipeline."""

        print(
            "Loading peer groups..."
        )

        peers = self.load_peer_groups()

        print(
            f"Peer assignments: {len(peers)}"
        )

        print(
            "Loading financial data..."
        )

        financial = (
            self.load_financial_data()
        )

        print(
            f"Financial rows: {len(financial)}"
        )

        print(
            "Computing percentile rankings..."
        )

        result = self.compute_percentiles(
            financial,
            peers,
        )

        print(
            f"Percentile rows: {len(result)}"
        )

        self.save_to_sqlite(
            result
        )

        print(
            "peer_percentiles table created."
        )

        return result


def main():
    engine = PeerPercentileEngine()

    result = engine.run()

    print("\nSample results:")
    print(
        result.head(20).to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()