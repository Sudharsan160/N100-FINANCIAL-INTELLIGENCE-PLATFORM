import argparse
import math
import sqlite3
import textwrap
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "nifty100.db"
OUTPUT_DIR = ROOT / "reports" / "tearsheets"

PROS_CONS_FILE = ROOT / "output" / "pros_cons_generated.csv"
CASHFLOW_FILE = ROOT / "output" / "cashflow_intelligence.xlsx"
CAPITAL_FILE = ROOT / "output" / "capital_allocation.csv"


PAGE_W, PAGE_H = A4


# ---------------------------------------------------------
# FONT SETUP
# ---------------------------------------------------------

FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

WINDOWS_REGULAR = Path(r"C:\Windows\Fonts\arial.ttf")
WINDOWS_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")

if WINDOWS_REGULAR.exists() and WINDOWS_BOLD.exists():
    try:
        pdfmetrics.registerFont(
            TTFont(
                "ArialEmbedded",
                str(WINDOWS_REGULAR),
            )
        )

        pdfmetrics.registerFont(
            TTFont(
                "ArialEmbedded-Bold",
                str(WINDOWS_BOLD),
            )
        )

        FONT_REGULAR = "ArialEmbedded"
        FONT_BOLD = "ArialEmbedded-Bold"

        print("Using embedded Arial fonts.")

    except Exception as exc:  # noqa: BLE001
        print(f"Arial embedding failed: {exc}")
        print("Falling back to Helvetica.")


# ---------------------------------------------------------
# COLORS
# ---------------------------------------------------------

NAVY = colors.HexColor("#0B1F3A")
LIGHT_NAVY = colors.HexColor("#17395C")
LIGHT_GREY = colors.HexColor("#F3F5F7")
MID_GREY = colors.HexColor("#6B7280")
DARK = colors.HexColor("#1F2937")
GREEN = colors.HexColor("#166534")
RED = colors.HexColor("#991B1B")
BORDER = colors.HexColor("#D6DADF")
WHITE = colors.white
GREY_BLUE = colors.HexColor("#7C8FA6")


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------


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


def fmt_number(value, decimals=2):
    value = safe_float(value)

    if value is None:
        return "N/A"

    return f"{value:,.{decimals}f}"


def fmt_pct(value, decimals=2):
    value = safe_float(value)

    if value is None:
        return "N/A"

    return f"{value:,.{decimals}f}%"


def fmt_x(value, decimals=2):
    value = safe_float(value)

    if value is None:
        return "N/A"

    return f"{value:,.{decimals}f}x"


def fmt_year_label(value):
    value = safe_float(value)

    if value is None:
        return "N/A"

    return str(int(value))


# ---------------------------------------------------------
# TEXT
# ---------------------------------------------------------


def draw_wrapped_text(
    c,
    text,
    x,
    y,
    max_width,
    font=None,
    size=9,
    leading=12,
    color=DARK,
):
    if text is None:
        return y

    text = str(text).replace("\n", " ").strip()

    if not text:
        return y

    if font is None:
        font = FONT_REGULAR

    c.setFont(font, size)
    c.setFillColor(color)

    words = text.split()

    lines = []
    current = ""

    for word in words:
        candidate = word if not current else current + " " + word

        if (
            stringWidth(
                candidate,
                font,
                size,
            )
            <= max_width
        ):
            current = candidate
        else:
            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    for line in lines:
        c.drawString(x, y, line)
        y -= leading

    return y


# ---------------------------------------------------------
# BASIC DRAWING
# ---------------------------------------------------------


def draw_box(
    c,
    x,
    y,
    w,
    h,
    fill=WHITE,
    stroke=BORDER,
    radius=6,
):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)

    c.roundRect(
        x,
        y,
        w,
        h,
        radius,
        fill=1,
        stroke=1,
    )


def draw_header(
    c,
    company_name,
    ticker,
    sector,
    page_number,
):
    c.setFillColor(NAVY)

    c.rect(
        0,
        PAGE_H - 88,
        PAGE_W,
        88,
        fill=1,
        stroke=0,
    )

    c.setFillColor(WHITE)

    c.setFont(
        FONT_BOLD,
        21,
    )

    c.drawString(
        36,
        PAGE_H - 37,
        company_name,
    )

    c.setFont(
        FONT_BOLD,
        10,
    )

    c.drawString(
        36,
        PAGE_H - 57,
        ticker,
    )

    c.setFont(
        FONT_REGULAR,
        10,
    )

    c.drawString(
        36,
        PAGE_H - 73,
        sector or "Sector unavailable",
    )

    c.setFont(
        FONT_REGULAR,
        8,
    )

    c.drawRightString(
        PAGE_W - 36,
        PAGE_H - 57,
        f"Company Tearsheet | Page {page_number}/2",
    )


