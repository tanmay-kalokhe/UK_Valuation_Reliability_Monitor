# Data dictionary

_Generated 17 October 2026 by `python -m valuation_monitor.data_dictionary` from the database schema. No example values are shown, so no address data appears here. Columns marked **Address field** never leave the local database._

## `stg_postcode_lookup`
Source: ONS postcode to OA/LSOA/MSOA/LAD best-fit lookup, August 2026 · Grain: one study-area postcode (live or terminated) · Rows: 144,026 · Built by: `sql/01_staging/01_stg_postcode_lookup.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `postcode` | VARCHAR | 0.0% | 144,026 | Postcode in standard format (e.g. LS6 1AA) |
| `oa21_code` | VARCHAR | 0.0% | 9,523 | 2021 Census output area |
| `area_classification` | VARCHAR | 0.0% | 52 | ONS 2021 output-area classification label |
| `lsoa21_code` | VARCHAR | 0.0% | 1,772 | 2021 lower layer super output area |
| `msoa21_code` | VARCHAR | 0.0% | 377 | 2021 middle layer super output area (used for maps) |
| `msoa21_name` | VARCHAR | 0.0% | 377 | MSOA name |
| `lad_code` | VARCHAR | 0.0% | 7 | Local authority code |
| `lad_name` | VARCHAR | 0.0% | 7 | Local authority name |
| `postcode_key` | VARCHAR | 0.0% | 144,026 | Postcode in upper case without spaces; the join key |
| `postcode_district` | VARCHAR | 0.0% | 218 | Outward code (e.g. LS6) |
| `is_terminated` | BOOLEAN | 0.0% | 2 | True if the postcode is no longer in use |

## `stg_price_paid`
Source: HM Land Registry Price Paid Data, yearly files 2020 to 2026 · Grain: one sale in the study area (all categories) · Rows: 316,148 · Built by: `sql/01_staging/02_stg_price_paid.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `lad_code` | VARCHAR | 0.0% | 7 | Study-area local authority code (from the district name) |
| `property_type` | VARCHAR | 0.0% | 5 | D detached, S semi-detached, T terraced, F flat/maisonette, O other |
| `tenure` | VARCHAR | 0.0% | 2 | F freehold, L leasehold |
| `town_city` | VARCHAR | 0.0% | 105 | Town or city |
| `district` | VARCHAR | 0.0% | 7 | Local authority name as recorded by Land Registry |
| `county` | VARCHAR | 0.0% | 6 | County |
| `ppd_category` | VARCHAR | 0.0% | 2 | A standard price paid; B additional (repossessions, buy-to-let etc.) |
| `record_status` | VARCHAR | 0.0% | 1 | A in the yearly files |
| `transaction_id` | VARCHAR | 0.0% | 316,148 | Land Registry transaction identifier (braces removed) |
| `price` | BIGINT | 0.0% | 20,058 | Sale price, £ |
| `sale_date` | DATE | 0.0% | 2,114 | Date of transfer |
| `postcode` | VARCHAR | 0.3% | 59,748 | Postcode as published |
| `postcode_key` | VARCHAR | 0.3% | 59,748 | Postcode in upper case without spaces |
| `postcode_district` | VARCHAR | 0.3% | 244 | Outward code |
| `is_new_build` | BOOLEAN | 0.0% | 2 | True for a newly built property |
| `paon` | VARCHAR | 0.0% | 24,995 | Primary addressable object name (house number or name). **Address field** |
| `saon` | VARCHAR | 81.3% | 7,141 | Secondary addressable object name (e.g. flat). **Address field** |
| `street` | VARCHAR | 3.1% | 30,315 | Street. **Address field** |
| `locality` | VARCHAR | 58.2% | 1,504 | Locality. **Address field** |

