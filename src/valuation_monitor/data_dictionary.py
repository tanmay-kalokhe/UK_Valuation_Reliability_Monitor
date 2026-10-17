"""Generate docs/data_dictionary.md from the live database schema.

Types, row counts, null shares and distinct counts come from the database; descriptions
come from TABLES below. No example values are written, so no address data can leak into
the committed document.

Usage:
    python -m valuation_monitor.data_dictionary
"""

from datetime import date

from valuation_monitor.config import PROJECT_ROOT, load_config
from valuation_monitor.db import connect

TABLES = {
    "stg_postcode_lookup": {
        "source": "ONS postcode to OA/LSOA/MSOA/LAD best-fit lookup, August 2026",
        "grain": "one study-area postcode (live or terminated)",
        "built_by": "sql/01_staging/01_stg_postcode_lookup.sql",
        "columns": {
            "postcode": "Postcode in standard format (e.g. LS6 1AA)",
            "postcode_key": "Postcode in upper case without spaces; the join key",
            "postcode_district": "Outward code (e.g. LS6)",
            "oa21_code": "2021 Census output area",
            "area_classification": "ONS 2021 output-area classification label",
            "lsoa21_code": "2021 lower layer super output area",
            "msoa21_code": "2021 middle layer super output area (used for maps)",
            "msoa21_name": "MSOA name",
            "lad_code": "Local authority code",
            "lad_name": "Local authority name",
            "is_terminated": "True if the postcode is no longer in use",
        },
    },
    "stg_price_paid": {
        "source": "HM Land Registry Price Paid Data, yearly files 2020 to 2026",
        "grain": "one sale in the study area (all categories)",
        "built_by": "sql/01_staging/02_stg_price_paid.sql",
        "columns": {
            "transaction_id": "Land Registry transaction identifier (braces removed)",
            "price": "Sale price, £",
            "sale_date": "Date of transfer",
            "postcode": "Postcode as published",
            "postcode_key": "Postcode in upper case without spaces",
            "postcode_district": "Outward code",
            "property_type": "D detached, S semi-detached, T terraced, F flat/maisonette, O other",
            "is_new_build": "True for a newly built property",
            "tenure": "F freehold, L leasehold",
            "paon": "Primary addressable object name (house number or name). Address field",
            "saon": "Secondary addressable object name (e.g. flat). Address field",
            "street": "Street. Address field",
            "locality": "Locality. Address field",
            "town_city": "Town or city",
            "district": "Local authority name as recorded by Land Registry",
            "county": "County",
            "ppd_category": "A standard price paid; B additional (repossessions, buy-to-let etc.)",
            "record_status": "A in the yearly files",
            "lad_code": "Study-area local authority code (from the district name)",
        },
    },
    "stg_price_paid_changes": {
        "source": "HM Land Registry Price Paid monthly update file",
        "grain": "one addition, change or deletion in the latest month, study area only",
        "built_by": "sql/01_staging/03_stg_price_paid_changes.sql",
        "columns": {
            "transaction_id": "Land Registry transaction identifier",
            "price": "Sale price, £",
            "sale_date": "Date of transfer",
            "property_type": "D, S, T, F or O",
            "ppd_category": "A or B",
            "record_status": "A added, C changed, D deleted",
            "lad_code": "Study-area local authority code",
        },
    },
    "stg_epc": {
        "source": "MHCLG domestic Energy Performance Certificates, 2008 to Oct 2026",
        "grain": "one certificate for a study-area postcode",
        "built_by": "sql/01_staging/04_stg_epc.sql",
        "columns": {
            "certificate_number": "Unique certificate identifier",
            "uprn": "Unique property reference number; identifies repeat certificates",
            "postcode": "Postcode as lodged",
            "postcode_key": "Postcode in upper case without spaces",
            "address1": "Address line 1. Address field",
            "address2": "Address line 2. Address field",
            "address3": "Address line 3. Address field",
            "lodgement_date": "Date the certificate was lodged",
            "inspection_date": "Date of the assessor's inspection",
            "epc_property_type": "House, Bungalow, Flat, Maisonette or Park home",
            "built_form": "Detached, semi-detached, mid-terrace etc.",
            "total_floor_area": "Total floor area, square metres",
            "habitable_rooms": "Number of habitable rooms",
            "heated_rooms": "Number of heated rooms",
            "current_energy_rating": "Energy rating band A to G",
            "current_energy_efficiency": "Energy efficiency score, 1 to 100+",
            "potential_energy_rating": "Band achievable with recommended improvements",
            "construction_age_band": "Construction period as recorded by the assessor",
            "epc_tenure": "Tenure as recorded on the certificate",
            "transaction_type": "Reason for the certificate (lower case), e.g. marketed sale",
            "main_fuel": "Main heating fuel",
            "mains_gas_flag": "Y/N mains gas available",
            "floor_level": "Floor level of a flat",
            "flat_top_storey": "Y/N flat on the top storey",
            "extension_count": "Number of extensions",
            "open_fireplaces": "Number of open fireplaces",
            "lad_code": "Study-area local authority code (from the ONS postcode lookup)",
        },
    },
    "stg_hpi": {
        "source": "UK House Price Index full file, to July 2026",
        "grain": "one study-area local authority and month, from January 2019",
        "built_by": "sql/01_staging/05_stg_hpi.sql",
        "columns": {
            "month_start": "First day of the month",
            "region_name": "Local authority name",
            "lad_code": "Local authority code",
            "average_price": "Mix-adjusted average price, £",
            "sales_volume": "Number of sales in the index",
            "index_all": "House price index, all property types",
            "index_detached": "Index, detached",
            "index_semi_detached": "Index, semi-detached",
            "index_terraced": "Index, terraced",
            "index_flat": "Index, flats and maisonettes",
        },
    },
    "match_sales": {
        "source": "stg_price_paid, Category A only",
        "grain": "one Category A sale",
        "built_by": "sql/02_matching/02_match_inputs.sql",
        "columns": {
            "transaction_id": "Land Registry transaction identifier",
            "sale_date": "Date of transfer",
            "price": "Sale price, £",
            "property_type": "D, S, T or F",
            "tenure": "F or L",
            "is_new_build": "True for a newly built property",
            "lad_code": "Local authority code",
            "postcode_key": "Postcode key used for blocking",
            "postcode_district": "Outward code",
            "address_norm": "Normalised saon + paon + street. Address field",
            "street_norm": "Normalised street. Address field",
            "address_tokens": "Sorted house/flat identifiers in the address",
            "address_words": "Address words without identifiers. Address field",
        },
    },
    "match_epc": {
        "source": "stg_epc",
        "grain": "one certificate",
        "built_by": "sql/02_matching/02_match_inputs.sql",
        "columns": {
            "certificate_number": "Unique certificate identifier",
            "uprn": "Unique property reference number",
            "postcode_key": "Postcode key used for blocking",
            "lodgement_date": "Date the certificate was lodged",
            "epc_property_type": "House, Bungalow, Flat, Maisonette or Park home",
            "transaction_type": "Reason for the certificate",
            "line_norm": "Normalised address1 + address2. Address field",
            "full_norm": "Normalised address1 + address2 + address3. Address field",
            "property_key": "UPRN, or postcode + normalised address when UPRN is missing",
            "address_tokens": "Sorted house/flat identifiers in the address",
            "address_words": "Address words without identifiers. Address field",
        },
    },
    "match_candidates": {
        "source": "match_sales joined to match_epc on postcode",
        "grain": "one (sale, property, rule tier) that passed a rule",
        "built_by": "sql/02_matching/03_match_candidates.sql",
        "columns": {
            "transaction_id": "Sale",
            "property_key": "Candidate property",
            "match_tier": "1 exact, 2 numbers and street, 3 named house, 4 named house + hamlet",
            "words_similarity": "Jaro-Winkler similarity of the address words",
        },
    },
    "match_property": {
        "source": "match_candidates",
        "grain": "one sale with at least one candidate",
        "built_by": "sql/02_matching/04_link_sale_epc.sql",
        "columns": {
            "transaction_id": "Sale",
            "best_tier": "Strongest tier reached",
            "property_key": "Matched property (meaningful only when n_properties = 1)",
            "n_properties": "Distinct properties tied at the best tier; above 1 means ambiguous",
        },
    },
    "link_sale_epc": {
        "source": "match_property, match_epc",
        "grain": "one matched sale",
        "built_by": "sql/02_matching/04_link_sale_epc.sql",
        "columns": {
            "transaction_id": "Sale",
            "certificate_number": "Latest certificate lodged on or before the sale date",
            "lodgement_date": "Lodgement date of that certificate",
            "days_before_sale": "Days between lodgement and sale",
        },
    },
    "match_outcome": {
        "source": "match_sales, match_property, link_sale_epc",
        "grain": "one Category A sale",
        "built_by": "sql/02_matching/04_link_sale_epc.sql",
        "columns": {
            "transaction_id": "Sale",
            "match_status": "matched, no_address_match, certificates_only_after_sale, "
            "ambiguous, no_epc_at_postcode or no_postcode",
            "match_tier": "Best tier reached (blank if no candidate)",
            "certificate_number": "Linked certificate (matched sales only)",
            "days_before_sale": "Days between lodgement and sale (matched sales only)",
        },
    },
    "feat_hpi": {
        "source": "stg_hpi",
        "grain": "one local authority, property type and month",
        "built_by": "sql/03_features/01_feat_hpi.sql",
        "columns": {
            "lad_code": "Local authority code",
            "month_start": "First day of the month",
            "property_type": "D, S, T or F",
            "hpi_index": "UK HPI index for that type (all types share one base month)",
        },
    },
    "feat_sales": {
        "source": "match_sales, stg_postcode_lookup, feat_hpi",
        "grain": "one Category A sale with a postcode district (matched or not)",
        "built_by": "sql/03_features/02_feat_sales.sql",
        "columns": {
            "transaction_id": "Sale",
            "sale_date": "Date of transfer",
            "price": "Sale price, £",
            "property_type": "D, S, T or F",
            "tenure": "F freehold, L leasehold",
            "is_new_build": "True for a newly built property",
            "lad_code": "Local authority code",
            "postcode_district": "Outward code",
            "msoa21_code": "2021 MSOA of the postcode",
            "area_classification": "ONS 2021 output-area classification",
            "area_key": "lad_code|postcode_district",
            "sale_month": "First day of the sale month",
            "info_cutoff": "Information cut-off: first day of (sale month - 3 months) (D-022)",
            "hpi_month": "HPI month used for indexing: the month before the cut-off",
            "hpi_sale_month": "HPI for the type in the sale month (used when the sale is a "
            "comparable)",
            "hpi_at_cutoff": "HPI for the type in hpi_month",
        },
    },
    "feat_baseline": {
        "source": "feat_sales",
        "grain": "one area_key, property type and sale month",
        "built_by": "sql/03_features/03_feat_baseline.sql",
        "columns": {
            "area_key": "lad_code|postcode_district",
            "property_type": "D, S, T or F",
            "sale_month": "First day of the sale month",
            "district_comparables": "Comparable sales in the district window",
            "baseline_estimate": "Median comparable price indexed to the cut-off, £ (D-004)",
            "baseline_level": "district, or local_authority when the district had too few sales",
        },
    },
    "feat_epc": {
        "source": "link_sale_epc, match_property, stg_epc",
        "grain": "one matched sale",
        "built_by": "sql/03_features/04_feat_epc.sql",
        "columns": {
            "transaction_id": "Sale",
            "certificate_number": "Linked certificate (latest on or before the sale)",
            "property_key": "Matched property (UPRN, or postcode + address without one)",
            "current_energy_rating": "Energy rating A to G",
            "epc_property_type": "House, Flat, Bungalow, Maisonette or Park home",
            "current_energy_efficiency": "Energy efficiency score",
            "certificate_age_years": "Years between lodgement and sale",
            "built_form": "Detached, semi-detached, terrace types",
            "is_top_storey": "True for a top-floor flat",
            "has_mains_gas": "True if mains gas is available",
            "certificate_reason": "Why the certificate was lodged (marketed sale, rental, ...)",
            "floor_area": "Total floor area, m² (missing outside the configured range)",
            "habitable_rooms": "Habitable rooms (missing outside 1 to 30)",
            "construction_year": "Midpoint of the construction age band",
            "floor_number": "Floor of a flat (ground 0, basement -1)",
            "main_fuel_group": "mains_gas, electricity, oil or other",
            "extension_count": "Number of extensions",
            "open_fireplaces": "Number of open fireplaces",
        },
    },
    "feat_area_history": {
        "source": "feat_sales, feat_epc",
        "grain": "one Category A sale with a postcode district",
        "built_by": "sql/03_features/05_feat_area_history.sql",
        "columns": {
            "transaction_id": "Sale",
            "district_sales": "Sales in the area_key in the 12 months before the cut-off",
            "msoa_sales": "Sales in the MSOA in the same window",
            "district_price_per_sqm": "Median £/m² in the district, constant prices",
            "msoa_price": "Median price in the MSOA, constant prices",
            "msoa_price_per_sqm": "Median £/m² in the MSOA, constant prices",
        },
    },
    "feat_previous_sale": {
        "source": "feat_sales, feat_epc",
        "grain": "one matched sale whose property sold earlier, before the cut-off",
        "built_by": "sql/03_features/06_feat_previous_sale.sql",
        "columns": {
            "transaction_id": "Sale",
            "previous_sale_date": "Date of the property's previous sale",
            "previous_price": "Previous price, £",
            "previous_price_const": "Previous price in constant prices",
            "years_since_previous_sale": "Years between the two sales",
        },
    },
    "model_input": {
        "source": "feat_sales, feat_epc, feat_baseline, feat_area_history, feat_previous_sale",
        "grain": "one matched Category A sale",
        "built_by": "sql/03_features/07_model_input.sql",
        "columns": {
            "transaction_id": "Sale",
            "log_price": "ln(price)",
            "log_baseline": "ln(baseline_estimate)",
            "log_ratio_target": "Model target: ln(price) - ln(baseline_estimate) (D-022)",
            "log_district_sqm_value_vs_baseline": "ln(district £/m² x floor area at the "
            "cut-off) - ln(baseline)",
            "log_msoa_sqm_value_vs_baseline": "ln(MSOA £/m² x floor area at the cut-off) - "
            "ln(baseline)",
            "log_msoa_price_vs_baseline": "ln(MSOA median price at the cut-off) - ln(baseline)",
            "log_previous_price_vs_baseline": "ln(previous price indexed to the cut-off) - "
            "ln(baseline)",
            "period": "history, train, calibration or test (D-020)",
        },
    },
    "model_predictions": {
        "source": "src/valuation_monitor/modelling.py",
        "grain": "one sale, split, fold and estimator",
        "built_by": "src/valuation_monitor/modelling.py",
        "columns": {
            "transaction_id": "Sale",
            "split": "time, or la_holdout",
            "fold": "all for the time split; the held-out local authority otherwise",
            "estimator": "baseline, lightgbm or catboost",
            "estimate": "Estimated value, £",
        },
    },
    "splink_link": {
        "source": "match_sales, match_epc (Splink model)",
        "grain": "one Category A sale with at least one scored pair",
        "built_by": "src/valuation_monitor/match_splink.py",
        "columns": {
            "transaction_id": "Sale",
            "property_key": "Highest-probability property (blank when tied)",
            "match_probability": "Splink match probability of that pair",
            "n_tied": "Properties tied at the highest probability",
            "is_linked": "True when untied and at or above the threshold",
        },
    },
    "splink_scores": {
        "source": "Splink predictions",
        "grain": "one scored (sale, property) pair for a hand-checked sale",
        "built_by": "src/valuation_monitor/match_splink.py",
        "columns": {
            "match_probability": "Splink match probability",
            "match_weight": "Splink match weight (log2 Bayes factor)",
            "transaction_id": "Sale",
            "property_key": "Candidate property",
        },
    },
    "hand_check_sample": {
        "source": "match_outcome (stratified, deterministic draw; decision D-019)",
        "grain": "one sale chosen for hand-checking",
        "built_by": "src/valuation_monitor/match_review.py",
        "columns": {
            "review_id": "Row number on the labelling sheet (shuffled across strata)",
            "transaction_id": "Sale",
            "stratum": "SQL outcome the sale was drawn from (tier_1 to tier_4, ambiguous, "
            "no_address_match, certificates_only_after_sale)",
            "stratum_population": "Sales in that stratum",
            "stratum_sampled": "Sales drawn from that stratum",
            "sample_weight": "stratum_population / stratum_sampled; used to re-weight estimates",
        },
    },
    "hand_check_candidates": {
        "source": "hand_check_sample, match_sales, match_epc, match_candidates",
        "grain": "one candidate property shown for a hand-checked sale",
        "built_by": "src/valuation_monitor/match_review.py",
        "columns": {
            "review_id": "Labelling-sheet row",
            "candidate_number": "Sheet column (candidate_1 to candidate_8), in address order",
            "property_key": "Candidate property (UPRN, or postcode + address without one)",
            "latest_certificate": "Most recent certificate for the property; its address is shown",
            "n_certificates": "Certificates lodged for the property",
            "first_lodged": "Earliest lodgement date",
            "last_lodged": "Latest lodgement date",
            "passed_a_rule": "True if the SQL rules made this a candidate (hidden from the sheet)",
            "similarity": "Jaro-Winkler similarity of the normalised addresses",
            "n_properties_at_postcode": "All properties with a certificate at the postcode",
        },
    },
}


