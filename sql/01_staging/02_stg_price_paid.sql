-- Inputs: Price Paid yearly files (no header, 16 columns); study_area
-- Output: stg_price_paid, one row per study-area sale (all categories), typed
-- Assumptions:
--   * The yearly files are re-issued monthly with corrections applied, so they are the
--     current state of the register. The monthly change file is staged separately.
--   * The study area is assigned from Land Registry's own district field; the ONS
--     postcode lookup is used later as a cross-check.

CREATE OR REPLACE TABLE stg_price_paid AS
WITH raw AS (
    SELECT *
    FROM READ_CSV(
        '${raw_price_paid}/pp-20[0-9][0-9].csv',
        header = FALSE,
        all_varchar = TRUE,
        names = [
            'transaction_id', 'price', 'transfer_date', 'postcode', 'property_type',
            'new_build', 'tenure', 'paon', 'saon', 'street', 'locality', 'town_city',
            'district', 'county', 'ppd_category', 'record_status'
        ]
    )
)

SELECT
    s.lad_code,
    r.property_type,
    r.tenure,
    r.town_city,
    r.district,
    r.county,
    r.ppd_category,
    r.record_status,
    TRIM(r.transaction_id, '{}') AS transaction_id,
    CAST(r.price AS BIGINT) AS price,
    CAST(STRPTIME(r.transfer_date, '%Y-%m-%d %H:%M') AS DATE) AS sale_date,
    NULLIF(TRIM(r.postcode), '') AS postcode,
    NULLIF(UPPER(REPLACE(r.postcode, ' ', '')), '') AS postcode_key,
    NULLIF(SPLIT_PART(TRIM(r.postcode), ' ', 1), '') AS postcode_district,
    r.new_build = 'Y' AS is_new_build,
    NULLIF(r.paon, '') AS paon,
    NULLIF(r.saon, '') AS saon,
    NULLIF(r.street, '') AS street,
    NULLIF(r.locality, '') AS locality
FROM raw AS r
INNER JOIN study_area AS s ON UPPER(r.district) = UPPER(s.lad_name);