def section_title(c, text, x, y):
    c.setFillColor(NAVY)

    c.setFont(
        FONT_BOLD,
        12,
    )

    c.drawString(
        x,
        y,
        text,
    )

    c.setStrokeColor(NAVY)
    c.setLineWidth(1.2)

    c.line(
        x,
        y - 5,
        x + 85,
        y - 5,
    )


# ---------------------------------------------------------
# KPI TILE
# ---------------------------------------------------------


def draw_kpi_tile(
    c,
    x,
    y,
    w,
    h,
    label,
    value,
):
    draw_box(
        c,
        x,
        y,
        w,
        h,
        fill=LIGHT_GREY,
    )

    c.setFillColor(MID_GREY)

    c.setFont(
        FONT_BOLD,
        8,
    )

    c.drawString(
        x + 8,
        y + h - 15,
        label.upper(),
    )

    c.setFillColor(DARK)

    c.setFont(
        FONT_BOLD,
        15,
    )

    display = str(value)

    while (
        stringWidth(
            display,
            FONT_BOLD,
            15,
        )
        > w - 16
        and len(display) > 5
    ):
        display = display[:-1]

    c.drawString(
        x + 8,
        y + 14,
        display,
    )


# ---------------------------------------------------------
# BAR CHART
# ---------------------------------------------------------


def draw_bar_chart(
    c,
    x,
    y,
    w,
    h,
    labels,
    values_a,
    values_b,
    legend_a,
    legend_b,
):
    draw_box(
        c,
        x,
        y,
        w,
        h,
    )

    chart_left = x + 35
    chart_bottom = y + 28
    chart_w = w - 50
    chart_h = h - 55

    all_values = [
        safe_float(v)
        for v in list(values_a) + list(values_b)
        if safe_float(v) is not None
    ]

    if not all_values:
        c.setFillColor(MID_GREY)

        c.setFont(
            FONT_REGULAR,
            9,
        )

        c.drawCentredString(
            x + w / 2,
            y + h / 2,
            "Data unavailable",
        )

        return

    max_value = max(all_values)

    if max_value <= 0:
        max_value = 1

    max_value *= 1.15

    c.setStrokeColor(BORDER)

    c.line(
        chart_left,
        chart_bottom,
        chart_left,
        chart_bottom + chart_h,
    )

    c.line(
        chart_left,
        chart_bottom,
        chart_left + chart_w,
        chart_bottom,
    )

    n = len(labels)

    group_w = chart_w / max(n, 1)

    bar_w = min(
        12,
        group_w / 3,
    )

    for i, label in enumerate(labels):

        base_x = chart_left + i * group_w + group_w / 2

        a = safe_float(values_a[i])
        b = safe_float(values_b[i])

        if a is not None:
            ah = max(
                0,
                a / max_value * chart_h,
            )

            c.setFillColor(LIGHT_NAVY)

            c.rect(
                base_x - bar_w - 2,
                chart_bottom,
                bar_w,
                ah,
                fill=1,
                stroke=0,
            )

        if b is not None:
            bh = max(
                0,
                b / max_value * chart_h,
            )

            c.setFillColor(GREY_BLUE)

            c.rect(
                base_x + 2,
                chart_bottom,
                bar_w,
                bh,
                fill=1,
                stroke=0,
            )

        c.setFillColor(MID_GREY)

        c.setFont(
            FONT_REGULAR,
            6.5,
        )

        c.drawCentredString(
            base_x,
            chart_bottom - 10,
            fmt_year_label(label),
        )

    # Legend
    c.setFillColor(LIGHT_NAVY)

    c.rect(
        x + 12,
        y + h - 20,
        8,
        8,
        fill=1,
        stroke=0,
    )

    c.setFillColor(DARK)

    c.setFont(
        FONT_REGULAR,
        7,
    )

    c.drawString(
        x + 24,
        y + h - 19,
        legend_a,
    )

    c.setFillColor(GREY_BLUE)

    c.rect(
        x + 90,
        y + h - 20,
        8,
        8,
        fill=1,
        stroke=0,
    )

    c.setFillColor(DARK)

    c.drawString(
        x + 102,
        y + h - 19,
        legend_b,
    )


