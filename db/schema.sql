PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- ============================================================
-- 1. Companies
-- ============================================================

CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    company_logo TEXT,
    company_name TEXT NOT NULL,
    chart_link TEXT,
    about_company TEXT,
    website TEXT,
    nse_profile TEXT,
    bse_profile TEXT,
    face_value REAL,
    book_value REAL,
    roce_percentage REAL,
    roe_percentage REAL
);

-- ============================================================
-- 2. Profit & Loss
-- ============================================================

CREATE TABLE IF NOT EXISTS profitandloss (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
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
    dividend_payout REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ============================================================
-- 3. Balance Sheet
-- ============================================================

CREATE TABLE IF NOT EXISTS balancesheet (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
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
    total_assets REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ============================================================
-- 4. Cash Flow
-- ============================================================

CREATE TABLE IF NOT EXISTS cashflow (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    year INTEGER,
    operating_activity REAL,
    investing_activity REAL,
    financing_activity REAL,
    net_cash_flow REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ============================================================
-- 5. Analysis
-- ============================================================

CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    compounded_sales_growth TEXT,
    compounded_profit_growth TEXT,
    stock_price_cagr TEXT,
    roe TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ============================================================
-- 6. Documents
-- ============================================================

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    year INTEGER,
    annual_report TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ============================================================
-- 7. Pros & Cons
-- ============================================================

CREATE TABLE IF NOT EXISTS prosandcons (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    pros TEXT,
    cons TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ============================================================
-- 8. Sectors
-- ============================================================

CREATE TABLE IF NOT EXISTS sectors (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    broad_sector TEXT,
    sub_sector TEXT,
    index_weight_pct REAL,
    market_cap_category TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ============================================================
-- 9. Stock Prices
-- ============================================================

CREATE TABLE IF NOT EXISTS stock_prices (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    date TEXT,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume INTEGER,
    adjusted_close REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ============================================================
-- 10. Financial Ratios
-- ============================================================

CREATE TABLE IF NOT EXISTS financial_ratios (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    year INTEGER,
    net_profit_margin_pct REAL,
    operating_profit_margin_pct REAL,
    return_on_equity_pct REAL,
    debt_to_equity REAL,
    interest_coverage REAL,
    asset_turnover REAL,
    free_cash_flow_cr REAL,
    capex_cr REAL,
    earnings_per_share REAL,
    book_value_per_share REAL,
    dividend_payout_ratio_pct REAL,
    total_debt_cr REAL,
    cash_from_operations_cr REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ============================================================
-- 11. Market Cap
-- ============================================================

CREATE TABLE IF NOT EXISTS market_cap (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    year INTEGER,
    market_cap_crore REAL,
    enterprise_value_crore REAL,
    pe_ratio REAL,
    pb_ratio REAL,
    ev_ebitda REAL,
    dividend_yield_pct REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ============================================================
-- 12. Peer Groups
-- ============================================================

CREATE TABLE IF NOT EXISTS peer_groups (
    id INTEGER PRIMARY KEY,
    peer_group_name TEXT,
    company_id TEXT NOT NULL,
    is_benchmark INTEGER,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ============================================================
-- Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_profitandloss_company_year
    ON profitandloss(company_id, year);

CREATE INDEX IF NOT EXISTS idx_balancesheet_company_year
    ON balancesheet(company_id, year);

CREATE INDEX IF NOT EXISTS idx_cashflow_company_year
    ON cashflow(company_id, year);

CREATE INDEX IF NOT EXISTS idx_documents_company_year
    ON documents(company_id, year);

CREATE INDEX IF NOT EXISTS idx_financial_ratios_company_year
    ON financial_ratios(company_id, year);

CREATE INDEX IF NOT EXISTS idx_market_cap_company_year
    ON market_cap(company_id, year);

CREATE INDEX IF NOT EXISTS idx_stock_prices_company_date
    ON stock_prices(company_id, date);

CREATE INDEX IF NOT EXISTS idx_sectors_company
    ON sectors(company_id);

CREATE INDEX IF NOT EXISTS idx_peer_groups_company
    ON peer_groups(company_id);

COMMIT;