## `stg_price_paid_changes`
Source: HM Land Registry Price Paid monthly update file · Grain: one addition, change or deletion in the latest month, study area only · Rows: 4,518 · Built by: `sql/01_staging/03_stg_price_paid_changes.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `lad_code` | VARCHAR | 0.0% | 7 | Study-area local authority code |
| `property_type` | VARCHAR | 0.0% | 5 | D, S, T, F or O |
| `ppd_category` | VARCHAR | 0.0% | 2 | A or B |
| `record_status` | VARCHAR | 0.0% | 3 | A added, C changed, D deleted |
| `transaction_id` | VARCHAR | 0.0% | 4,518 | Land Registry transaction identifier |
| `price` | BIGINT | 0.0% | 1,225 | Sale price, £ |
| `sale_date` | DATE | 0.0% | 567 | Date of transfer |

## `stg_epc`
Source: MHCLG domestic Energy Performance Certificates, 2008 to Oct 2026 · Grain: one certificate for a study-area postcode · Rows: 1,698,260 · Built by: `sql/01_staging/04_stg_epc.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `certificate_number` | VARCHAR | 0.0% | 1,698,260 | Unique certificate identifier |
| `postcode` | VARCHAR | 0.0% | 74,091 | Postcode as lodged |
| `address1` | VARCHAR | 0.0% | 1,096,303 | Address line 1. **Address field** |
| `address2` | VARCHAR | 43.1% | 66,751 | Address line 2. **Address field** |
| `address3` | VARCHAR | 87.6% | 10,354 | Address line 3. **Address field** |
| `epc_property_type` | VARCHAR | 0.0% | 5 | House, Bungalow, Flat, Maisonette or Park home |
| `built_form` | VARCHAR | 2.0% | 7 | Detached, semi-detached, mid-terrace etc. |
| `current_energy_rating` | VARCHAR | 0.0% | 7 | Energy rating band A to G |
| `potential_energy_rating` | VARCHAR | 0.0% | 7 | Band achievable with recommended improvements |
| `construction_age_band` | VARCHAR | 0.0% | 122 | Construction period as recorded by the assessor |
| `epc_tenure` | VARCHAR | 25.3% | 8 | Tenure as recorded on the certificate |
| `main_fuel` | VARCHAR | 1.6% | 53 | Main heating fuel |
| `mains_gas_flag` | VARCHAR | 13.1% | 2 | Y/N mains gas available |
| `floor_level` | VARCHAR | 62.7% | 27 | Floor level of a flat |
| `flat_top_storey` | VARCHAR | 0.0% | 2 | Y/N flat on the top storey |
| `lad_code` | VARCHAR | 0.0% | 7 | Study-area local authority code (from the ONS postcode lookup) |
| `uprn` | VARCHAR | 1.8% | 1,088,176 | Unique property reference number; identifies repeat certificates |
| `postcode_key` | VARCHAR | 0.0% | 74,091 | Postcode in upper case without spaces |
| `lodgement_date` | DATE | 0.0% | 6,591 | Date the certificate was lodged |
| `inspection_date` | DATE | 0.0% | 6,744 | Date of the assessor's inspection |
| `total_floor_area` | DOUBLE | 0.1% | 1,038 | Total floor area, square metres |
| `habitable_rooms` | INTEGER | 12.8% | 62 | Number of habitable rooms |
| `heated_rooms` | INTEGER | 12.8% | 54 | Number of heated rooms |
| `current_energy_efficiency` | INTEGER | 0.0% | 160 | Energy efficiency score, 1 to 100+ |
| `extension_count` | INTEGER | 12.8% | 5 | Number of extensions |
| `open_fireplaces` | INTEGER | 4.4% | 23 | Number of open fireplaces |
| `transaction_type` | VARCHAR | 0.1% | 19 | Reason for the certificate (lower case), e.g. marketed sale |

