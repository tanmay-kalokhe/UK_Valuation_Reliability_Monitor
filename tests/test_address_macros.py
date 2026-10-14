"""Unit tests for the address macros in sql/02_matching/01_address_macros.sql.

Each test runs against a fresh in-memory DuckDB connection, so the project database is never
opened.
"""

import duckdb
import pytest

from valuation_monitor.db import SQL_ROOT

MACRO_FILE = SQL_ROOT / "02_matching" / "01_address_macros.sql"


@pytest.fixture(scope="module")
def con():
    connection = duckdb.connect()
    connection.execute(MACRO_FILE.read_text(encoding="utf-8"))
    yield connection
    connection.close()


def one(con, sql, *params):
    """Return the first column of the first row of a query."""
    return con.execute(sql, params).fetchone()[0]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Flat 3, 24 Taylor-Way", "FLAT 3 24 TAYLOR WAY"),
        ("Apartment 5 The Mill", "FLAT 5 THE MILL"),
        (None, ""),
    ],
)
def test_normalise_address(con, raw, expected):
    assert one(con, "SELECT normalise_address(?)", raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Flat 3, 24 Taylor Way", ["24", "3"]),
        ("24 Taylor Way Flat 3", ["24", "3"]),
        ("Flat D, 20 Birchington Road", ["20", "_D"]),
        ("42-43 Cartwright Gardens", ["42", "43"]),
        ("12A High Street", ["12A"]),
        ("Flat B1002 Oxygen Tower 50 Store Street", ["50", "B1002"]),
        ("Rose Cottage", []),
    ],
)
def test_address_tokens(con, raw, expected):
    tokens = one(con, "SELECT address_tokens(normalise_address(?))", raw)
    assert list(tokens) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Flat 3, 24 Taylor Way", "TAYLOR WAY"),
        ("Highlands Coxpark", "HIGHLANDS COXPARK"),
    ],
)
def test_address_words(con, raw, expected):
    words = one(con, "SELECT address_words(normalise_address(?))", raw)
    assert words == expected