# ---------------------------------------------------------
# LINE CHART
# ---------------------------------------------------------


def draw_line_chart(
    c,
    x,
    y,
    w,
    h,
    labels,
    values_a,
    values_b,
    legend_a,
    legend_b,
):
    draw_box(
        c,
        x,
        y,
        w,
        h,
    )

    chart_left = x + 34
    chart_bottom = y + 30
    chart_w = w - 48
    chart_h = h - 55

    parsed_a = [safe_float(v) for v in values_a]

    parsed_b = [safe_float(v) for v in values_b]

    all_values = [v for v in parsed_a + parsed_b if v is not None and math.isfinite(v)]

    if not all_values:
        c.setFillColor(MID_GREY)

        c.setFont(
            FONT_REGULAR,
            9,
        )

        c.drawCentredString(
            x + w / 2,
            y + h / 2,
            "Data unavailable",
        )

        return

    low = min(
        0,
        min(all_values),
    )

    high = max(all_values)

    if high == low:
        high = low + 1

    pad = (high - low) * 0.1

    low -= pad
    high += pad

    def point(index, value):

        px = chart_left + (index / max(len(labels) - 1, 1)) * chart_w

        py = chart_bottom + ((value - low) / (high - low)) * chart_h

        return px, py

    c.setStrokeColor(BORDER)

    c.line(
        chart_left,
        chart_bottom,
        chart_left,
        chart_bottom + chart_h,
    )

    c.line(
        chart_left,
        chart_bottom,
        chart_left + chart_w,
        chart_bottom,
    )

    for values, stroke in [
        (parsed_a, LIGHT_NAVY),
        (parsed_b, GREY_BLUE),
    ]:

        previous = None

        c.setStrokeColor(stroke)
        c.setLineWidth(1.8)

        for i, value in enumerate(values):

            if value is None:
                previous = None
                continue

            px, py = point(
                i,
                value,
            )

            if previous is not None:
                c.line(
                    previous[0],
                    previous[1],
                    px,
                    py,
                )

            c.setFillColor(stroke)

            c.circle(
                px,
                py,
                2.2,
                fill=1,
                stroke=0,
            )

            previous = (
                px,
                py,
            )

    for i, label in enumerate(labels):

        px = chart_left + (i / max(len(labels) - 1, 1)) * chart_w

        c.setFillColor(MID_GREY)

        c.setFont(
            FONT_REGULAR,
            6.5,
        )

        c.drawCentredString(
            px,
            chart_bottom - 10,
            fmt_year_label(label),
        )

    # Legend
    c.setFillColor(LIGHT_NAVY)

    c.rect(
        x + 12,
        y + h - 20,
        8,
        8,
        fill=1,
        stroke=0,
    )

    c.setFillColor(DARK)

    c.setFont(
        FONT_REGULAR,
        7,
    )

    c.drawString(
        x + 24,
        y + h - 19,
        legend_a,
    )

    c.setFillColor(GREY_BLUE)

    c.rect(
        x + 90,
        y + h - 20,
        8,
        8,
        fill=1,
        stroke=0,
    )

    c.setFillColor(DARK)

    c.drawString(
        x + 102,
        y + h - 19,
        legend_b,
    )


# ---------------------------------------------------------
# BALANCE SHEET COMPOSITION
# ---------------------------------------------------------


def draw_horizontal_composition(
    c,
    x,
    y,
    w,
    h,
    labels,
    values,
):
    draw_box(
        c,
        x,
        y,
        w,
        h,
    )

    valid = []

    for label, value in zip(
        labels,
        values,
    ):
        value = safe_float(value)

        if value is not None and value > 0:
            valid.append(
                (
                    label,
                    value,
                )
            )

    total = sum(v for _, v in valid)

    if total <= 0:

        c.setFillColor(MID_GREY)

        c.setFont(
            FONT_REGULAR,
            9,
        )

        c.drawCentredString(
            x + w / 2,
            y + h / 2,
            "Data unavailable",
        )

        return

    bar_x = x + 18
    bar_y = y + h - 55
    bar_w = w - 36
    bar_h = 28

    segment_colors = [
        LIGHT_NAVY,
        colors.HexColor("#5C6F82"),
        colors.HexColor("#8798A9"),
        colors.HexColor("#AEB9C4"),
        colors.HexColor("#D2D8DE"),
    ]

    current_x = bar_x

    for i, (label, value) in enumerate(valid):

        seg_w = bar_w * value / total

        c.setFillColor(segment_colors[i % len(segment_colors)])

        c.rect(
            current_x,
            bar_y,
            seg_w,
            bar_h,
            fill=1,
            stroke=0,
        )

        current_x += seg_w

    text_y = bar_y - 17

    for i, (label, value) in enumerate(valid):

        c.setFillColor(segment_colors[i % len(segment_colors)])

        c.rect(
            x + 18,
            text_y - 2,
            7,
            7,
            fill=1,
            stroke=0,
        )

        c.setFillColor(DARK)

        c.setFont(
            FONT_REGULAR,
            7,
        )

        pct = value / total * 100

        c.drawString(
            x + 30,
            text_y,
            (f"{label}: " f"{fmt_number(value)} Cr " f"({pct:.1f}%)"),
        )

        text_y -= 13


