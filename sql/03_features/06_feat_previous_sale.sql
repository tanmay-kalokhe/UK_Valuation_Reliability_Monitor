-- Inputs: feat_sales, feat_epc
-- Output: feat_previous_sale, one row per matched sale whose property sold earlier (within
--         the downloaded history, from January 2020) before the sale's information cut-off
-- Assumptions:
--   * A property is identified by the property_key of its matched certificate (UPRN where
--     present), so only matched sales can have a previous sale.
--   * The previous sale must be completed before the information cut-off (decision D-022).
--   * previous_price_const is the previous price deflated by the HPI for its type and month,
--     in the same constant prices as feat_area_history.

CREATE OR REPLACE TABLE feat_previous_sale AS
WITH sales AS (
    SELECT
        s.transaction_id,
        e.property_key,
        s.sale_date,
        s.info_cutoff,
        s.price,
        s.price / s.hpi_sale_month AS deflated_price
    FROM feat_sales AS s
    INNER JOIN feat_epc AS e ON s.transaction_id = e.transaction_id
)

SELECT
    cur.transaction_id,
    prev.sale_date AS previous_sale_date,
    prev.price AS previous_price,
    prev.deflated_price AS previous_price_const,
    DATE_DIFF('day', prev.sale_date, cur.sale_date) / 365.25 AS years_since_previous_sale
FROM sales AS cur
INNER JOIN sales AS prev
    ON
        cur.property_key = prev.property_key
        AND cur.info_cutoff > prev.sale_date
        AND cur.transaction_id <> prev.transaction_id
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY cur.transaction_id ORDER BY prev.sale_date DESC, prev.transaction_id DESC
) = 1;
