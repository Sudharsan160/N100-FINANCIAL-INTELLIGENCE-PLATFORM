import math
import sqlite3
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"
OUTPUT_DIR = ROOT / "reports" / "sector"

PAGE_W, PAGE_H = A4

FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

WINDOWS_REGULAR = Path(r"C:\Windows\Fonts\arial.ttf")
WINDOWS_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")

if WINDOWS_REGULAR.exists() and WINDOWS_BOLD.exists():
    try:
        pdfmetrics.registerFont(TTFont("ArialEmbedded", str(WINDOWS_REGULAR)))
        pdfmetrics.registerFont(TTFont("ArialEmbedded-Bold", str(WINDOWS_BOLD)))
        FONT_REGULAR = "ArialEmbedded"
        FONT_BOLD = "ArialEmbedded-Bold"
        print("Using embedded Arial fonts.")
    except Exception as exc:  # noqa: BLE001
        print(f"Arial embedding failed: {exc}")
        print("Using Helvetica.")

NAVY = colors.HexColor("#0B1F3A")
LIGHT_NAVY = colors.HexColor("#17395C")
LIGHT_GREY = colors.HexColor("#F3F5F7")
MID_GREY = colors.HexColor("#6B7280")
DARK = colors.HexColor("#1F2937")
BORDER = colors.HexColor("#D6DADF")
WHITE = colors.white
GREY_BLUE = colors.HexColor("#7C8FA6")


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


def fmt(value, suffix=""):
    value = safe_float(value)
    if value is None:
        return "N/A"
    return f"{value:,.2f}{suffix}"


def draw_box(c, x, y, w, h, fill=WHITE):
    c.setFillColor(fill)
    c.setStrokeColor(BORDER)
    c.roundRect(x, y, w, h, 6, fill=1, stroke=1)


def draw_header(c, sector):
    c.setFillColor(NAVY)
    c.rect(0, PAGE_H - 90, PAGE_W, 90, fill=1, stroke=0)

    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 21)
    c.drawString(36, PAGE_H - 39, sector)

    c.setFont(FONT_REGULAR, 9)
    c.drawString(
        36,
        PAGE_H - 61,
        "Nifty 100 Sector Intelligence Report",
    )

    c.setFont(FONT_REGULAR, 8)
    c.drawRightString(
        PAGE_W - 36,
        PAGE_H - 61,
        "Latest available financial data",
    )


def section_title(c, text, x, y):
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 12)
    c.drawString(x, y, text)

    c.setStrokeColor(NAVY)
    c.line(x, y - 5, x + 90, y - 5)


def draw_kpi(c, x, y, w, h, label, value):
    draw_box(c, x, y, w, h)

    c.setFillColor(MID_GREY)
    c.setFont(FONT_BOLD, 7)
    c.drawString(x + 9, y + h - 16, label.upper())

    c.setFillColor(DARK)
    c.setFont(FONT_BOLD, 14)
    c.drawString(x + 9, y + 15, str(value))


def draw_horizontal_bars(
    c,
    x,
    y,
    w,
    h,
    labels,
    values,
):
    draw_box(c, x, y, w, h)

    valid = []

    for label, value in zip(labels, values):
        value = safe_float(value)
        if value is not None:
            valid.append((label, value))

    if not valid:
        c.setFillColor(MID_GREY)
        c.setFont(FONT_REGULAR, 9)
        c.drawCentredString(
            x + w / 2,
            y + h / 2,
            "Data unavailable",
        )
        return

    max_value = max(abs(v) for _, v in valid)

    if max_value == 0:
        max_value = 1

    bar_y = y + h - 35

    for label, value in valid[:8]:
        c.setFillColor(MID_GREY)
        c.setFont(FONT_REGULAR, 7)

        c.drawString(
            x + 10,
            bar_y,
            str(label)[:22],
        )

        bar_x = x + 115
        bar_w = w - 145

        c.setFillColor(LIGHT_GREY)
        c.rect(
            bar_x,
            bar_y - 2,
            bar_w,
            8,
            fill=1,
            stroke=0,
        )

        actual_w = abs(value) / max_value * bar_w

        c.setFillColor(LIGHT_NAVY)
        c.rect(
            bar_x,
            bar_y - 2,
            actual_w,
            8,
            fill=1,
            stroke=0,
        )

        c.setFillColor(DARK)
        c.setFont(FONT_BOLD, 7)

        c.drawString(
            bar_x + bar_w + 4,
            bar_y,
            fmt(value),
        )

        bar_y -= 20


def load_sector_data():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    try:
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
            """,
            conn,
        )

        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            """,
            conn,
        )

    finally:
        conn.close()

    return sectors, ratios, companies