# ---------------------------------------------------------
# CASH FLOW WATERFALL
# ---------------------------------------------------------


def draw_cashflow_waterfall(
    c,
    x,
    y,
    w,
    h,
    cfo,
    cfi,
    cff,
):
    draw_box(
        c,
        x,
        y,
        w,
        h,
    )

    values = [
        (
            "CFO",
            safe_float(cfo),
        ),
        (
            "CFI",
            safe_float(cfi),
        ),
        (
            "CFF",
            safe_float(cff),
        ),
    ]

    valid = [value for _, value in values if value is not None]

    if not valid:

        c.setFillColor(MID_GREY)

        c.setFont(
            FONT_REGULAR,
            9,
        )

        c.drawCentredString(
            x + w / 2,
            y + h / 2,
            "Data unavailable",
        )

        return

    max_abs = max(abs(value) for value in valid)

    if max_abs == 0:
        max_abs = 1

    chart_left = x + 30
    chart_bottom = y + 35
    chart_w = w - 55
    chart_h = h - 65

    zero_y = chart_bottom + chart_h / 2

    c.setStrokeColor(BORDER)

    c.line(
        chart_left,
        zero_y,
        chart_left + chart_w,
        zero_y,
    )

    step = chart_w / len(values)

    for i, (label, value) in enumerate(values):

        if value is None:
            continue

        bar_x = chart_left + i * step + step * 0.25

        bar_w = step * 0.5

        bar_h = abs(value) / max_abs * (chart_h / 2 - 5)

        if value >= 0:
            bar_y = zero_y
            c.setFillColor(GREEN)

        else:
            bar_y = zero_y - bar_h
            c.setFillColor(RED)

        c.rect(
            bar_x,
            bar_y,
            bar_w,
            bar_h,
            fill=1,
            stroke=0,
        )

        c.setFillColor(DARK)

        c.setFont(
            FONT_BOLD,
            7,
        )

        text_y = bar_y + bar_h + 5 if value >= 0 else bar_y - 10

        c.drawCentredString(
            bar_x + bar_w / 2,
            text_y,
            fmt_number(value),
        )

        c.setFont(
            FONT_REGULAR,
            7,
        )

        c.drawCentredString(
            bar_x + bar_w / 2,
            chart_bottom - 12,
            label,
        )


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------


def get_company_id(
    conn,
    ticker,
):
    query = """
        SELECT id, company_name
        FROM companies
        WHERE id = ?
           OR UPPER(company_name) = UPPER(?)
        LIMIT 1
    """

    row = conn.execute(
        query,
        (
            ticker,
            ticker,
        ),
    ).fetchone()

    if row is None:
        raise ValueError(f"Company not found: {ticker}")

    return (
        row[0],
        row[1],
    )


def load_company_data(ticker):

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    try:

        company_id, company_name = get_company_id(
            conn,
            ticker,
        )

        company = pd.read_sql_query(
            """
            SELECT *
            FROM companies
            WHERE id = ?
            """,
            conn,
            params=(company_id,),
        )

        ratios = pd.read_sql_query(
            """
            SELECT *
            FROM financial_ratios
            WHERE company_id = ?
            ORDER BY year
            """,
            conn,
            params=(company_id,),
        )

        pnl = pd.read_sql_query(
            """
            SELECT *
            FROM profitandloss
            WHERE company_id = ?
            ORDER BY year
            """,
            conn,
            params=(company_id,),
        )

        balance = pd.read_sql_query(
            """
            SELECT *
            FROM balancesheet
            WHERE company_id = ?
            ORDER BY year
            """,
            conn,
            params=(company_id,),
        )

        cashflow = pd.read_sql_query(
            """
            SELECT *
            FROM cashflow
            WHERE company_id = ?
            ORDER BY year
            """,
            conn,
            params=(company_id,),
        )

        sectors = pd.read_sql_query(
            """
            SELECT *
            FROM sectors
            WHERE company_id = ?
            LIMIT 1
            """,
            conn,
            params=(company_id,),
        )

    finally:
        conn.close()

    if not company.empty:
        company_row = company.iloc[0]

    else:
        company_row = pd.Series(dtype=object)

    sector = (
        str(sectors.iloc[0]["broad_sector"])
        if not sectors.empty
        else "Sector unavailable"
    )

    return {
        "company_id": company_id,
        "company_name": company_name,
        "sector": sector,
        "company": company_row,
        "ratios": ratios,
        "pnl": pnl,
        "balance": balance,
        "cashflow": cashflow,
    }


