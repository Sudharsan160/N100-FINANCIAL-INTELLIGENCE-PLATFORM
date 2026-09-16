from pathlib import Path
import math
import sqlite3

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "nifty100.db"

CASHFLOW_FILE = (
    ROOT / "output" / "cashflow_intelligence.xlsx"
)

CAPITAL_FILE = (
    ROOT / "output" / "capital_allocation.csv"
)

OUTPUT_DIR = (
    ROOT / "reports" / "portfolio"
)

OUTPUT_FILE = (
    OUTPUT_DIR / "portfolio_summary.pdf"
)


PAGE_W, PAGE_H = A4


# =========================================================
# FONT SETUP
# =========================================================

FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

ARIAL = Path(r"C:\Windows\Fonts\arial.ttf")
ARIAL_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")

if ARIAL.exists() and ARIAL_BOLD.exists():
    try:
        pdfmetrics.registerFont(
            TTFont(
                "ArialEmbedded",
                str(ARIAL),
            )
        )

        pdfmetrics.registerFont(
            TTFont(
                "ArialEmbedded-Bold",
                str(ARIAL_BOLD),
            )
        )

        FONT_REGULAR = "ArialEmbedded"
        FONT_BOLD = "ArialEmbedded-Bold"

        print("Using embedded Arial fonts.")

    except Exception as exc:
        print(
            f"Arial embedding failed: {exc}"
        )
        print(
            "Using Helvetica."
        )


# =========================================================
# COLORS
# =========================================================

NAVY = colors.HexColor("#0B1F3A")
LIGHT_NAVY = colors.HexColor("#17395C")
LIGHT_GREY = colors.HexColor("#F3F5F7")
MID_GREY = colors.HexColor("#6B7280")
DARK = colors.HexColor("#1F2937")
GREEN = colors.HexColor("#166534")
RED = colors.HexColor("#991B1B")
AMBER = colors.HexColor("#92400E")
BORDER = colors.HexColor("#D6DADF")
WHITE = colors.white


# =========================================================
# HELPERS
# =========================================================

def safe_float(value):
    try:
        if value is None or pd.isna(value):
            return None

        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def fmt_number(value, decimals=1):
    value = safe_float(value)

    if value is None:
        return "N/A"

    return f"{value:,.{decimals}f}"


def fmt_pct(value, decimals=1):
    value = safe_float(value)

    if value is None:
        return "N/A"

    return f"{value:,.{decimals}f}%"


def fmt_x(value, decimals=2):
    value = safe_float(value)

    if value is None:
        return "N/A"

    return f"{value:,.{decimals}f}x"


def fmt_year(value):
    value = safe_float(value)

    if value is None:
        return "N/A"

    return str(int(value))


def trend_arrow(change):
    change = safe_float(change)

    if change is None:
        return "→"

    if change > 2:
        return "↑"

    if change < -2:
        return "↓"

    return "→"


def clean_text(value, fallback="N/A"):
    if value is None:
        return fallback

    try:
        if pd.isna(value):
            return fallback
    except Exception:
        pass

    text = str(value).strip()

    return text if text else fallback


# =========================================================
# DATA LOAD
# =========================================================

