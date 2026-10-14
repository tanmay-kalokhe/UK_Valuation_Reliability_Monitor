-- Inputs: ONS postcode lookup CSV; study_area (written from the config by db.py)
-- Output: stg_postcode_lookup, one row per study-area postcode, live or terminated
-- Assumptions: postcode_key is the postcode in upper case with spaces removed.
-- Terminated postcodes are kept because older sales and certificates still use them.

CREATE OR REPLACE TABLE stg_postcode_lookup AS
SELECT
    l.pcds AS postcode,
    l.oa21cd AS oa21_code,
    l.oac21desc AS area_classification,
    l.lsoa21cd AS lsoa21_code,
    l.msoa21cd AS msoa21_code,
    l.msoa21nm AS msoa21_name,
    l.ladcd AS lad_code,
    l.ladnm AS lad_name,
    UPPER(REPLACE(l.pcds, ' ', '')) AS postcode_key,
    SPLIT_PART(l.pcds, ' ', 1) AS postcode_district,
    COALESCE(l.doterm, '') <> '' AS is_terminated
FROM READ_CSV('${postcode_lookup_csv}', header = TRUE, all_varchar = TRUE) AS l
INNER JOIN study_area AS s ON l.ladcd = s.lad_code;
