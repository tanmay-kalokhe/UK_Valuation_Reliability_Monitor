-- Inputs: stg_price_paid, stg_epc
-- Output: match_sales (one row per Category A sale) and match_epc (one row per
--         certificate), each with normalised address fields
-- Assumptions:
--   * Only Category A (standard market) sales are matched (decision D-002).
--   * A property is identified by its UPRN; the 1.8% of certificates without one fall
--     back to postcode + normalised address.

CREATE OR REPLACE TABLE match_sales AS
WITH base AS (
    SELECT
        transaction_id,
        sale_date,
        price,
        property_type,
        tenure,
        is_new_build,
        lad_code,
        postcode_key,
        postcode_district,
        NORMALISE_ADDRESS(CONCAT_WS(' ', saon, paon, street)) AS address_norm,
        NORMALISE_ADDRESS(street) AS street_norm
    FROM stg_price_paid
    WHERE ppd_category = 'A'
)

SELECT
    *,
    ADDRESS_TOKENS(address_norm) AS address_tokens,
    ADDRESS_WORDS(address_norm) AS address_words
FROM base;

CREATE OR REPLACE TABLE match_epc AS
WITH base AS (
    SELECT
        certificate_number,
        uprn,
        postcode_key,
        lodgement_date,
        epc_property_type,
        transaction_type,
        NORMALISE_ADDRESS(CONCAT_WS(' ', address1, address2)) AS line_norm,
        NORMALISE_ADDRESS(CONCAT_WS(' ', address1, address2, address3)) AS full_norm
    FROM stg_epc
)

SELECT
    *,
    COALESCE(uprn, postcode_key || '|' || line_norm) AS property_key,
    ADDRESS_TOKENS(line_norm) AS address_tokens,
    ADDRESS_WORDS(line_norm) AS address_words
FROM base;
