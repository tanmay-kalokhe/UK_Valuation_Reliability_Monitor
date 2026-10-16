"""Tests for the hand-check sample in valuation_monitor.match_review.

A small synthetic postcode is matched in an in-memory DuckDB, the sample is drawn, and the
strata, weights, candidate shortlist and labelling sheet are checked. The project database
is never opened.
"""

from datetime import date

import duckdb
import pandas as pd
import pytest

from valuation_monitor.config import load_config
from valuation_monitor.db import run_sql_folder
from valuation_monitor.match_review import draw_sample, write_sheet

SALE_DATE = date(2024, 6, 1)
SETTINGS = {
    "strata": {"tier_1": 1, "no_address_match": 5, "ambiguous": 1},
    "max_candidates": 4,
    "seed": 42,
}


def _sale(transaction_id, postcode_key, paon, street):
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
        None,
        paon,
        street,
        None,
        "TOWN",
        "A",
        "AB1 1AA",
    )


# Twelve houses on TAYLOR WAY (AB11AA), and two UPRNs sharing one address on ELM ROAD (AB12BB).
EPCS = [
    (
        f"C{n}",
        f"U{n}",
        "AB11AA",
        date(2020, 1, 1),
        "House",
        "marketed sale",
        f"{n} Taylor Way",
        None,
        None,
    )
    for n in range(1, 13)
] + [
    ("E1", "UE1", "AB12BB", date(2020, 1, 1), "House", "marketed sale", "7 Elm Road", None, None),
    ("E2", "UE2", "AB12BB", date(2021, 1, 1), "House", "marketed sale", "7 Elm Road", None, None),
]

SALES = [
    _sale("S1", "AB11AA", "3", "TAYLOR WAY"),  # tier 1
    _sale("S2", "AB11AA", "99", "TAYLOR WAY"),  # no address match
    _sale("S3", "AB11AA", "5", "TAYLOR WAY"),  # tier 1
    _sale("S4", "AB12BB", "7", "ELM ROAD"),  # ambiguous
]


@pytest.fixture(scope="module")
def con():
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE stg_price_paid (transaction_id VARCHAR, sale_date DATE, price BIGINT, "
        "property_type VARCHAR, tenure VARCHAR, is_new_build BOOLEAN, lad_code VARCHAR, "
        "postcode_key VARCHAR, postcode_district VARCHAR, saon VARCHAR, paon VARCHAR, "
        "street VARCHAR, locality VARCHAR, town_city VARCHAR, ppd_category VARCHAR, "
        "postcode VARCHAR)"
    )
    con.execute(
        "CREATE TABLE stg_epc (certificate_number VARCHAR, uprn VARCHAR, postcode_key VARCHAR, "
        "lodgement_date DATE, epc_property_type VARCHAR, transaction_type VARCHAR, "
        "address1 VARCHAR, address2 VARCHAR, address3 VARCHAR)"
    )
    con.executemany(f"INSERT INTO stg_price_paid VALUES ({', '.join(['?'] * 16)})", SALES)
    con.executemany(f"INSERT INTO stg_epc VALUES ({', '.join(['?'] * 9)})", EPCS)
    run_sql_folder(con, "02_matching", {}, verbose=False)
    draw_sample(con, SETTINGS)
    yield con
    con.close()


def _sample(con):
    return con.execute("SELECT * FROM hand_check_sample ORDER BY transaction_id").df()


def test_strata_are_capped_and_weighted(con):
    sample = _sample(con).set_index("transaction_id")
    tier_1 = sample[sample["stratum"] == "tier_1"]
    assert len(tier_1) == 1
    assert tier_1["stratum_population"].iloc[0] == 2
    assert tier_1["sample_weight"].iloc[0] == pytest.approx(2.0)
    # Requested 5 but only one sale exists, so the stratum is taken whole with weight 1.
    assert sample.loc["S2", "stratum"] == "no_address_match"
    assert sample.loc["S2", "sample_weight"] == pytest.approx(1.0)
    assert sample.loc["S4", "stratum"] == "ambiguous"
    assert sorted(sample["review_id"]) == [1, 2, 3]


def test_draw_is_deterministic(con):
    first = _sample(con)
    draw_sample(con, SETTINGS)
    pd.testing.assert_frame_equal(first, _sample(con))


def test_shortlist_is_capped_and_keeps_rule_candidates(con):
    candidates = con.execute(
        "SELECT h.transaction_id, c.* FROM hand_check_candidates AS c "
        "JOIN hand_check_sample AS h USING (review_id)"
    ).df()
    per_sale = candidates.groupby("transaction_id")
    assert per_sale.size().max() <= SETTINGS["max_candidates"]
    assert (
        candidates.loc[candidates["transaction_id"] == "S2", "n_properties_at_postcode"] == 12
    ).all()
    ambiguous = candidates[candidates["transaction_id"] == "S4"]
    assert set(ambiguous["property_key"]) == {"UE1", "UE2"}
    assert ambiguous["passed_a_rule"].all()
    tier_1 = candidates[candidates["transaction_id"].isin(["S1", "S3"])]
    assert tier_1["passed_a_rule"].sum() == 1
    for _, group in per_sale:
        assert sorted(group["candidate_number"]) == list(range(1, len(group) + 1))


def test_sheet_is_blind_and_has_one_row_per_sale(con, tmp_path):
    path = tmp_path / "sheet.csv"
    rows = write_sheet(con, path, SETTINGS["max_candidates"])
    sheet = pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False)
    assert rows == len(sheet) == 3
    assert list(sheet.columns[-2:]) == ["answer", "notes"]
    assert (sheet["answer"] == "").all()
    forbidden = {"stratum", "passed_a_rule", "sample_weight", "transaction_id", "property_key"}
    assert not forbidden & set(sheet.columns)


def test_config_allocation_matches_sample_size():
    matching = load_config()["matching"]
    assert sum(matching["hand_check"]["strata"].values()) == matching["hand_checked_sample_size"]
