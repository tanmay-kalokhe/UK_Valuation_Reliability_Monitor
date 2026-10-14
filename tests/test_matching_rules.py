"""Tests for the address-matching rules in sql/02_matching/.

A small set of sales and certificates is loaded into an in-memory DuckDB, the matching SQL is
run, and the resulting match_outcome rows are checked. The project database is never opened.
"""

from datetime import date

import duckdb
import pytest

from valuation_monitor.db import run_sql_folder

SALE_DATE = date(2024, 6, 1)

SALE_COLUMNS = (
    "transaction_id, sale_date, price, property_type, tenure, is_new_build, lad_code, "
    "postcode_key, postcode_district, saon, paon, street, ppd_category"
)
EPC_COLUMNS = (
    "certificate_number, uprn, postcode_key, lodgement_date, epc_property_type, "
    "transaction_type, address1, address2, address3"
)
OUTCOME_COLUMNS = (
    "transaction_id",
    "match_status",
    "match_tier",
    "certificate_number",
    "days_before_sale",
)


def _sale(transaction_id, postcode_key, saon, paon, street, category="A"):
    return (
        transaction_id,
        SALE_DATE,
        200000,
        "T",
        "F",
        False,
        "E08000003",
        postcode_key,
        "AB1",
        saon,
        paon,
        street,
        category,
    )


SALES = [
    _sale("S1", "AB11AA", None, "24", "TAYLOR WAY"),
    _sale("S2", "AB12BB", "FLAT 3", "24", "MILL LANE"),
    _sale("S3", "AB13CC", None, "HIGHLANDS", None),
    _sale("S4", "AB14DD", None, "5", "OAK ROAD"),
    _sale("S5", "ZZ99ZZ", None, "9", "NOWHERE ROAD"),
    _sale("S6", "AB15EE", None, "7", "ELM ROAD"),
    _sale("S7", "AB11AA", None, "24", "TAYLOR WAY", category="B"),
]

# (certificate_number, uprn, postcode_key, lodgement_date, epc_property_type,
#  transaction_type, address1, address2, address3)
EPCS = [
    ("C1", "U1", "AB11AA", date(2020, 1, 1), "House", "marketed sale", "24 Taylor Way", None, None),
    ("C2", "U1", "AB11AA", date(2025, 1, 1), "House", "marketed sale", "24 Taylor Way", None, None),
    (
        "C3",
        "U2",
        "AB12BB",
        date(2019, 5, 1),
        "House",
        "marketed sale",
        "24 Mill Lane",
        "Flat 3",
        None,
    ),
    (
        "C4",
        "U3",
        "AB13CC",
        date(2018, 3, 1),
        "House",
        "marketed sale",
        "Highlands",
        "Coxpark",
        None,
    ),
    ("C5", "U4", "AB14DD", date(2025, 2, 1), "House", "marketed sale", "5 Oak Road", None, None),
    ("C6", "U6A", "AB15EE", date(2020, 1, 1), "House", "marketed sale", "7 Elm Road", None, None),
    ("C7", "U6B", "AB15EE", date(2021, 1, 1), "House", "marketed sale", "7 Elm Road", None, None),
]


@pytest.fixture(scope="module")
def outcomes():
    """Build the input tables, run the matching SQL once and return the outcome rows."""
    con = duckdb.connect()
    try:
        con.execute(
            "CREATE TABLE stg_price_paid (transaction_id VARCHAR, sale_date DATE, "
            "price BIGINT, property_type VARCHAR, tenure VARCHAR, is_new_build BOOLEAN, "
            "lad_code VARCHAR, postcode_key VARCHAR, postcode_district VARCHAR, "
            "saon VARCHAR, paon VARCHAR, street VARCHAR, ppd_category VARCHAR)"
        )
        con.execute(
            "CREATE TABLE stg_epc (certificate_number VARCHAR, uprn VARCHAR, "
            "postcode_key VARCHAR, lodgement_date DATE, epc_property_type VARCHAR, "
            "transaction_type VARCHAR, address1 VARCHAR, address2 VARCHAR, "
            "address3 VARCHAR)"
        )
        con.executemany(
            f"INSERT INTO stg_price_paid ({SALE_COLUMNS}) VALUES ({', '.join(['?'] * 13)})",
            SALES,
        )
        con.executemany(
            f"INSERT INTO stg_epc ({EPC_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            EPCS,
        )
        run_sql_folder(con, "02_matching", {}, verbose=False)
        rows = con.execute(
            f"SELECT {', '.join(OUTCOME_COLUMNS)} FROM match_outcome ORDER BY transaction_id"
        ).fetchall()
    finally:
        con.close()
    return [dict(zip(OUTCOME_COLUMNS, row, strict=True)) for row in rows]


def _row(outcomes, transaction_id):
    matches = [row for row in outcomes if row["transaction_id"] == transaction_id]
    assert len(matches) == 1, f"expected one outcome row for {transaction_id}"
    return matches[0]


def test_outcome_has_six_rows_and_excludes_category_b(outcomes):
    assert len(outcomes) == 6
    assert "S7" not in {row["transaction_id"] for row in outcomes}


def test_s1_matches_tier_one_to_latest_pre_sale_certificate(outcomes):
    row = _row(outcomes, "S1")
    assert row["match_status"] == "matched"
    assert row["match_tier"] == 1
    assert row["certificate_number"] == "C1"
    assert row["days_before_sale"] == 1613


def test_s2_matches_tier_two(outcomes):
    row = _row(outcomes, "S2")
    assert row["match_status"] == "matched"
    assert row["match_tier"] == 2
    assert row["certificate_number"] == "C3"


def test_s3_matches_tier_four_named_prefix(outcomes):
    row = _row(outcomes, "S3")
    assert row["match_status"] == "matched"
    assert row["match_tier"] == 4
    assert row["certificate_number"] == "C4"


def test_s4_certificate_only_after_sale(outcomes):
    row = _row(outcomes, "S4")
    assert row["match_status"] == "certificates_only_after_sale"
    assert row["certificate_number"] is None


def test_s5_no_epc_at_postcode(outcomes):
    row = _row(outcomes, "S5")
    assert row["match_status"] == "no_epc_at_postcode"


def test_s6_ambiguous_between_two_uprns(outcomes):
    row = _row(outcomes, "S6")
    assert row["match_status"] == "ambiguous"
    assert row["certificate_number"] is None
