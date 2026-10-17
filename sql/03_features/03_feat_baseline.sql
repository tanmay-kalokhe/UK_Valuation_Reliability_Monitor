-- Inputs: feat_sales
-- Output: feat_baseline, one row per local authority + postcode district (area_key),
--         property type and sale month: the baseline estimate for sales in that cell
-- Assumptions (decision D-004, with the cut-off of D-022):
--   * Comparables are all Category A sales of the same type in the same area_key completed in
--     the ${history_window_months} months before the information cut-off. Each comparable's
--     price is indexed to the cut-off with the local-authority HPI for its type:
--     price x HPI(month before cut-off) / HPI(comparable's sale month).
--   * The baseline is the median indexed price. With fewer than ${min_comparables}
--     comparables in the district, the local-authority median for the type is used instead.
--   * Every sale in a cell shares one cut-off, so the estimate is computed once per cell.

CREATE OR REPLACE TABLE feat_baseline AS
WITH cells AS (
    SELECT DISTINCT
        lad_code,
        area_key,
        property_type,
        sale_month,
        info_cutoff,
        hpi_at_cutoff
    FROM feat_sales
),

comparables AS (
    SELECT
        lad_code,
        area_key,
        property_type,
        sale_date,
        price / hpi_sale_month AS deflated_price
    FROM feat_sales
    WHERE hpi_sale_month IS NOT NULL
),

district AS (
    SELECT
        c.area_key,
        c.property_type,
        c.sale_month,
        MEDIAN(p.deflated_price * c.hpi_at_cutoff) AS median_indexed,
        COUNT(*) AS n_comparables
    FROM cells AS c
    INNER JOIN comparables AS p
        ON
            c.area_key = p.area_key
            AND c.property_type = p.property_type
            AND p.sale_date >= c.info_cutoff - INTERVAL ${history_window_months} MONTH
            AND c.info_cutoff > p.sale_date
    GROUP BY c.area_key, c.property_type, c.sale_month
),

local_authority AS (
    SELECT
        c.lad_code,
        c.property_type,
        c.sale_month,
        MEDIAN(p.deflated_price * c.hpi_at_cutoff) AS median_indexed,
        COUNT(*) AS n_comparables
    FROM (
        SELECT DISTINCT
            lad_code,
            property_type,
            sale_month,
            info_cutoff,
            hpi_at_cutoff
        FROM cells
    ) AS c
    INNER JOIN comparables AS p
        ON
            c.lad_code = p.lad_code
            AND c.property_type = p.property_type
            AND p.sale_date >= c.info_cutoff - INTERVAL ${history_window_months} MONTH
            AND c.info_cutoff > p.sale_date
    GROUP BY c.lad_code, c.property_type, c.sale_month
)

SELECT
    c.area_key,
    c.property_type,
    c.sale_month,
    COALESCE(d.n_comparables, 0) AS district_comparables,
    CASE
        WHEN d.n_comparables >= ${min_comparables} THEN d.median_indexed
        ELSE la.median_indexed
    END AS baseline_estimate,
    CASE
        WHEN d.n_comparables >= ${min_comparables} THEN 'district'
        WHEN la.median_indexed IS NOT NULL THEN 'local_authority'
    END AS baseline_level
FROM cells AS c
LEFT JOIN district AS d
    ON
        c.area_key = d.area_key
        AND c.property_type = d.property_type
        AND c.sale_month = d.sale_month
LEFT JOIN local_authority AS la
    ON
        c.lad_code = la.lad_code
        AND c.property_type = la.property_type
        AND c.sale_month = la.sale_month;
