-- Inputs: match_sales, stg_postcode_lookup, feat_hpi
-- Output: feat_sales, one row per Category A sale with a postcode district (matched or not),
--         with its area codes, information cut-off and HPI values
-- Assumptions:
--   * Information cut-off (decision D-022): a valuation uses only sales completed before the
--     first day of (sale month - ${info_lag_months} months), and the HPI for the month before
--     that cut-off. This allows for the time between agreeing a price and completion, and
--     for Land Registry's registration lag.
--   * All Category A sales are kept here, matched or not: unmatched sales are still public
--     comparables for the baseline and the area features.

CREATE OR REPLACE TABLE feat_sales AS
WITH base AS (
    SELECT
        s.transaction_id,
        s.sale_date,
        s.price,
        s.property_type,
        s.tenure,
        s.is_new_build,
        s.lad_code,
        s.postcode_district,
        l.msoa21_code,
        l.area_classification,
        s.lad_code || '|' || s.postcode_district AS area_key,
        CAST(DATE_TRUNC('month', s.sale_date) AS DATE) AS sale_month,
        CAST(
            DATE_TRUNC('month', s.sale_date) - INTERVAL ${info_lag_months} MONTH AS DATE
        ) AS info_cutoff
    FROM match_sales AS s
    LEFT JOIN stg_postcode_lookup AS l ON s.postcode_key = l.postcode_key
    WHERE s.postcode_district IS NOT NULL
)

SELECT
    b.*,
    CAST(b.info_cutoff - INTERVAL 1 MONTH AS DATE) AS hpi_month,
    hs.hpi_index AS hpi_sale_month,
    hi.hpi_index AS hpi_at_cutoff
FROM base AS b
LEFT JOIN feat_hpi AS hs
    ON
        b.lad_code = hs.lad_code
        AND b.property_type = hs.property_type
        AND b.sale_month = hs.month_start
LEFT JOIN feat_hpi AS hi
    ON
        b.lad_code = hi.lad_code
        AND b.property_type = hi.property_type
        AND b.info_cutoff - INTERVAL 1 MONTH = hi.month_start;
