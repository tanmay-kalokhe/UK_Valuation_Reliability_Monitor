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
}


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
            description = info["columns"].get(column, "")
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