## `stg_hpi`
Source: UK House Price Index full file, to July 2026 · Grain: one study-area local authority and month, from January 2019 · Rows: 637 · Built by: `sql/01_staging/05_stg_hpi.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `region_name` | VARCHAR | 0.0% | 7 | Local authority name |
| `lad_code` | VARCHAR | 0.0% | 7 | Local authority code |
| `average_price` | BIGINT | 0.0% | 637 | Mix-adjusted average price, £ |
| `sales_volume` | BIGINT | 2.2% | 452 | Number of sales in the index |
| `index_detached` | DOUBLE | 0.0% | 279 | Index, detached |
| `index_semi_detached` | DOUBLE | 0.0% | 285 | Index, semi-detached |
| `index_terraced` | DOUBLE | 0.0% | 302 | Index, terraced |
| `index_flat` | DOUBLE | 0.0% | 244 | Index, flats and maisonettes |
| `month_start` | DATE | 0.0% | 91 | First day of the month |
| `index_all` | DOUBLE | 0.0% | 273 | House price index, all property types |

## `match_sales`
Source: stg_price_paid, Category A only · Grain: one Category A sale · Rows: 256,677 · Built by: `sql/02_matching/02_match_inputs.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `transaction_id` | VARCHAR | 0.0% | 256,677 | Land Registry transaction identifier |
| `sale_date` | DATE | 0.0% | 2,023 | Date of transfer |
| `price` | BIGINT | 0.0% | 14,433 | Sale price, £ |
| `property_type` | VARCHAR | 0.0% | 4 | D, S, T or F |
| `tenure` | VARCHAR | 0.0% | 2 | F or L |
| `is_new_build` | BOOLEAN | 0.0% | 2 | True for a newly built property |
| `lad_code` | VARCHAR | 0.0% | 7 | Local authority code |
| `postcode_key` | VARCHAR | 0.0% | 53,257 | Postcode key used for blocking |
| `postcode_district` | VARCHAR | 0.0% | 222 | Outward code |
| `address_norm` | VARCHAR | 0.0% | 228,708 | Normalised saon + paon + street. **Address field** |
| `street_norm` | VARCHAR | 0.0% | 28,270 | Normalised street. **Address field** |
| `address_tokens` | VARCHAR[] | 0.0% | 15,116 | Sorted house/flat identifiers in the address |
| `address_words` | VARCHAR | 0.0% | 46,495 | Address words without identifiers. **Address field** |

## `match_epc`
Source: stg_epc · Grain: one certificate · Rows: 1,698,260 · Built by: `sql/02_matching/02_match_inputs.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `certificate_number` | VARCHAR | 0.0% | 1,698,260 | Unique certificate identifier |
| `uprn` | VARCHAR | 1.8% | 1,088,176 | Unique property reference number |
| `postcode_key` | VARCHAR | 0.0% | 74,091 | Postcode key used for blocking |
| `lodgement_date` | DATE | 0.0% | 6,591 | Date the certificate was lodged |
| `epc_property_type` | VARCHAR | 0.0% | 5 | House, Bungalow, Flat, Maisonette or Park home |
| `transaction_type` | VARCHAR | 0.1% | 19 | Reason for the certificate |
| `line_norm` | VARCHAR | 0.0% | 1,174,098 | Normalised address1 + address2. **Address field** |
| `full_norm` | VARCHAR | 0.0% | 1,166,569 | Normalised address1 + address2 + address3. **Address field** |
| `property_key` | VARCHAR | 0.0% | 1,113,010 | UPRN, or postcode + normalised address when UPRN is missing |
| `address_tokens` | VARCHAR[] | 0.0% | 53,031 | Sorted house/flat identifiers in the address |
| `address_words` | VARCHAR | 0.0% | 147,375 | Address words without identifiers. **Address field** |

## `match_candidates`
Source: match_sales joined to match_epc on postcode · Grain: one (sale, property, rule tier) that passed a rule · Rows: 260,217 · Built by: `sql/02_matching/03_match_candidates.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `transaction_id` | VARCHAR | 0.0% | 246,251 | Sale |
| `property_key` | VARCHAR | 0.0% | 228,837 | Candidate property |
| `match_tier` | INTEGER | 0.0% | 4 | 1 exact, 2 numbers and street, 3 named house, 4 named house + hamlet |
| `words_similarity` | DOUBLE | 0.0% | 4,932 | Jaro-Winkler similarity of the address words |

## `match_property`
Source: match_candidates · Grain: one sale with at least one candidate · Rows: 246,251 · Built by: `sql/02_matching/04_link_sale_epc.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `transaction_id` | VARCHAR | 0.0% | 246,251 | Sale |
| `best_tier` | INTEGER | 0.0% | 4 | Strongest tier reached |
| `property_key` | VARCHAR | 0.0% | 225,248 | Matched property (meaningful only when n_properties = 1) |
| `n_properties` | BIGINT | 0.0% | 9 | Distinct properties tied at the best tier; above 1 means ambiguous |

## `link_sale_epc`
Source: match_property, match_epc · Grain: one matched sale · Rows: 243,320 · Built by: `sql/02_matching/04_link_sale_epc.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `transaction_id` | VARCHAR | 0.0% | 243,320 | Sale |
| `certificate_number` | VARCHAR | 0.0% | 227,701 | Latest certificate lodged on or before the sale date |
| `lodgement_date` | DATE | 0.0% | 6,227 | Lodgement date of that certificate |
| `days_before_sale` | BIGINT | 0.0% | 4,827 | Days between lodgement and sale |