# ---------------------------------------------------------
# INPUT FILES
# ---------------------------------------------------------


def load_pros_cons(company_id):

    if not PROS_CONS_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(PROS_CONS_FILE)

    return df[df["company_id"].astype(str) == str(company_id)].copy()


def load_cashflow_intelligence(company_id):

    if not CASHFLOW_FILE.exists():
        return pd.Series(dtype=object)

    df = pd.read_excel(CASHFLOW_FILE)

    rows = df[df["company_id"].astype(str) == str(company_id)]

    if rows.empty:
        return pd.Series(dtype=object)

    return rows.iloc[0]


def load_latest_capital_allocation(company_id):

    if not CAPITAL_FILE.exists():
        return pd.Series(dtype=object)

    df = pd.read_csv(CAPITAL_FILE)

    df = df[df["company_id"].astype(str) == str(company_id)].copy()

    if df.empty:
        return pd.Series(dtype=object)

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    df = df.dropna(subset=["year"])

    if df.empty:
        return pd.Series(dtype=object)

    return df.sort_values("year").iloc[-1]


# ---------------------------------------------------------
# DATA HELPERS
# ---------------------------------------------------------


def get_latest_ratio(ratios):

    if ratios.empty:
        return pd.Series(dtype=object)

    temp = ratios.copy()

    temp["year"] = pd.to_numeric(
        temp["year"],
        errors="coerce",
    )

    temp = temp.dropna(subset=["year"])

    if temp.empty:
        return ratios.iloc[-1]

    return temp.sort_values("year").iloc[-1]


def get_latest_year(ratios):

    latest = get_latest_ratio(ratios)

    if latest.empty:
        return None

    return safe_float(latest.get("year"))


def get_revenue_cagr(ratios):

    if ratios.empty:
        return None

    col = "revenue_cagr_pct"

    if col in ratios.columns:

        valid = ratios[col].dropna()

        if not valid.empty:
            return safe_float(valid.iloc[-1])

    return None


# ---------------------------------------------------------
# PAGE 1
# ---------------------------------------------------------


