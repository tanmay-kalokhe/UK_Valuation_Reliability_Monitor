-- Inputs: study-area EPC certificates (Parquet, all text) from ingest.extract_epc_study_area
-- Output: stg_epc, one row per certificate, typed, with the columns the project uses
-- Assumptions: transaction_type is lower-cased and trimmed because the source mixes
--              capitalisation (e.g. 'Marketed sale' and 'marketed sale').

CREATE OR REPLACE TABLE stg_epc AS
SELECT
    certificate_number,
    postcode,
    address1,
    address2,
    address3,
    property_type AS epc_property_type,
    built_form,
    current_energy_rating,
    potential_energy_rating,
    construction_age_band,
    tenure AS epc_tenure,
    main_fuel,
    mains_gas_flag,
    floor_level,
    flat_top_storey,
    study_lad_code AS lad_code,
    NULLIF(uprn, '') AS uprn,
    UPPER(REPLACE(postcode, ' ', '')) AS postcode_key,
    CAST(lodgement_date AS DATE) AS lodgement_date,
    TRY_CAST(inspection_date AS DATE) AS inspection_date,
    TRY_CAST(total_floor_area AS DOUBLE) AS total_floor_area,
    TRY_CAST(number_habitable_rooms AS INTEGER) AS habitable_rooms,
    TRY_CAST(number_heated_rooms AS INTEGER) AS heated_rooms,
    TRY_CAST(current_energy_efficiency AS INTEGER) AS current_energy_efficiency,
    TRY_CAST(extension_count AS INTEGER) AS extension_count,
    TRY_CAST(number_open_fireplaces AS INTEGER) AS open_fireplaces,
    LOWER(TRIM(transaction_type)) AS transaction_type
FROM READ_PARQUET('${interim}/epc_study_area/*.parquet');