## `match_outcome`
Source: match_sales, match_property, link_sale_epc · Grain: one Category A sale · Rows: 256,677 · Built by: `sql/02_matching/04_link_sale_epc.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `transaction_id` | VARCHAR | 0.0% | 256,677 | Sale |
| `match_tier` | INTEGER | 4.1% | 4 | Best tier reached (blank if no candidate) |
| `certificate_number` | VARCHAR | 5.2% | 227,701 | Linked certificate (matched sales only) |
| `days_before_sale` | BIGINT | 5.2% | 4,827 | Days between lodgement and sale (matched sales only) |
| `match_status` | VARCHAR | 0.0% | 6 | matched, no_address_match, certificates_only_after_sale, ambiguous, no_epc_at_postcode or no_postcode |

## `feat_hpi`
Source: stg_hpi · Grain: one local authority, property type and month · Rows: 2,548 · Built by: `sql/03_features/01_feat_hpi.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `lad_code` | VARCHAR | 0.0% | 7 | Local authority code |
| `month_start` | DATE | 0.0% | 91 | First day of the month |
| `property_type` | VARCHAR | 0.0% | 4 | D, S, T or F |
| `hpi_index` | DOUBLE | 0.0% | 398 | UK HPI index for that type (all types share one base month) |

## `feat_sales`
Source: match_sales, stg_postcode_lookup, feat_hpi · Grain: one Category A sale with a postcode district (matched or not) · Rows: 256,638 · Built by: `sql/03_features/02_feat_sales.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `transaction_id` | VARCHAR | 0.0% | 256,638 | Sale |
| `sale_date` | DATE | 0.0% | 2,022 | Date of transfer |
| `price` | BIGINT | 0.0% | 14,433 | Sale price, £ |
| `property_type` | VARCHAR | 0.0% | 4 | D, S, T or F |
| `tenure` | VARCHAR | 0.0% | 2 | F freehold, L leasehold |
| `is_new_build` | BOOLEAN | 0.0% | 2 | True for a newly built property |
| `lad_code` | VARCHAR | 0.0% | 7 | Local authority code |
| `postcode_district` | VARCHAR | 0.0% | 222 | Outward code |
| `msoa21_code` | VARCHAR | 0.1% | 377 | 2021 MSOA of the postcode |
| `area_classification` | VARCHAR | 0.1% | 52 | ONS 2021 output-area classification |
| `area_key` | VARCHAR | 0.0% | 235 | lad_code|postcode_district |
| `sale_month` | DATE | 0.0% | 80 | First day of the sale month |
| `info_cutoff` | DATE | 0.0% | 80 | Information cut-off: first day of (sale month - 3 months) (D-022) |
| `hpi_month` | DATE | 0.0% | 80 | HPI month used for indexing: the month before the cut-off |
| `hpi_sale_month` | DOUBLE | 0.3% | 366 | HPI for the type in the sale month (used when the sale is a comparable) |
| `hpi_at_cutoff` | DOUBLE | 0.0% | 365 | HPI for the type in hpi_month |

## `feat_baseline`
Source: feat_sales · Grain: one area_key, property type and sale month · Rows: 36,281 · Built by: `sql/03_features/03_feat_baseline.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `area_key` | VARCHAR | 0.0% | 235 | lad_code|postcode_district |
| `property_type` | VARCHAR | 0.0% | 4 | D, S, T or F |
| `sale_month` | DATE | 0.0% | 80 | First day of the sale month |
| `district_comparables` | BIGINT | 0.0% | 573 | Comparable sales in the district window |
| `baseline_estimate` | DOUBLE | 4.8% | 31,693 | Median comparable price indexed to the cut-off, £ (D-004) |
| `baseline_level` | VARCHAR | 4.8% | 2 | district, or local_authority when the district had too few sales |