def draw_page_one(
    c,
    data,
    pros_cons,
):
    company_name = data["company_name"]

    ticker = str(data["company_id"])

    sector = data["sector"]

    ratios = data["ratios"]

    pnl = data["pnl"]

    latest = get_latest_ratio(ratios)

    latest_year = get_latest_year(ratios)

    roe = latest.get("return_on_equity_pct")

    roce = latest.get("roce_pct")

    npm = latest.get("net_profit_margin_pct")

    debt_equity = latest.get("debt_to_equity")

    revenue_cagr = get_revenue_cagr(ratios)

    fcf = latest.get("free_cash_flow_cr")

    draw_header(
        c,
        company_name,
        ticker,
        sector,
        1,
    )

    c.setFillColor(MID_GREY)

    c.setFont(
        FONT_REGULAR,
        8,
    )

    c.drawRightString(
        PAGE_W - 36,
        PAGE_H - 103,
        (
            "Latest financial year: "
            + (fmt_year_label(latest_year) if latest_year is not None else "N/A")
        ),
    )

    # KPI tiles
    tile_y = PAGE_H - 170

    gap = 8

    tile_w = (PAGE_W - 72 - gap * 2) / 3

    tile_h = 54

    kpis = [
        (
            "ROE",
            fmt_pct(roe),
        ),
        (
            "ROCE",
            fmt_pct(roce),
        ),
        (
            "Net Margin",
            fmt_pct(npm),
        ),
        (
            "Debt / Equity",
            fmt_x(debt_equity),
        ),
        (
            "Revenue CAGR",
            fmt_pct(revenue_cagr),
        ),
        (
            "Free Cash Flow",
            f"{fmt_number(fcf, 0)} Cr",
        ),
    ]

    positions = [
        (
            36,
            tile_y,
        ),
        (
            36 + tile_w + gap,
            tile_y,
        ),
        (
            36 + 2 * (tile_w + gap),
            tile_y,
        ),
        (
            36,
            tile_y - tile_h - 8,
        ),
        (
            36 + tile_w + gap,
            tile_y - tile_h - 8,
        ),
        (
            36 + 2 * (tile_w + gap),
            tile_y - tile_h - 8,
        ),
    ]

    for (
        label,
        value,
    ), (
        x,
        y,
    ) in zip(
        kpis,
        positions,
    ):

        draw_kpi_tile(
            c,
            x,
            y,
            tile_w,
            tile_h,
            label,
            value,
        )

    # Revenue / Net Profit
    chart_y = PAGE_H - 425

    section_title(
        c,
        "Revenue and Net Profit Trend",
        36,
        chart_y + 12,
    )

    pnl_plot = pnl.copy()

    if not pnl_plot.empty:
        pnl_plot["year"] = pd.to_numeric(
            pnl_plot["year"],
            errors="coerce",
        )

        pnl_plot = pnl_plot.dropna(subset=["year"]).tail(8)

    draw_bar_chart(
        c,
        36,
        chart_y - 145,
        250,
        140,
        (pnl_plot["year"].tolist() if not pnl_plot.empty else []),
        (pnl_plot["sales"].tolist() if not pnl_plot.empty else []),
        (pnl_plot["net_profit"].tolist() if not pnl_plot.empty else []),
        "Revenue",
        "Net Profit",
    )

    # ROE / ROCE
    section_title(
        c,
        "ROE and ROCE Trend",
        307,
        chart_y + 12,
    )

    ratio_plot = ratios.copy()

    if not ratio_plot.empty:
        ratio_plot["year"] = pd.to_numeric(
            ratio_plot["year"],
            errors="coerce",
        )

        ratio_plot = ratio_plot.dropna(subset=["year"]).tail(8)

    draw_line_chart(
        c,
        307,
        chart_y - 145,
        PAGE_W - 343,
        140,
        (ratio_plot["year"].tolist() if not ratio_plot.empty else []),
        (
            ratio_plot["return_on_equity_pct"].tolist()
            if "return_on_equity_pct" in ratio_plot.columns
            else []
        ),
        (ratio_plot["roce_pct"].tolist() if "roce_pct" in ratio_plot.columns else []),
        "ROE %",
        "ROCE %",
    )

    # Snapshot
    info_y = 168

    section_title(
        c,
        "Company Snapshot",
        36,
        info_y + 10,
    )

    about = data["company"].get(
        "about_company",
        None,
    )

    y = draw_wrapped_text(
        c,
        (about if pd.notna(about) else "Company description unavailable."),
        36,
        info_y - 10,
        PAGE_W - 72,
        font=FONT_REGULAR,
        size=8.5,
        leading=11,
        color=DARK,
    )

    # Top positive insight
    if not pros_cons.empty:

        pros = pros_cons[
            pros_cons["type"].astype(str).str.lower() == "pro"
        ].sort_values(
            "confidence_pct",
            ascending=False,
        )

        if not pros.empty:

            top_pro = pros.iloc[0]

            c.setFillColor(GREEN)

            c.setFont(
                FONT_BOLD,
                8,
            )

            c.drawString(
                36,
                max(
                    50,
                    y - 5,
                ),
                "Top generated positive signal:",
            )

            draw_wrapped_text(
                c,
                top_pro["text"],
                36,
                max(
                    38,
                    y - 20,
                ),
                PAGE_W - 72,
                font=FONT_REGULAR,
                size=8,
                leading=10,
                color=DARK,
            )

    c.setFillColor(MID_GREY)

    c.setFont(
        FONT_REGULAR,
        7,
    )

    c.drawRightString(
        PAGE_W - 36,
        22,
        "Nifty 100 Financial Intelligence Platform",
    )

    c.showPage()


# ---------------------------------------------------------
# CAPITAL ALLOCATION BADGE
# ---------------------------------------------------------


