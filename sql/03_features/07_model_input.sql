-- Inputs: feat_sales, feat_epc, feat_baseline, feat_area_history, feat_previous_sale
-- Output: model_input, one row per matched Category A sale: target, baseline, features and
--         validation period
-- Assumptions:
--   * Only sales linked to a certificate are modelled; the match-bias analysis in
--     reports/match_quality.md describes what this excludes.
--   * Periods (decision D-020): history before ${train_start} (features only, never scored),
--     train, calibration from ${calibration_start}, test from ${test_start} to ${test_end}.
--   * log_ratio_target = ln(price) - ln(baseline_estimate): the models learn how far a home
--     sits above or below the HPI-indexed local median (decision D-022).
--   * Constant-price features are re-expressed at the cut-off with hpi_at_cutoff, so that they
--     are on the same scale as the baseline.

CREATE OR REPLACE TABLE model_input AS
SELECT
    s.transaction_id,
    s.sale_date,
    s.sale_month,
    s.price,
    s.lad_code,
    s.area_key,
    s.postcode_district,
    s.msoa21_code,
    s.property_type,
    s.tenure,
    s.is_new_build,
    s.area_classification,
    e.epc_property_type,
    e.built_form,
    e.current_energy_rating,
    e.main_fuel_group,
    e.certificate_reason,
    e.floor_area,
    e.habitable_rooms,
    e.current_energy_efficiency,
    e.construction_year,
    e.floor_number,
    e.is_top_storey,
    e.has_mains_gas,
    e.extension_count,
    e.open_fireplaces,
    e.certificate_age_years,
    b.baseline_estimate,
    b.baseline_level,
    b.district_comparables,
    a.district_sales,
    a.msoa_sales,
    p.years_since_previous_sale,
    LN(s.price) AS log_price,
    LN(b.baseline_estimate) AS log_baseline,
    LN(s.price) - LN(b.baseline_estimate) AS log_ratio_target,
    LN(a.district_price_per_sqm * s.hpi_at_cutoff * e.floor_area)
    - LN(b.baseline_estimate) AS log_district_sqm_value_vs_baseline,
    LN(a.msoa_price_per_sqm * s.hpi_at_cutoff * e.floor_area)
    - LN(b.baseline_estimate) AS log_msoa_sqm_value_vs_baseline,
    LN(a.msoa_price * s.hpi_at_cutoff) - LN(b.baseline_estimate) AS log_msoa_price_vs_baseline,
    LN(p.previous_price_const * s.hpi_at_cutoff)
    - LN(b.baseline_estimate) AS log_previous_price_vs_baseline,
    CASE
        WHEN s.sale_date < DATE '${train_start}' THEN 'history'
        WHEN s.sale_date < DATE '${calibration_start}' THEN 'train'
        WHEN s.sale_date < DATE '${test_start}' THEN 'calibration'
        WHEN s.sale_date <= DATE '${test_end}' THEN 'test'
    END AS period
FROM feat_sales AS s
INNER JOIN feat_epc AS e ON s.transaction_id = e.transaction_id
LEFT JOIN feat_baseline AS b
    ON
        s.area_key = b.area_key
        AND s.property_type = b.property_type
        AND s.sale_month = b.sale_month
LEFT JOIN feat_area_history AS a ON s.transaction_id = a.transaction_id
LEFT JOIN feat_previous_sale AS p ON s.transaction_id = p.transaction_id;
