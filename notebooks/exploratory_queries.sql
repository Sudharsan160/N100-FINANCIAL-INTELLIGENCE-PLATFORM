-- N100 Financial Intelligence Platform
-- Sprint 1 - Day 07
-- Exploratory Queries

-- 1. Total number of companies
SELECT COUNT(*) AS total_companies
FROM companies;


-- 2. Companies by sector
SELECT broad_sector, COUNT(*) AS company_count
FROM sectors
GROUP BY broad_sector
ORDER BY company_count DESC;


-- 3. P&L year coverage
SELECT
    MIN(year) AS first_year,
    MAX(year) AS last_year,
    COUNT(DISTINCT year) AS total_years
FROM profitandloss;


-- 4. Top 10 companies by latest net profit
SELECT
    company_id,
    year,
    net_profit
FROM profitandloss
WHERE year = (SELECT MAX(year) FROM profitandloss)
ORDER BY net_profit DESC
LIMIT 10;


-- 5. Top 10 companies by latest sales
SELECT
    company_id,
    year,
    sales
FROM profitandloss
WHERE year = (SELECT MAX(year) FROM profitandloss)
ORDER BY sales DESC
LIMIT 10;


-- 6. Companies with highest latest ROE
SELECT
    company_id,
    year,
    return_on_equity_pct
FROM financial_ratios
WHERE year = (SELECT MAX(year) FROM financial_ratios)
ORDER BY return_on_equity_pct DESC
LIMIT 10;


-- 7. Companies with highest latest market capitalization
SELECT
    company_id,
    year,
    market_cap_crore
FROM market_cap
WHERE year = (SELECT MAX(year) FROM market_cap)
ORDER BY market_cap_crore DESC
LIMIT 10;


-- 8. Average operating margin by sector
SELECT
    s.broad_sector,
    ROUND(AVG(p.opm_percentage), 2) AS avg_opm
FROM profitandloss p
JOIN sectors s
    ON p.company_id = s.company_id
GROUP BY s.broad_sector
ORDER BY avg_opm DESC;


-- 9. Companies with positive free cash flow
SELECT
    company_id,
    year,
    free_cash_flow_cr
FROM financial_ratios
WHERE free_cash_flow_cr > 0
  AND year = (SELECT MAX(year) FROM financial_ratios)
ORDER BY free_cash_flow_cr DESC
LIMIT 10;


-- 10. Stock price range by company
SELECT
    company_id,
    MIN(low_price) AS lowest_price,
    MAX(high_price) AS highest_price
FROM stock_prices
GROUP BY company_id
ORDER BY company_id;