FIRST_DESCRIPTIONS: dict[str, str] = {}
for _info in TABLES.values():
    for _column, _text in _info["columns"].items():
        FIRST_DESCRIPTIONS.setdefault(_column, _text)


def build_dictionary(con) -> str:
    lines = [
        "# Data dictionary",
        "",
        f"_Generated {date.today():%d %B %Y} by `python -m valuation_monitor.data_dictionary` "
        "from the database schema. No example values are shown, so no address data appears "
        "here. Columns marked **Address field** never leave the local database._",
        "",
    ]
    for table, info in TABLES.items():
        rows = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        schema = con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position",
            [table],
        ).fetchall()
        lines += [
            f"## `{table}`",
            f"Source: {info['source']} · Grain: {info['grain']} · Rows: {rows:,} · "
            f"Built by: `{info['built_by']}`",
            "",
            "| Column | Type | Null % | Distinct | Description |",
            "|---|---|---:|---:|---|",
        ]
        for column, dtype in schema:
            nulls, distinct = con.execute(
                f'SELECT avg(("{column}" IS NULL)::INT), count(DISTINCT "{column}") FROM {table}'
            ).fetchone()
            # Columns carried through from an earlier table reuse its description.
            description = info["columns"].get(column) or FIRST_DESCRIPTIONS.get(column, "")
            if description.endswith("Address field"):
                description = description.replace("Address field", "**Address field**")
            lines.append(f"| `{column}` | {dtype} | {nulls:.1%} | {distinct:,} | {description} |")
        lines.append("")
    return "\n".join(lines)


def write_data_dictionary(config: dict) -> None:
    with connect(config, read_only=True) as con:
        text = build_dictionary(con)
    target = PROJECT_ROOT / "docs" / "data_dictionary.md"
    target.write_text(text, encoding="utf-8", newline="\n")
    print("  wrote docs/data_dictionary.md")


if __name__ == "__main__":
    write_data_dictionary(load_config())
