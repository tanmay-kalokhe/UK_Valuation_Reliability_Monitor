-- Inputs: Price Paid monthly update file (no header, 16 columns); study_area
-- Output: stg_price_paid_changes, the latest month's additions (A), changes (C) and
--         deletions (D) for the study area
-- Assumptions: used to measure how much the register is revised after publication;
--              the yearly files already include these corrections.

CREATE OR REPLACE TABLE stg_price_paid_changes AS
SELECT
    s.lad_code,
    r.property_type,
    r.ppd_category,
    r.record_status,
    TRIM(r.transaction_id, '{}') AS transaction_id,
    CAST(r.price AS BIGINT) AS price,
    CAST(STRPTIME(r.transfer_date, '%Y-%m-%d %H:%M') AS DATE) AS sale_date
FROM
    READ_CSV(
        '${raw_price_paid}/pp-monthly-update-new-version.csv',
        header = FALSE,
        all_varchar = TRUE,
        names = [
            'transaction_id', 'price', 'transfer_date', 'postcode', 'property_type',
            'new_build', 'tenure', 'paon', 'saon', 'street', 'locality', 'town_city',
            'district', 'county', 'ppd_category', 'record_status'
        ]
    ) AS r
INNER JOIN study_area AS s ON UPPER(r.district) = UPPER(s.lad_name);