## `feat_epc`
Source: link_sale_epc, match_property, stg_epc · Grain: one matched sale · Rows: 243,320 · Built by: `sql/03_features/04_feat_epc.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `transaction_id` | VARCHAR | 0.0% | 243,320 | Sale |
| `certificate_number` | VARCHAR | 0.0% | 227,701 | Linked certificate (latest on or before the sale) |
| `property_key` | VARCHAR | 0.0% | 222,866 | Matched property (UPRN, or postcode + address without one) |
| `current_energy_rating` | VARCHAR | 0.0% | 7 | Energy rating A to G |
| `epc_property_type` | VARCHAR | 0.0% | 5 | House, Flat, Bungalow, Maisonette or Park home |
| `current_energy_efficiency` | INTEGER | 0.0% | 118 | Energy efficiency score |
| `certificate_age_years` | DOUBLE | 0.0% | 4,827 | Years between lodgement and sale |
| `built_form` | VARCHAR | 1.0% | 6 | Detached, semi-detached, terrace types |
| `is_top_storey` | BOOLEAN | 0.0% | 2 | True for a top-floor flat |
| `has_mains_gas` | BOOLEAN | 18.2% | 2 | True if mains gas is available |
| `certificate_reason` | VARCHAR | 0.0% | 19 | Why the certificate was lodged (marketed sale, rental, ...) |
| `floor_area` | DOUBLE | 0.0% | 605 | Total floor area, m² (missing outside the configured range) |
| `habitable_rooms` | INTEGER | 18.2% | 24 | Habitable rooms (missing outside 1 to 30) |
| `construction_year` | INTEGER | 0.0% | 46 | Midpoint of the construction age band |
| `floor_number` | INTEGER | 84.1% | 23 | Floor of a flat (ground 0, basement -1) |
| `main_fuel_group` | VARCHAR | 0.8% | 4 | mains_gas, electricity, oil or other |
| `extension_count` | INTEGER | 18.2% | 5 | Number of extensions |
| `open_fireplaces` | INTEGER | 2.1% | 9 | Number of open fireplaces |

## `feat_area_history`
Source: feat_sales, feat_epc · Grain: one Category A sale with a postcode district · Rows: 256,638 · Built by: `sql/03_features/05_feat_area_history.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `transaction_id` | VARCHAR | 0.0% | 256,638 | Sale |
| `district_sales` | BIGINT | 0.0% | 965 | Sales in the area_key in the 12 months before the cut-off |
| `msoa_sales` | BIGINT | 0.0% | 464 | Sales in the MSOA in the same window |
| `district_price_per_sqm` | DOUBLE | 4.3% | 9,164 | Median £/m² in the district, constant prices |
| `msoa_price` | DOUBLE | 4.2% | 20,384 | Median price in the MSOA, constant prices |
| `msoa_price_per_sqm` | DOUBLE | 4.2% | 22,018 | Median £/m² in the MSOA, constant prices |

