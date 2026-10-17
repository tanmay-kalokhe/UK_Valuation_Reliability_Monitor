-- Inputs: link_sale_epc, match_property, stg_epc
-- Output: feat_epc, one row per matched sale with the attributes of its linked certificate
--         (the latest lodged on or before the sale, decision D-003)
-- Assumptions:
--   * Floor areas outside ${floor_area_min} to ${floor_area_max} m² are treated as missing;
--     habitable rooms outside 1 to 30 likewise.
--   * construction_year is the midpoint of the age band ("1930-1949" -> 1939), 1890 for
--     "before 1900", start + 3 for "YYYY onwards", or the year itself when one is given.
--   * floor_number: ground 0, basement -1, "1st" 1 and so on; "mid floor" and "top floor"
--     give no number (is_top_storey still records the top floor).
--   * main_fuel is grouped into mains gas, electricity, oil and other.

CREATE OR REPLACE TABLE feat_epc AS
SELECT
    l.transaction_id,
    l.certificate_number,
    p.property_key,
    e.current_energy_rating,
    e.epc_property_type,
    e.current_energy_efficiency,
    l.days_before_sale / 365.25 AS certificate_age_years,
    NULLIF(e.built_form, 'Not Recorded') AS built_form,
    e.flat_top_storey = 'Y' AS is_top_storey,
    e.mains_gas_flag = 'Y' AS has_mains_gas,
    e.transaction_type AS certificate_reason,
    CASE
        WHEN e.total_floor_area BETWEEN ${floor_area_min} AND ${floor_area_max}
            THEN e.total_floor_area
    END AS floor_area,
    CASE WHEN e.habitable_rooms BETWEEN 1 AND 30 THEN e.habitable_rooms END AS habitable_rooms,
    CASE
        WHEN REGEXP_MATCHES(e.construction_age_band, '\d{4}-\d{4}')
            THEN (
                CAST(REGEXP_EXTRACT(e.construction_age_band, '(\d{4})-(\d{4})', 1) AS INTEGER)
                + CAST(REGEXP_EXTRACT(e.construction_age_band, '(\d{4})-(\d{4})', 2) AS INTEGER)
            ) // 2
        WHEN REGEXP_MATCHES(LOWER(e.construction_age_band), 'before 1900|pre-1900') THEN 1890
        WHEN REGEXP_MATCHES(e.construction_age_band, '\d{4} onwards')
            THEN CAST(REGEXP_EXTRACT(e.construction_age_band, '(\d{4}) onwards', 1) AS INTEGER) + 3
        WHEN REGEXP_FULL_MATCH(TRIM(e.construction_age_band), '\d{4}')
            THEN CAST(TRIM(e.construction_age_band) AS INTEGER)
    END AS construction_year,
    CASE
        WHEN LOWER(e.floor_level) IN ('ground', 'ground floor') THEN 0
        WHEN LOWER(e.floor_level) LIKE 'basement%' THEN -1
        WHEN REGEXP_MATCHES(e.floor_level, '^-?\d+')
            THEN CAST(REGEXP_EXTRACT(e.floor_level, '^(-?\d+)', 1) AS INTEGER)
    END AS floor_number,
    CASE
        WHEN LOWER(e.main_fuel) LIKE '%mains gas%' THEN 'mains_gas'
        WHEN LOWER(e.main_fuel) LIKE '%electric%' THEN 'electricity'
        WHEN LOWER(e.main_fuel) LIKE '%oil%' THEN 'oil'
        WHEN e.main_fuel IS NOT NULL THEN 'other'
    END AS main_fuel_group,
    CASE WHEN e.extension_count BETWEEN 0 AND 10 THEN e.extension_count END AS extension_count,
    CASE WHEN e.open_fireplaces BETWEEN 0 AND 10 THEN e.open_fireplaces END AS open_fireplaces
FROM link_sale_epc AS l
INNER JOIN stg_epc AS e ON l.certificate_number = e.certificate_number
INNER JOIN match_property AS p ON l.transaction_id = p.transaction_id;