def draw_pattern_badge(
    c,
    x,
    y,
    w,
    h,
    label,
):
    draw_box(
        c,
        x,
        y,
        w,
        h,
        fill=LIGHT_GREY,
        stroke=BORDER,
        radius=7,
    )

    c.setFillColor(NAVY)

    c.setFont(
        FONT_BOLD,
        8,
    )

    c.drawCentredString(
        x + w / 2,
        y + h - 16,
        "CAPITAL ALLOCATION",
    )

    wrapped = textwrap.wrap(
        str(label),
        width=27,
    )

    c.setFillColor(DARK)

    c.setFont(
        FONT_BOLD,
        11,
    )

    start_y = y + h / 2 + 5

    for line in wrapped[:3]:

        c.drawCentredString(
            x + w / 2,
            start_y,
            line,
        )

        start_y -= 13


# ---------------------------------------------------------
# BULLETS
# ---------------------------------------------------------


def draw_bullets(
    c,
    items,
    x,
    y,
    width,
    color,
):
    if not items:

        c.setFillColor(MID_GREY)

        c.setFont(
            FONT_REGULAR,
            8,
        )

        c.drawString(
            x,
            y,
            "No generated insights available.",
        )

        return y - 15

    for item in items:

        c.setFillColor(color)

        c.circle(
            x + 3,
            y + 3,
            2,
            fill=1,
            stroke=0,
        )

        y = draw_wrapped_text(
            c,
            item,
            x + 12,
            y,
            width - 12,
            font=FONT_REGULAR,
            size=8,
            leading=10,
            color=DARK,
        )

        y -= 4

    return y


# ---------------------------------------------------------
# PAGE 2
# ---------------------------------------------------------


def draw_page_two(
    c,
    data,
    pros_cons,
    intelligence,
    capital_latest,
):
    company_name = data["company_name"]

    ticker = str(data["company_id"])

    sector = data["sector"]

    balance = data["balance"]

    cashflow = data["cashflow"]

    draw_header(
        c,
        company_name,
        ticker,
        sector,
        2,
    )

    # Balance sheet
    section_title(
        c,
        "Balance Sheet Composition",
        36,
        PAGE_H - 112,
    )

    latest_balance = (
        balance.sort_values("year").iloc[-1]
        if not balance.empty
        else pd.Series(dtype=object)
    )

    balance_labels = [
        "Fixed Assets",
        "CWIP",
        "Investments",
        "Other Assets",
    ]

    balance_values = [
        latest_balance.get("fixed_assets"),
        latest_balance.get("cwip"),
        latest_balance.get("investments"),
        latest_balance.get("other_asset"),
    ]

    draw_horizontal_composition(
        c,
        36,
        PAGE_H - 270,
        250,
        145,
        balance_labels,
        balance_values,
    )

    # Cash flow
    section_title(
        c,
        "Cash Flow Waterfall",
        307,
        PAGE_H - 112,
    )

    latest_cf = (
        cashflow.sort_values("year").iloc[-1]
        if not cashflow.empty
        else pd.Series(dtype=object)
    )

    draw_cashflow_waterfall(
        c,
        307,
        PAGE_H - 270,
        PAGE_W - 343,
        145,
        latest_cf.get("operating_activity"),
        latest_cf.get("investing_activity"),
        latest_cf.get("financing_activity"),
    )

    # Pros / Cons
    section_title(
        c,
        "Generated Pros and Cons",
        36,
        PAGE_H - 296,
    )

    left_x = 36
    right_x = PAGE_W / 2 + 4

    column_w = PAGE_W / 2 - 48

    pros = []
    cons = []

    if not pros_cons.empty:

        pros_df = pros_cons[
            pros_cons["type"].astype(str).str.lower() == "pro"
        ].sort_values(
            "confidence_pct",
            ascending=False,
        )

        cons_df = pros_cons[
            pros_cons["type"].astype(str).str.lower() == "con"
        ].sort_values(
            "confidence_pct",
            ascending=False,
        )

        pros = [
            (f"{row['text']} " f"({fmt_pct(row['confidence_pct'])} confidence)")
            for _, row in pros_df.head(4).iterrows()
        ]

        cons = [
            (f"{row['text']} " f"({fmt_pct(row['confidence_pct'])} confidence)")
            for _, row in cons_df.head(4).iterrows()
        ]

    # Pros box
    draw_box(
        c,
        left_x,
        PAGE_H - 500,
        column_w,
        185,
        fill=WHITE,
    )

    c.setFillColor(GREEN)

    c.setFont(
        FONT_BOLD,
        10,
    )

    c.drawString(
        left_x + 12,
        PAGE_H - 332,
        "PROS",
    )

    draw_bullets(
        c,
        pros,
        left_x + 12,
        PAGE_H - 353,
        column_w - 24,
        GREEN,
    )

    # Cons box
    draw_box(
        c,
        right_x,
        PAGE_H - 500,
        column_w,
        185,
        fill=WHITE,
    )

    c.setFillColor(RED)

    c.setFont(
        FONT_BOLD,
        10,
    )

    c.drawString(
        right_x + 12,
        PAGE_H - 332,
        "CONS",
    )

    draw_bullets(
        c,
        cons,
        right_x + 12,
        PAGE_H - 353,
        column_w - 24,
        RED,
    )

    # Capital allocation
    section_title(
        c,
        "Capital Allocation Intelligence",
        36,
        PAGE_H - 530,
    )

    allocation_label = "Data Unavailable"

    if not intelligence.empty:

        allocation_label = intelligence.get(
            "capital_allocation",
            intelligence.get(
                "capital_allocation_label",
                "Data Unavailable",
            ),
        )

        if pd.isna(allocation_label):
            allocation_label = "Data Unavailable"

    if not capital_latest.empty:

        fallback = capital_latest.get(
            "pattern_label",
            None,
        )

        if pd.notna(fallback):
            allocation_label = fallback

    draw_pattern_badge(
        c,
        36,
        PAGE_H - 655,
        250,
        105,
        allocation_label,
    )

    # Intelligence panel
    draw_box(
        c,
        307,
        PAGE_H - 655,
        PAGE_W - 343,
        105,
        fill=LIGHT_GREY,
    )

    fields = [
        (
            "CFO Quality",
            (intelligence.get("cfo_quality_label") if not intelligence.empty else None),
        ),
        (
            "CapEx",
            (intelligence.get("capex_label") if not intelligence.empty else None),
        ),
        (
            "Distress",
            (intelligence.get("distress_flag") if not intelligence.empty else None),
        ),
        (
            "Deleveraging",
            (intelligence.get("deleveraging_flag") if not intelligence.empty else None),
        ),
    ]

    ix = 319
    iy = PAGE_H - 575

    for label, value in fields:

        c.setFillColor(MID_GREY)

        c.setFont(
            FONT_BOLD,
            7,
        )

        c.drawString(
            ix,
            iy,
            label.upper(),
        )

        c.setFillColor(DARK)

        c.setFont(
            FONT_BOLD,
            9,
        )

        display = "N/A" if value is None or pd.isna(value) else str(value)

        c.drawString(
            ix,
            iy - 13,
            display[:24],
        )

        ix += 67

    c.setFillColor(MID_GREY)

    c.setFont(
        FONT_REGULAR,
        7,
    )

    c.drawRightString(
        PAGE_W - 36,
        22,
        "Nifty 100 Financial Intelligence Platform",
    )

    c.showPage()


