-- Inputs: feat_sales, feat_epc
-- Output: feat_area_history, one row per sale with local price levels from earlier sales
-- Assumptions:
--   * Only sales completed in the ${history_window_months} months before the sale's
--     information cut-off are used (decision D-022), so nothing from the sale's own period
--     leaks in.
--   * Prices are deflated by the local-authority HPI for their type and month. UK HPI indices
--     share one base month, so deflated prices are comparable across types and months
--     ("constant prices").
--   * Price per m² uses matched sales only (floor area comes from the certificate).
--   * A level based on fewer than ${min_comparables} sales is left missing.
--   * Levels are computed once per area and sale month, then joined to the sales.

CREATE OR REPLACE TABLE feat_area_history AS
WITH comparables AS (
    SELECT
        s.area_key,
        s.msoa21_code,
        s.sale_date,
        s.price / s.hpi_sale_month AS deflated_price,
        s.price / s.hpi_sale_month / e.floor_area AS deflated_price_per_sqm
    FROM feat_sales AS s
    LEFT JOIN feat_epc AS e ON s.transaction_id = e.transaction_id
    WHERE s.hpi_sale_month IS NOT NULL
),

district_cells AS (
    SELECT DISTINCT
        area_key,
        sale_month,
        info_cutoff
    FROM feat_sales
),

msoa_cells AS (
    SELECT DISTINCT
        msoa21_code,
        sale_month,
        info_cutoff
    FROM feat_sales
    WHERE msoa21_code IS NOT NULL
),

district AS (
    SELECT
        c.area_key,
        c.sale_month,
        MEDIAN(p.deflated_price_per_sqm) AS district_price_per_sqm,
        COUNT(p.deflated_price_per_sqm) AS district_sqm_sales,
        COUNT(*) AS district_sales
    FROM district_cells AS c
    INNER JOIN comparables AS p
        ON
            c.area_key = p.area_key
            AND p.sale_date >= c.info_cutoff - INTERVAL ${history_window_months} MONTH
            AND c.info_cutoff > p.sale_date
    GROUP BY c.area_key, c.sale_month
),

msoa AS (
    SELECT
        c.msoa21_code,
        c.sale_month,
        MEDIAN(p.deflated_price) AS msoa_price,
        MEDIAN(p.deflated_price_per_sqm) AS msoa_price_per_sqm,
        COUNT(p.deflated_price_per_sqm) AS msoa_sqm_sales,
        COUNT(*) AS msoa_sales
    FROM msoa_cells AS c
    INNER JOIN comparables AS p
        ON
            c.msoa21_code = p.msoa21_code
            AND p.sale_date >= c.info_cutoff - INTERVAL ${history_window_months} MONTH
            AND c.info_cutoff > p.sale_date
    GROUP BY c.msoa21_code, c.sale_month
)

SELECT
    s.transaction_id,
    COALESCE(d.district_sales, 0) AS district_sales,
    COALESCE(m.msoa_sales, 0) AS msoa_sales,
    CASE
        WHEN d.district_sqm_sales >= ${min_comparables} THEN d.district_price_per_sqm
    END AS district_price_per_sqm,
    CASE WHEN m.msoa_sales >= ${min_comparables} THEN m.msoa_price END AS msoa_price,
    CASE
        WHEN m.msoa_sqm_sales >= ${min_comparables} THEN m.msoa_price_per_sqm
    END AS msoa_price_per_sqm
FROM feat_sales AS s
LEFT JOIN district AS d ON s.area_key = d.area_key AND s.sale_month = d.sale_month
LEFT JOIN msoa AS m ON s.msoa21_code = m.msoa21_code AND s.sale_month = m.sale_month;