def load_data():

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(
        DB_PATH
    )

    try:

        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            ORDER BY id
            """,
            conn,
        )

        sectors = pd.read_sql_query(
            """
            SELECT
                company_id,
                broad_sector,
                sub_sector
            FROM sectors
            """,
            conn,
        )

        ratios = pd.read_sql_query(
            """
            SELECT *
            FROM financial_ratios
            ORDER BY company_id, year
            """,
            conn,
        )

    finally:
        conn.close()

    if CASHFLOW_FILE.exists():

        cashflow = pd.read_excel(
            CASHFLOW_FILE
        )

    else:

        cashflow = pd.DataFrame()

    if CAPITAL_FILE.exists():

        capital = pd.read_csv(
            CAPITAL_FILE
        )

    else:

        capital = pd.DataFrame()

    return (
        companies,
        sectors,
        ratios,
        cashflow,
        capital,
    )


# =========================================================
# BUILD ONE COMPANY SUMMARY
# =========================================================

def build_company_summaries(
    companies,
    sectors,
    ratios,
    cashflow,
    capital,
):

    sector_map = (
        sectors
        .drop_duplicates(
            "company_id"
        )
        .set_index(
            "company_id"
        )["broad_sector"]
        .to_dict()
    )

    subsection_map = (
        sectors
        .drop_duplicates(
            "company_id"
        )
        .set_index(
            "company_id"
        )["sub_sector"]
        .to_dict()
    )

    summaries = []

    for _, company in companies.iterrows():

        company_id = company[
            "company_id"
        ]

        group = ratios[
            ratios["company_id"]
            .astype(str)
            == str(company_id)
        ].copy()

        if not group.empty:

            group["year"] = pd.to_numeric(
                group["year"],
                errors="coerce",
            )

            group = group.dropna(
                subset=["year"]
            )

            group = group.sort_values(
                "year"
            )

        if group.empty:

            latest = pd.Series(
                dtype=object
            )

            previous = pd.Series(
                dtype=object
            )

        else:

            latest = group.iloc[-1]

            previous = (
                group.iloc[-2]
                if len(group) >= 2
                else pd.Series(
                    dtype=object
                )
            )

        latest_roe = safe_float(
            latest.get(
                "return_on_equity_pct"
            )
        )

        previous_roe = safe_float(
            previous.get(
                "return_on_equity_pct"
            )
        )

        roe_change = None

        if (
            latest_roe is not None
            and previous_roe is not None
        ):
            roe_change = (
                latest_roe
                - previous_roe
            )

        latest_npm = safe_float(
            latest.get(
                "net_profit_margin_pct"
            )
        )

        previous_npm = safe_float(
            previous.get(
                "net_profit_margin_pct"
            )
        )

        npm_change = None

        if (
            latest_npm is not None
            and previous_npm is not None
        ):
            npm_change = (
                latest_npm
                - previous_npm
            )

        latest_de = safe_float(
            latest.get(
                "debt_to_equity"
            )
        )

        previous_de = safe_float(
            previous.get(
                "debt_to_equity"
            )
        )

        de_change = None

        if (
            latest_de is not None
            and previous_de is not None
        ):
            de_change = (
                latest_de
                - previous_de
            )

        # -------------------------------------------------
        # Cash-flow intelligence
        # -------------------------------------------------

        if not cashflow.empty:

            cf_rows = cashflow[
                cashflow["company_id"]
                .astype(str)
                == str(company_id)
            ]

        else:

            cf_rows = pd.DataFrame()

        if cf_rows.empty:

            cf = {}

        else:

            cf = cf_rows.iloc[
                0
            ].to_dict()

        # -------------------------------------------------
        # Capital allocation
        # -------------------------------------------------

        if not capital.empty:

            ca_rows = capital[
                capital["company_id"]
                .astype(str)
                == str(company_id)
            ].copy()

        else:

            ca_rows = pd.DataFrame()

        if not ca_rows.empty:

            ca_rows["year"] = pd.to_numeric(
                ca_rows["year"],
                errors="coerce",
            )

            ca_rows = ca_rows.dropna(
                subset=["year"]
            )

        if ca_rows.empty:

            ca = {}

        else:

            ca = (
                ca_rows
                .sort_values("year")
                .iloc[-1]
                .to_dict()
            )

        allocation = cf.get(
            "capital_allocation",
            None,
        )

        if allocation is None:
            allocation = ca.get(
                "pattern_label",
                "N/A",
            )

        if pd.isna(allocation):
            allocation = "N/A"

        summaries.append(
            {
                "company_id": company_id,

                "company_name": company[
                    "company_name"
                ],

                "sector": sector_map.get(
                    company_id,
                    "Unknown",
                ),

                "sub_sector": subsection_map.get(
                    company_id,
                    "Unknown",
                ),

                "year": safe_float(
                    latest.get("year")
                ),

                "roe": latest_roe,

                "roe_arrow": trend_arrow(
                    roe_change
                ),

                "npm": latest_npm,

                "npm_arrow": trend_arrow(
                    npm_change
                ),

                "de": latest_de,

                "de_arrow": trend_arrow(
                    -de_change
                    if de_change is not None
                    else None
                ),

                "revenue_cagr": safe_float(
                    latest.get(
                        "revenue_cagr_pct"
                    )
                ),

                "profit_cagr": safe_float(
                    latest.get(
                        "net_profit_growth_pct"
                    )
                ),

                "fcf": safe_float(
                    latest.get(
                        "free_cash_flow_cr"
                    )
                ),

                "cfo_quality": clean_text(
                    cf.get(
                        "cfo_quality_label"
                    )
                ),

                "capex": clean_text(
                    cf.get(
                        "capex_label"
                    )
                ),

                "distress": clean_text(
                    cf.get(
                        "distress_flag"
                    )
                ),

                "deleveraging": clean_text(
                    cf.get(
                        "deleveraging_flag"
                    )
                ),

                "capital_allocation": clean_text(
                    allocation
                ),
            }
        )

    return pd.DataFrame(
        summaries
    )


# =========================================================
# PDF DRAWING
# =========================================================

def draw_header(
    c,
    company_name,
    ticker,
    sector,
):
    c.setFillColor(
        NAVY
    )

    c.rect(
        0,
        PAGE_H - 100,
        PAGE_W,
        100,
        fill=1,
        stroke=0,
    )

    c.setFillColor(
        WHITE
    )

    c.setFont(
        FONT_BOLD,
        23,
    )

    c.drawString(
        36,
        PAGE_H - 40,
        clean_text(
            company_name,
            ticker,
        ),
    )

    c.setFont(
        FONT_BOLD,
        10,
    )

    c.drawString(
        36,
        PAGE_H - 60,
        ticker,
    )

    c.setFont(
        FONT_REGULAR,
        10,
    )

    c.drawString(
        36,
        PAGE_H - 77,
        sector,
    )

    c.setFont(
        FONT_REGULAR,
        8,
    )

    c.drawRightString(
        PAGE_W - 36,
        PAGE_H - 60,
        "Portfolio Summary",
    )


def draw_info_box(
    c,
    x,
    y,
    w,
    h,
    label,
    value,
):
    c.setFillColor(
        LIGHT_GREY
    )

    c.setStrokeColor(
        BORDER
    )

    c.roundRect(
        x,
        y,
        w,
        h,
        6,
        fill=1,
        stroke=1,
    )

    c.setFillColor(
        MID_GREY
    )

    c.setFont(
        FONT_BOLD,
        7,
    )

    c.drawString(
        x + 9,
        y + h - 17,
        label.upper(),
    )

    c.setFillColor(
        DARK
    )

    c.setFont(
        FONT_BOLD,
        13,
    )

    value_text = clean_text(
        value
    )

    if len(value_text) > 20:
        value_text = value_text[:20]

    c.drawString(
        x + 9,
        y + 12,
        value_text,
    )


def draw_metric_row(
    c,
    y,
    label,
    current,
    trend,
):
    c.setFillColor(
        MID_GREY
    )

    c.setFont(
        FONT_BOLD,
        8,
    )

    c.drawString(
        48,
        y,
        label,
    )

    c.setFillColor(
        DARK
    )

    c.setFont(
        FONT_BOLD,
        11,
    )

    c.drawRightString(
        220,
        y,
        current,
    )

    c.setFont(
        FONT_BOLD,
        12,
    )

    if trend == "↑":
        c.setFillColor(
            GREEN
        )
    elif trend == "↓":
        c.setFillColor(
            RED
        )
    else:
        c.setFillColor(
            MID_GREY
        )

    c.drawString(
        235,
        y,
        trend,
    )


def draw_section(
    c,
    title,
    x,
    y,
    width,
):
    c.setFillColor(
        NAVY
    )

    c.setFont(
        FONT_BOLD,
        12,
    )

    c.drawString(
        x,
        y,
        title,
    )

    c.setStrokeColor(
        NAVY
    )

    c.line(
        x,
        y - 5,
        x + width,
        y - 5,
    )


def draw_capital_badge(
    c,
    x,
    y,
    w,
    h,
    label,
):
    c.setFillColor(
        LIGHT_NAVY
    )

    c.setStrokeColor(
        LIGHT_NAVY
    )

    c.roundRect(
        x,
        y,
        w,
        h,
        8,
        fill=1,
        stroke=1,
    )

    c.setFillColor(
        WHITE
    )

    c.setFont(
        FONT_BOLD,
        8,
    )

    c.drawCentredString(
        x + w / 2,
        y + h - 17,
        "CAPITAL ALLOCATION",
    )

    text = clean_text(
        label
    )

    if len(text) > 30:
        text = text[:30]

    words = text.split()

    lines = []
    current = ""

    for word in words:

        candidate = (
            word
            if not current
            else current + " " + word
        )

        if len(candidate) <= 25:
            current = candidate
        else:

            if current:
                lines.append(
                    current
                )

            current = word

    if current:
        lines.append(
            current
        )

    c.setFont(
        FONT_BOLD,
        10,
    )

    start_y = (
        y + h / 2 + 4
    )

    for line in lines[:3]:

        c.drawCentredString(
            x + w / 2,
            start_y,
            line,
        )

        start_y -= 13


def draw_footer(
    c,
    page_number,
    total_pages,
):
    c.setFillColor(
        MID_GREY
    )

    c.setFont(
        FONT_REGULAR,
        7,
    )

    c.drawString(
        36,
        20,
        "Nifty 100 Financial Intelligence Platform",
    )

    c.drawRightString(
        PAGE_W - 36,
        20,
        f"{page_number}/{total_pages}",
    )


# =========================================================
# ONE COMPANY PAGE
# =========================================================

def draw_company_page(
    c,
    row,
    page_number,
    total_pages,
):
    company_name = clean_text(
        row.get(
            "company_name"
        )
    )

    ticker = clean_text(
        row.get(
            "company_id"
        )
    )

    sector = clean_text(
        row.get(
            "sector"
        ),
        "Unknown",
    )

    draw_header(
        c,
        company_name,
        ticker,
        sector,
    )

    # -----------------------------------------------------
    # Latest year
    # -----------------------------------------------------

    latest_year = fmt_year(
        row.get(
            "year"
        )
    )

    c.setFillColor(
        MID_GREY
    )

    c.setFont(
        FONT_REGULAR,
        8,
    )

    c.drawRightString(
        PAGE_W - 36,
        PAGE_H - 118,
        f"Latest financial year: {latest_year}",
    )

    # -----------------------------------------------------
    # KPI tiles
    # -----------------------------------------------------

    tile_y = PAGE_H - 195

    gap = 8

    tile_w = (
        PAGE_W - 72 - 3 * gap
    ) / 4

    draw_info_box(
        c,
        36,
        tile_y,
        tile_w,
        58,
        "ROE",
        fmt_pct(
            row.get("roe")
        ),
    )

    draw_info_box(
        c,
        36 + tile_w + gap,
        tile_y,
        tile_w,
        58,
        "Net Margin",
        fmt_pct(
            row.get("npm")
        ),
    )

    draw_info_box(
        c,
        36 + 2 * (tile_w + gap),
        tile_y,
        tile_w,
        58,
        "Debt / Equity",
        fmt_x(
            row.get("de")
        ),
    )

    draw_info_box(
        c,
        36 + 3 * (tile_w + gap),
        tile_y,
        tile_w,
        58,
        "Revenue CAGR",
        fmt_pct(
            row.get("revenue_cagr")
        ),
    )

    # -----------------------------------------------------
    # Trend section
    # -----------------------------------------------------

    draw_section(
        c,
        "Key Trend Indicators",
        36,
        PAGE_H - 225,
        190,
    )

    trend_y = PAGE_H - 255

    draw_metric_row(
        c,
        trend_y,
        "ROE",
        fmt_pct(
            row.get("roe")
        ),
        clean_text(
            row.get(
                "roe_arrow"
            ),
            "→",
        ),
    )

    draw_metric_row(
        c,
        trend_y - 28,
        "Net Margin",
        fmt_pct(
            row.get("npm")
        ),
        clean_text(
            row.get(
                "npm_arrow"
            ),
            "→",
        ),
    )

    draw_metric_row(
        c,
        trend_y - 56,
        "Debt / Equity",
        fmt_x(
            row.get("de")
        ),
        clean_text(
            row.get(
                "de_arrow"
            ),
            "→",
        ),
    )

    # -----------------------------------------------------
    # Growth / cashflow panel
    # -----------------------------------------------------

    panel_x = 320
    panel_y = PAGE_H - 345
    panel_w = PAGE_W - 356
    panel_h = 135

    c.setFillColor(
        LIGHT_GREY
    )

    c.setStrokeColor(
        BORDER
    )

    c.roundRect(
        panel_x,
        panel_y,
        panel_w,
        panel_h,
        7,
        fill=1,
        stroke=1,
    )

    c.setFillColor(
        NAVY
    )

    c.setFont(
        FONT_BOLD,
        11,
    )

    c.drawString(
        panel_x + 12,
        panel_y + panel_h - 22,
        "Growth & Cash Flow",
    )

    metrics = [
        (
            "Profit Growth",
            fmt_pct(
                row.get(
                    "profit_cagr"
                )
            ),
        ),
        (
            "Free Cash Flow",
            f"{fmt_number(row.get('fcf'), 0)} Cr",
        ),
        (
            "CFO Quality",
            clean_text(
                row.get(
                    "cfo_quality"
                )
            ),
        ),
        (
            "CapEx",
            clean_text(
                row.get(
                    "capex"
                )
            ),
        ),
    ]

    yy = panel_y + panel_h - 44

    for label, value in metrics:

        c.setFillColor(
            MID_GREY
        )

        c.setFont(
            FONT_BOLD,
            7,
        )

        c.drawString(
            panel_x + 12,
            yy,
            label.upper(),
        )

        c.setFillColor(
            DARK
        )

        c.setFont(
            FONT_BOLD,
            9,
        )

        c.drawString(
            panel_x + 12,
            yy - 13,
            value[:24],
        )

        yy -= 27

    # -----------------------------------------------------
    # Intelligence
    # -----------------------------------------------------

    draw_section(
        c,
        "Financial Intelligence",
        36,
        PAGE_H - 390,
        170,
    )

    intelligence_y = PAGE_H - 425

    fields = [
        (
            "Distress Flag",
            clean_text(
                row.get(
                    "distress"
                )
            ),
        ),
        (
            "Deleveraging",
            clean_text(
                row.get(
                    "deleveraging"
                )
            ),
        ),
        (
            "Sub-Sector",
            clean_text(
                row.get(
                    "sub_sector"
                )
            ),
        ),
    ]

    for label, value in fields:

        c.setFillColor(
            MID_GREY
        )

        c.setFont(
            FONT_BOLD,
            8,
        )

        c.drawString(
            48,
            intelligence_y,
            label,
        )

        c.setFillColor(
            DARK
        )

        c.setFont(
            FONT_REGULAR,
            8,
        )

        text = value[:55]

        c.drawString(
            160,
            intelligence_y,
            text,
        )

        intelligence_y -= 25

    # -----------------------------------------------------
    # Capital allocation
    # -----------------------------------------------------

    draw_section(
        c,
        "Capital Allocation Pattern",
        36,
        PAGE_H - 510,
        210,
    )

    draw_capital_badge(
        c,
        36,
        PAGE_H - 625,
        245,
        92,
        clean_text(
            row.get(
                "capital_allocation"
            )
        ),
    )

    # -----------------------------------------------------
    # Portfolio interpretation
    # -----------------------------------------------------

    draw_section(
        c,
        "Portfolio Snapshot",
        310,
        PAGE_H - 510,
        PAGE_W - 346,
    )

    c.setFillColor(
        DARK
    )

    c.setFont(
        FONT_REGULAR,
        8.5,
    )

    y = PAGE_H - 540

    narrative = (
        f"{ticker} belongs to the {sector} sector. "
        f"The latest available financial year is {latest_year}. "
        f"ROE is {fmt_pct(row.get('roe'))}, "
        f"net margin is {fmt_pct(row.get('npm'))}, "
        f"and debt-to-equity is {fmt_x(row.get('de'))}. "
        f"Revenue CAGR is {fmt_pct(row.get('revenue_cagr'))}."
    )

    words = narrative.split()

    line = ""

    for word in words:

        candidate = (
            word
            if not line
            else line + " " + word
        )

        # Approximate wrapping for the panel.
        if len(candidate) <= 58:
            line = candidate

        else:

            c.drawString(
                310,
                y,
                line,
            )

            y -= 13

            line = word

    if line:
        c.drawString(
            310,
            y,
            line,
        )

    # -----------------------------------------------------
    # Footer
    # -----------------------------------------------------

    draw_footer(
        c,
        page_number,
        total_pages,
    )

    c.showPage()


# =========================================================
# MAIN
# =========================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        companies,
        sectors,
        ratios,
        cashflow,
        capital,
    ) = load_data()

    summary = build_company_summaries(
        companies,
        sectors,
        ratios,
        cashflow,
        capital,
    )

    total_companies = len(
        summary
    )

    print(
        f"Companies loaded: {total_companies}"
    )

    if total_companies != 92:
        raise ValueError(
            f"Expected 92 companies, "
            f"found {total_companies}"
        )

    c = canvas.Canvas(
        str(OUTPUT_FILE),
        pagesize=A4,
        pageCompression=1,
    )

    c.setTitle(
        "Nifty 100 Portfolio Summary"
    )

    for index, (_, row) in enumerate(
        summary.iterrows(),
        start=1,
    ):

        draw_company_page(
            c,
            row,
            index,
            total_companies,
        )

    c.save()

    print(
        f"Portfolio summary saved: "
        f"{OUTPUT_FILE}"
    )

    print(
        f"PDF pages: {total_companies}"
    )


if __name__ == "__main__":
    main()