# ---------------------------------------------------------
# GENERATE ONE TEARSHEET
# ---------------------------------------------------------


def generate_tearsheet(ticker):

    data = load_company_data(ticker)

    pros_cons = load_pros_cons(data["company_id"])

    intelligence = load_cashflow_intelligence(data["company_id"])

    capital_latest = load_latest_capital_allocation(data["company_id"])

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_name = (
        str(data["company_id"]).replace("/", "_").replace("\\", "_").replace(" ", "_")
    )

    output_file = OUTPUT_DIR / f"{safe_name}.pdf"

    c = canvas.Canvas(
        str(output_file),
        pagesize=A4,
        pageCompression=1,
    )

    c.setTitle(f"{data['company_name']} " f"- Financial Tearsheet")

    draw_page_one(
        c,
        data,
        pros_cons,
    )

    draw_page_two(
        c,
        data,
        pros_cons,
        intelligence,
        capital_latest,
    )

    c.save()

    return output_file


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------


def main():

    parser = argparse.ArgumentParser(
        description=("Generate 2-page " "Nifty 100 company tearsheets.")
    )

    parser.add_argument(
        "--companies",
        nargs="+",
        help="Tickers/company IDs to generate.",
    )

    args = parser.parse_args()

    if args.companies:

        companies = args.companies

    else:

        companies = [
            "INDIGO",
            "TCS",
            "HDFCBANK",
            "ITC",
            "ONGC",
        ]

    print("Generating tearsheets...\n")

    for ticker in companies:

        try:

            output = generate_tearsheet(ticker)

            print(f"[OK] {ticker}: {output}")

        except Exception as exc:  # noqa: BLE001

            print(f"[ERROR] {ticker}: {exc}")

    print("\nDone.")


if __name__ == "__main__":
    main()
