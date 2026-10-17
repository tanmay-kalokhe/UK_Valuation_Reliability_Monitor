"""Tests for the feature SQL in sql/03_features/, above all the information cut-off.

Synthetic sales are loaded into an in-memory DuckDB with a flat HPI (100 every month), so
indexed prices equal raw prices. The project database is never opened.
"""

from datetime import date

import duckdb
import pytest

from valuation_monitor.db import run_sql_folder

PARAMS = {
    "info_lag_months": "3",
    "history_window_months": "12",
    "min_comparables": "5",
    "floor_area_min": "15.0",
    "floor_area_max": "1000.0",
    "train_start": "2021-01-01",
    "calibration_start": "2025-03-01",
    "test_start": "2025-09-01",
    "test_end": "2026-08-31",
}

# (transaction_id, sale_date, price, district, postcode_key)
SALES = [
    # Six comparables in AB1 inside the window for an October 2023 sale (Jul 2022 to Jun 2023).
    *[(f"C{n}", date(2023, n, 10), 100_000, "AB1", "AB11AA") for n in range(1, 7)],
    ("LEAK", date(2023, 9, 1), 1_000_000, "AB1", "AB11AA"),  # after the cut-off: must be ignored
    ("OLD", date(2022, 3, 1), 80_000, "AB1", "AB11AA"),  # before the window
    ("P1", date(2023, 8, 1), 90_000, "AB1", "AB11AA"),  # same property, after the cut-off
    ("TARGET", date(2023, 10, 15), 500_000, "AB1", "AB11AA"),
    # Sales in AB2 used to test the certificate parsing.
    *[(f"X{n}", date(2023, 5, 1), 200_000, "AB2", "AB21BB") for n in range(1, 6)],
]

# transaction_id -> (property_key, construction_age_band, floor_level, total_floor_area)
LINKS = {
    "OLD": ("U1", "England and Wales: 1930-1949", None, 80.0),
    "P1": ("U1", "England and Wales: 1930-1949", None, 80.0),
    "TARGET": ("U1", "England and Wales: 1930-1949", None, 80.0),
    "X1": ("U2", "England and Wales: before 1900", "1st", 60.0),
    "X2": ("U3", "England and Wales: 2007 onwards", "Ground", 70.0),
    "X3": ("U4", "2015", "mid floor", 5.0),
    "X4": ("U5", "NO DATA!", "Basement", 90.0),
    "X5": ("U6", "Pre-1900", "12th", 100.0),
}


@pytest.fixture(scope="module")
def con():
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE stg_hpi AS SELECT 'L1' AS lad_code, CAST(m AS DATE) AS month_start, "
        "100.0 AS index_detached, 100.0 AS index_semi_detached, 100.0 AS index_terraced, "
        "100.0 AS index_flat FROM range(DATE '2019-01-01', DATE '2027-01-01', INTERVAL 1 MONTH) "
        "AS t(m)"
    )
    con.execute(
        "CREATE TABLE match_sales (transaction_id VARCHAR, sale_date DATE, price BIGINT, "
        "property_type VARCHAR, tenure VARCHAR, is_new_build BOOLEAN, lad_code VARCHAR, "
        "postcode_key VARCHAR, postcode_district VARCHAR)"
    )
    con.executemany(
        "INSERT INTO match_sales VALUES (?, ?, ?, 'T', 'F', FALSE, 'L1', ?, ?)",
        [(t, d, p, pc, district) for t, d, p, district, pc in SALES],
    )
    con.execute(
        "CREATE TABLE stg_postcode_lookup AS SELECT * FROM (VALUES "
        "('AB11AA', 'M1', 'Group A'), ('AB21BB', 'M2', 'Group B')) "
        "AS t(postcode_key, msoa21_code, area_classification)"
    )
    con.execute(
        "CREATE TABLE stg_epc (certificate_number VARCHAR, current_energy_rating VARCHAR, "
        "epc_property_type VARCHAR, current_energy_efficiency INTEGER, built_form VARCHAR, "
        "flat_top_storey VARCHAR, mains_gas_flag VARCHAR, transaction_type VARCHAR, "
        "total_floor_area DOUBLE, habitable_rooms INTEGER, construction_age_band VARCHAR, "
        "floor_level VARCHAR, main_fuel VARCHAR, extension_count INTEGER, "
        "open_fireplaces INTEGER)"
    )
    con.execute(
        "CREATE TABLE link_sale_epc (transaction_id VARCHAR, certificate_number VARCHAR, "
        "days_before_sale INTEGER)"
    )
    con.execute("CREATE TABLE match_property (transaction_id VARCHAR, property_key VARCHAR)")
    for transaction_id, (key, band, floor, area) in LINKS.items():
        cert = f"E-{transaction_id}"
        con.execute(
            "INSERT INTO stg_epc VALUES (?, 'D', 'House', 60, 'Mid-Terrace', 'N', 'Y', "
            "'marketed sale', ?, 4, ?, ?, 'mains gas (not community)', 0, 0)",
            [cert, area, band, floor],
        )
        con.execute("INSERT INTO link_sale_epc VALUES (?, ?, 100)", [transaction_id, cert])
        con.execute("INSERT INTO match_property VALUES (?, ?)", [transaction_id, key])
    run_sql_folder(con, "03_features", PARAMS, verbose=False)
    yield con
    con.close()


def _one(con, sql, params=None):
    rows = con.execute(sql, params or []).fetchall()
    assert len(rows) == 1
    return rows[0]


def test_cut_off_is_three_months_before_the_sale_month(con):
    cutoff, hpi_month = _one(
        con, "SELECT info_cutoff, hpi_month FROM feat_sales WHERE transaction_id = 'TARGET'"
    )
    assert cutoff == date(2023, 7, 1)
    assert hpi_month == date(2023, 6, 1)


def test_baseline_uses_only_sales_before_the_cut_off(con):
    estimate, level, comparables = _one(
        con,
        "SELECT b.baseline_estimate, b.baseline_level, b.district_comparables "
        "FROM model_input AS m JOIN feat_baseline AS b USING (area_key, property_type, "
        "sale_month) WHERE m.transaction_id = 'TARGET'",
    )
    # C1 to C6 only: LEAK and P1 are after the cut-off, OLD is before the window.
    assert comparables == 6
    assert estimate == pytest.approx(100_000)
    assert level == "district"


def test_previous_sale_must_precede_the_cut_off(con):
    previous_date, previous_price = _one(
        con,
        "SELECT previous_sale_date, previous_price FROM feat_previous_sale "
        "WHERE transaction_id = 'TARGET'",
    )
    assert previous_date == date(2022, 3, 1)  # OLD, not P1
    assert previous_price == 80_000


def test_target_and_periods(con):
    target, period = _one(
        con,
        "SELECT log_ratio_target, period FROM model_input WHERE transaction_id = 'TARGET'",
    )
    assert target == pytest.approx(1.6094379, rel=1e-6)  # ln(500,000 / 100,000)
    assert period == "train"


@pytest.mark.parametrize(
    ("transaction_id", "year", "floor", "area"),
    [
        ("X1", 1890, 1, 60.0),
        ("X2", 2010, 0, 70.0),
        ("X3", 2015, None, None),  # 5 m² is implausible, so missing
        ("X4", None, -1, 90.0),
        ("X5", 1890, 12, 100.0),
    ],
)
def test_certificate_parsing(con, transaction_id, year, floor, area):
    row = _one(
        con,
        "SELECT construction_year, floor_number, floor_area FROM feat_epc WHERE transaction_id = ?",
        [transaction_id],
    )
    assert row == (year, floor, area)