## `feat_previous_sale`
Source: feat_sales, feat_epc · Grain: one matched sale whose property sold earlier, before the cut-off · Rows: 20,003 · Built by: `sql/03_features/06_feat_previous_sale.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `transaction_id` | VARCHAR | 0.0% | 20,003 | Sale |
| `previous_sale_date` | DATE | 0.0% | 1,352 | Date of the property's previous sale |
| `previous_price` | BIGINT | 0.0% | 2,510 | Previous price, £ |
| `previous_price_const` | DOUBLE | 0.0% | 15,879 | Previous price in constant prices |
| `years_since_previous_sale` | DOUBLE | 0.0% | 2,176 | Years between the two sales |

## `model_input`
Source: feat_sales, feat_epc, feat_baseline, feat_area_history, feat_previous_sale · Grain: one matched Category A sale · Rows: 243,320 · Built by: `sql/03_features/07_model_input.sql`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `transaction_id` | VARCHAR | 0.0% | 243,320 | Sale |
| `sale_date` | DATE | 0.0% | 1,995 | Date of transfer |
| `sale_month` | DATE | 0.0% | 80 | First day of the sale month |
| `price` | BIGINT | 0.0% | 12,977 | Sale price, £ |
| `lad_code` | VARCHAR | 0.0% | 7 | Local authority code |
| `area_key` | VARCHAR | 0.0% | 178 | lad_code|postcode_district |
| `postcode_district` | VARCHAR | 0.0% | 169 | Outward code (e.g. LS6) |
| `msoa21_code` | VARCHAR | 0.0% | 377 | 2021 middle layer super output area (used for maps) |
| `property_type` | VARCHAR | 0.0% | 4 | D detached, S semi-detached, T terraced, F flat/maisonette, O other |
| `tenure` | VARCHAR | 0.0% | 2 | F freehold, L leasehold |
| `is_new_build` | BOOLEAN | 0.0% | 2 | True for a newly built property |
| `area_classification` | VARCHAR | 0.0% | 52 | ONS 2021 output-area classification label |
| `epc_property_type` | VARCHAR | 0.0% | 5 | House, Bungalow, Flat, Maisonette or Park home |
| `built_form` | VARCHAR | 1.0% | 6 | Detached, semi-detached, mid-terrace etc. |
| `current_energy_rating` | VARCHAR | 0.0% | 7 | Energy rating band A to G |
| `main_fuel_group` | VARCHAR | 0.8% | 4 | mains_gas, electricity, oil or other |
| `certificate_reason` | VARCHAR | 0.0% | 19 | Why the certificate was lodged (marketed sale, rental, ...) |
| `floor_area` | DOUBLE | 0.0% | 605 | Total floor area, m² (missing outside the configured range) |
| `habitable_rooms` | INTEGER | 18.2% | 24 | Number of habitable rooms |
| `current_energy_efficiency` | INTEGER | 0.0% | 118 | Energy efficiency score, 1 to 100+ |
| `construction_year` | INTEGER | 0.0% | 46 | Midpoint of the construction age band |
| `floor_number` | INTEGER | 84.1% | 23 | Floor of a flat (ground 0, basement -1) |
| `is_top_storey` | BOOLEAN | 0.0% | 2 | True for a top-floor flat |
| `has_mains_gas` | BOOLEAN | 18.2% | 2 | True if mains gas is available |
| `extension_count` | INTEGER | 18.2% | 5 | Number of extensions |
| `open_fireplaces` | INTEGER | 2.1% | 9 | Number of open fireplaces |
| `certificate_age_years` | DOUBLE | 0.0% | 4,827 | Years between lodgement and sale |
| `baseline_estimate` | DOUBLE | 4.1% | 31,308 | Median comparable price indexed to the cut-off, £ (D-004) |
| `baseline_level` | VARCHAR | 4.1% | 2 | district, or local_authority when the district had too few sales |
| `district_comparables` | BIGINT | 0.0% | 573 | Comparable sales in the district window |
| `district_sales` | BIGINT | 0.0% | 965 | Sales in the area_key in the 12 months before the cut-off |
| `msoa_sales` | BIGINT | 0.0% | 464 | Sales in the MSOA in the same window |
| `years_since_previous_sale` | DOUBLE | 91.8% | 2,176 | Years between the two sales |
| `log_price` | DOUBLE | 0.0% | 12,977 | ln(price) |
| `log_baseline` | DOUBLE | 4.1% | 31,165 | ln(baseline_estimate) |
| `log_ratio_target` | DOUBLE | 4.1% | 214,449 | Model target: ln(price) - ln(baseline_estimate) (D-022) |
| `log_district_sqm_value_vs_baseline` | DOUBLE | 4.3% | 207,136 | ln(district £/m² x floor area at the cut-off) - ln(baseline) |
| `log_msoa_sqm_value_vs_baseline` | DOUBLE | 4.2% | 218,835 | ln(MSOA £/m² x floor area at the cut-off) - ln(baseline) |
| `log_msoa_price_vs_baseline` | DOUBLE | 4.2% | 88,811 | ln(MSOA median price at the cut-off) - ln(baseline) |
| `log_previous_price_vs_baseline` | DOUBLE | 91.8% | 19,945 | ln(previous price indexed to the cut-off) - ln(baseline) |
| `period` | VARCHAR | 0.0% | 4 | history, train, calibration or test (D-020) |

## `model_predictions`
Source: src/valuation_monitor/modelling.py · Grain: one sale, split, fold and estimator · Rows: 220,569 · Built by: `src/valuation_monitor/modelling.py`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `transaction_id` | VARCHAR | 0.0% | 45,884 | Sale |
| `split` | VARCHAR | 0.0% | 2 | time, or la_holdout |
| `fold` | VARCHAR | 0.0% | 8 | all for the time split; the held-out local authority otherwise |
| `estimator` | VARCHAR | 0.0% | 3 | baseline, lightgbm or catboost |
| `estimate` | DOUBLE | 0.0% | 153,903 | Estimated value, £ |

## `splink_link`
Source: match_sales, match_epc (Splink model) · Grain: one Category A sale with at least one scored pair · Rows: 253,909 · Built by: `src/valuation_monitor/match_splink.py`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `transaction_id` | VARCHAR | 0.0% | 253,909 | Sale |
| `property_key` | VARCHAR | 8.4% | 210,160 | Highest-probability property (blank when tied) |
| `match_probability` | DOUBLE | 0.0% | 50 | Splink match probability of that pair |
| `match_weight` | DOUBLE | 0.0% | 50 | Splink match weight (log2 Bayes factor) |
| `n_tied` | BIGINT | 0.0% | 79 | Properties tied at the highest probability |
| `is_linked` | BOOLEAN | 0.0% | 2 | True when untied and at or above the threshold |

## `splink_scores`
Source: Splink predictions · Grain: one scored (sale, property) pair for a hand-checked sale · Rows: 5,315 · Built by: `src/valuation_monitor/match_splink.py`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `match_probability` | DOUBLE | 0.0% | 35 | Splink match probability |
| `match_weight` | DOUBLE | 0.0% | 35 | Splink match weight (log2 Bayes factor) |
| `transaction_id` | VARCHAR | 0.0% | 286 | Sale |
| `property_key` | VARCHAR | 0.0% | 5,182 | Candidate property |

## `hand_check_sample`
Source: match_outcome (stratified, deterministic draw; decision D-019) · Grain: one sale chosen for hand-checking · Rows: 300 · Built by: `src/valuation_monitor/match_review.py`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `review_id` | BIGINT | 0.0% | 300 | Row number on the labelling sheet (shuffled across strata) |
| `transaction_id` | VARCHAR | 0.0% | 300 | Sale |
| `stratum` | VARCHAR | 0.0% | 7 | SQL outcome the sale was drawn from (tier_1 to tier_4, ambiguous, no_address_match, certificates_only_after_sale) |
| `stratum_population` | BIGINT | 0.0% | 7 | Sales in that stratum |
| `stratum_sampled` | BIGINT | 0.0% | 5 | Sales drawn from that stratum |
| `sample_weight` | DOUBLE | 0.0% | 7 | stratum_population / stratum_sampled; used to re-weight estimates |

## `hand_check_candidates`
Source: hand_check_sample, match_sales, match_epc, match_candidates · Grain: one candidate property shown for a hand-checked sale · Rows: 2,246 · Built by: `src/valuation_monitor/match_review.py`

| Column | Type | Null % | Distinct | Description |
|---|---|---:|---:|---|
| `review_id` | BIGINT | 0.0% | 300 | Labelling-sheet row |
| `candidate_number` | BIGINT | 0.0% | 8 | Sheet column (candidate_1 to candidate_8), in address order |
| `property_key` | VARCHAR | 0.0% | 2,213 | Candidate property (UPRN, or postcode + address without one) |
| `latest_certificate` | VARCHAR | 0.0% | 2,213 | Most recent certificate for the property; its address is shown |
| `n_certificates` | BIGINT | 0.0% | 9 | Certificates lodged for the property |
| `first_lodged` | DATE | 0.0% | 1,603 | Earliest lodgement date |
| `last_lodged` | DATE | 0.0% | 1,609 | Latest lodgement date |
| `passed_a_rule` | BOOLEAN | 0.0% | 2 | True if the SQL rules made this a candidate (hidden from the sheet) |
| `similarity` | DOUBLE | 0.0% | 1,077 | Jaro-Winkler similarity of the normalised addresses |
| `n_properties_at_postcode` | BIGINT | 0.0% | 70 | All properties with a certificate at the postcode |