def generate_sector_report(
    sector_name,
    sectors,
    ratios,
    companies,
):
    sector_companies = sectors[sectors["broad_sector"] == sector_name].copy()

    if sector_companies.empty:
        return None

    company_ids = sector_companies["company_id"].astype(str)

    sector_ratios = ratios[ratios["company_id"].astype(str).isin(company_ids)].copy()

    if sector_ratios.empty:
        return None

    sector_ratios["year"] = pd.to_numeric(
        sector_ratios["year"],
        errors="coerce",
    )

    sector_ratios = sector_ratios.dropna(subset=["year"])

    if sector_ratios.empty:
        return None

    latest_year = sector_ratios["year"].max()

    latest = sector_ratios[sector_ratios["year"] == latest_year].copy()

    company_lookup = companies.set_index("company_id")["company_name"].to_dict()

    median_roe = (
        latest["return_on_equity_pct"].median()
        if "return_on_equity_pct" in latest.columns
        else None
    )

    median_margin = (
        latest["net_profit_margin_pct"].median()
        if "net_profit_margin_pct" in latest.columns
        else None
    )

    median_de = (
        latest["debt_to_equity"].median()
        if "debt_to_equity" in latest.columns
        else None
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_name = (
        sector_name.replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
        .replace("&", "and")
    )

    output_file = OUTPUT_DIR / f"{safe_name}.pdf"

    c = canvas.Canvas(
        str(output_file),
        pagesize=A4,
        pageCompression=1,
    )

    c.setTitle(f"{sector_name} - Sector Intelligence")

    draw_header(
        c,
        sector_name,
    )

    # -----------------------------------------------------
    # KPI ROW
    # -----------------------------------------------------

    y = PAGE_H - 165
    gap = 8

    tile_w = (PAGE_W - 72 - gap * 3) / 4

    draw_kpi(
        c,
        36,
        y,
        tile_w,
        58,
        "Companies",
        len(sector_companies),
    )

    draw_kpi(
        c,
        36 + tile_w + gap,
        y,
        tile_w,
        58,
        "Median ROE",
        fmt(median_roe, "%"),
    )

    draw_kpi(
        c,
        36 + 2 * (tile_w + gap),
        y,
        tile_w,
        58,
        "Median Net Margin",
        fmt(median_margin, "%"),
    )

    draw_kpi(
        c,
        36 + 3 * (tile_w + gap),
        y,
        tile_w,
        58,
        "Median D/E",
        fmt(median_de, "x"),
    )

    # -----------------------------------------------------
    # TOP ROE
    # -----------------------------------------------------

    section_title(
        c,
        "Latest ROE by Company",
        36,
        PAGE_H - 205,
    )

    top_roe = (
        latest[
            [
                "company_id",
                "return_on_equity_pct",
            ]
        ]
        .dropna()
        .sort_values(
            "return_on_equity_pct",
            ascending=False,
        )
        .head(8)
    )

    draw_horizontal_bars(
        c,
        36,
        PAGE_H - 395,
        PAGE_W - 72,
        175,
        [
            company_lookup.get(
                cid,
                str(cid),
            )
            for cid in top_roe["company_id"]
        ],
        top_roe["return_on_equity_pct"].tolist(),
    )

    # -----------------------------------------------------
    # TOP NET MARGIN
    # -----------------------------------------------------

    section_title(
        c,
        "Latest Net Profit Margin by Company",
        36,
        PAGE_H - 420,
    )

    top_margin = (
        latest[
            [
                "company_id",
                "net_profit_margin_pct",
            ]
        ]
        .dropna()
        .sort_values(
            "net_profit_margin_pct",
            ascending=False,
        )
        .head(8)
    )

    draw_horizontal_bars(
        c,
        36,
        PAGE_H - 610,
        PAGE_W - 72,
        175,
        [
            company_lookup.get(
                cid,
                str(cid),
            )
            for cid in top_margin["company_id"]
        ],
        top_margin["net_profit_margin_pct"].tolist(),
    )

    # -----------------------------------------------------
    # SUB-SECTOR DISTRIBUTION
    # -----------------------------------------------------

    section_title(
        c,
        "Sub-Sector Distribution",
        36,
        PAGE_H - 635,
    )

    sub_counts = sector_companies["sub_sector"].fillna("Unclassified").value_counts()

    draw_horizontal_bars(
        c,
        36,
        38,
        PAGE_W - 72,
        170,
        sub_counts.index.tolist(),
        sub_counts.values.tolist(),
    )

    c.setFillColor(MID_GREY)
    c.setFont(FONT_REGULAR, 7)

    c.drawRightString(
        PAGE_W - 36,
        20,
        "Nifty 100 Financial Intelligence Platform",
    )

    c.showPage()
    c.save()

    return output_file


def main():
    (
        sectors,
        ratios,
        companies,
    ) = load_sector_data()

    unique_sectors = (
        sectors["broad_sector"].dropna().drop_duplicates().sort_values().tolist()
    )

    print(f"Sector count: {len(unique_sectors)}")

    generated = 0
    failed = 0

    for sector_name in unique_sectors:
        try:
            output = generate_sector_report(
                sector_name,
                sectors,
                ratios,
                companies,
            )

            if output is not None:
                generated += 1
                print(f"[OK] {sector_name}: {output.name}")
            else:
                failed += 1
                print(f"[SKIP] {sector_name}: insufficient data")

        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"[ERROR] {sector_name}: {exc}")

    print("\n=== SECTOR REPORT RESULT ===")
    print(f"Generated: {generated}")
    print(f"Failed/Skipped: {failed}")


if __name__ == "__main__":
    main()
