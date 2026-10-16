"""Hand-checked sample for measuring matching accuracy (Week 2).

Draws a stratified sample of sales, lists the candidate properties at each sale's postcode,
and writes a labelling sheet on which a person records which candidate, if any, is the same
property. The labels are the ground truth for the precision and recall of the SQL rules and
of Splink (decision D-019; protocol in docs/hand_check_protocol.md).

Design:
- strata follow the SQL outcome (tiers 1 to 4, ambiguous, no address match, certificates
  only after the sale); rare and uncertain outcomes are over-sampled, and every estimate is
  re-weighted by stratum size;
- the sheet is blind: candidates are listed in address order and nothing shows which one
  the SQL rules (or Splink) picked, so the labels are not anchored to either method;
- the draw is deterministic (MD5 of the transaction ID and the seed) and is frozen once the
  sheet exists, so later changes to the rules cannot change the sample.

The sheet contains addresses, so it stays in data/interim/hand_check/ (git-ignored).

Usage:
    py -3.12 -m valuation_monitor.match_review sample     # draw the sample, write the sheet
    py -3.12 -m valuation_monitor.match_review recheck    # 30 rows to re-label blind
"""

import argparse
from pathlib import Path

import duckdb
import pandas as pd

from valuation_monitor.config import PROJECT_ROOT, load_config
from valuation_monitor.db import connect

SHEET_NAME = "hand_check_sheet.csv"
RECHECK_NAME = "hand_check_recheck.csv"

PROPERTY_TYPES = {"D": "Detached", "S": "Semi-detached", "T": "Terraced", "F": "Flat/Maisonette"}

SAMPLE_SQL = """
CREATE OR REPLACE TABLE hand_check_sample AS
WITH frame AS (
    SELECT
        transaction_id,
        CASE
            WHEN match_status = 'matched' THEN 'tier_' || match_tier
            ELSE match_status
        END AS stratum
    FROM match_outcome
    WHERE match_status NOT IN ('no_postcode', 'no_epc_at_postcode')
),

sizes AS (
    SELECT stratum, COUNT(*) AS stratum_population FROM frame GROUP BY stratum
),

ranked AS (
    SELECT
        f.transaction_id,
        f.stratum,
        ROW_NUMBER() OVER (
            PARTITION BY f.stratum ORDER BY MD5(f.transaction_id || ':' || $seed)
        ) AS draw_order
    FROM frame AS f
),

drawn AS (
    SELECT r.transaction_id, r.stratum, s.stratum_population
    FROM ranked AS r
    INNER JOIN hand_check_allocation AS a ON r.stratum = a.stratum
    INNER JOIN sizes AS s ON r.stratum = s.stratum
    WHERE r.draw_order <= a.n_requested
)

SELECT
    ROW_NUMBER() OVER (ORDER BY MD5(transaction_id || ':review:' || $seed)) AS review_id,
    transaction_id,
    stratum,
    stratum_population,
    COUNT(*) OVER (PARTITION BY stratum) AS stratum_sampled,
    stratum_population / COUNT(*) OVER (PARTITION BY stratum) AS sample_weight
FROM drawn
"""

CANDIDATES_SQL = """
CREATE OR REPLACE TABLE hand_check_candidates AS
WITH sale AS (
    SELECT h.review_id, s.transaction_id, s.postcode_key, s.address_norm, s.address_tokens
    FROM hand_check_sample AS h
    INNER JOIN match_sales AS s ON h.transaction_id = s.transaction_id
),

property AS (
    SELECT
        property_key,
        postcode_key,
        ARG_MAX(line_norm, lodgement_date) AS line_norm,
        ARG_MAX(address_tokens, lodgement_date) AS address_tokens,
        ARG_MAX(certificate_number, lodgement_date) AS latest_certificate,
        COUNT(*) AS n_certificates,
        MIN(lodgement_date) AS first_lodged,
        MAX(lodgement_date) AS last_lodged
    FROM match_epc
    WHERE postcode_key IN (SELECT postcode_key FROM sale)
    GROUP BY property_key, postcode_key
),

rule_pairs AS (
    SELECT DISTINCT transaction_id, property_key FROM match_candidates
),

scored AS (
    SELECT
        s.review_id,
        p.property_key,
        p.latest_certificate,
        p.n_certificates,
        p.first_lodged,
        p.last_lodged,
        p.line_norm,
        r.property_key IS NOT NULL AS passed_a_rule,
        LEN(s.address_tokens) > 0 AND s.address_tokens = p.address_tokens AS same_identifiers,
        JARO_WINKLER_SIMILARITY(s.address_norm, p.line_norm) AS similarity,
        COUNT(*) OVER (PARTITION BY s.review_id) AS n_properties_at_postcode
    FROM sale AS s
    INNER JOIN property AS p ON s.postcode_key = p.postcode_key
    LEFT JOIN rule_pairs AS r
        ON s.transaction_id = r.transaction_id AND p.property_key = r.property_key
),

shortlist AS (
    SELECT *
    FROM scored
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY review_id
        ORDER BY passed_a_rule DESC, same_identifiers DESC, similarity DESC, property_key
    ) <= $max_candidates
)

SELECT
    review_id,
    ROW_NUMBER() OVER (
        PARTITION BY review_id
        ORDER BY
            TRY_CAST(REGEXP_EXTRACT(line_norm, '\\d+') AS INTEGER) NULLS LAST,
            line_norm,
            property_key
    ) AS candidate_number,
    property_key,
    latest_certificate,
    n_certificates,
    first_lodged,
    last_lodged,
    passed_a_rule,
    similarity,
    n_properties_at_postcode
FROM shortlist
"""

SHEET_SALES_SQL = """
SELECT
    h.review_id,
    CONCAT_WS(', ', p.saon, p.paon, p.street, p.locality, p.town_city) AS sale_address,
    p.postcode AS sale_postcode,
    p.sale_date,
    p.property_type,
    CASE WHEN p.is_new_build THEN 'Y' ELSE 'N' END AS new_build,
    p.tenure,
    COALESCE(MAX(c.n_properties_at_postcode), 0) AS properties_at_postcode
FROM hand_check_sample AS h
INNER JOIN stg_price_paid AS p ON h.transaction_id = p.transaction_id
LEFT JOIN hand_check_candidates AS c ON h.review_id = c.review_id
GROUP BY ALL
ORDER BY h.review_id
"""

SHEET_CANDIDATES_SQL = """
SELECT
    c.review_id,
    c.candidate_number,
    CONCAT_WS(', ', e.address1, e.address2, e.address3) AS address,
    e.epc_property_type,
    c.n_certificates,
    YEAR(c.first_lodged) AS first_year,
    YEAR(c.last_lodged) AS last_year
FROM hand_check_candidates AS c
INNER JOIN stg_epc AS e ON c.latest_certificate = e.certificate_number
ORDER BY c.review_id, c.candidate_number
"""


def draw_sample(con: duckdb.DuckDBPyConnection, settings: dict) -> None:
    """Create hand_check_sample and hand_check_candidates from the matching tables."""
    con.execute(
        "CREATE OR REPLACE TEMP TABLE hand_check_allocation (stratum VARCHAR, n_requested INTEGER)"
    )
    con.executemany(
        "INSERT INTO hand_check_allocation VALUES (?, ?)", list(settings["strata"].items())
    )
    con.execute(SAMPLE_SQL, {"seed": str(settings["seed"])})
    con.execute(CANDIDATES_SQL, {"max_candidates": settings["max_candidates"]})


def _candidate_text(row) -> str:
    years = (
        f"{row.first_year}"
        if row.first_year == row.last_year
        else (f"{row.first_year}-{row.last_year}")
    )
    plural = "" if row.n_certificates == 1 else "s"
    return f"{row.address} [{row.epc_property_type}; {row.n_certificates} cert{plural}, {years}]"


def write_sheet(con: duckdb.DuckDBPyConnection, path: Path, max_candidates: int) -> int:
    """Write the blind labelling sheet (one row per sale) and return the number of rows."""
    sales = con.execute(SHEET_SALES_SQL).df()
    candidates = con.execute(SHEET_CANDIDATES_SQL).df()
    sales["property_type"] = sales["property_type"].map(PROPERTY_TYPES)
    for number in range(1, max_candidates + 1):
        chosen = candidates[candidates["candidate_number"] == number]
        texts = dict(zip(chosen["review_id"], chosen.apply(_candidate_text, axis=1), strict=True))
        sales[f"candidate_{number}"] = sales["review_id"].map(texts).fillna("")
    sales["answer"] = ""
    sales["notes"] = ""
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so that Excel opens the file with the right encoding.
    sales.to_csv(path, index=False, encoding="utf-8-sig")
    return len(sales)


def sample(config: dict) -> None:
    settings = config["matching"]["hand_check"]
    sheet = PROJECT_ROOT / config["paths"]["interim"] / "hand_check" / SHEET_NAME
    if sheet.exists():
        raise SystemExit(
            f"{sheet} already exists. The sample is frozen once drawn so that labels stay "
            "valid; delete the sheet deliberately to redraw it."
        )
    with connect(config) as con:
        draw_sample(con, settings)
        rows = write_sheet(con, sheet, settings["max_candidates"])
        summary = con.execute(
            "SELECT stratum, stratum_sampled, stratum_population FROM hand_check_sample "
            "GROUP BY ALL ORDER BY stratum"
        ).fetchall()
    for stratum, sampled, population in summary:
        print(f"  {stratum:30s} {sampled:>4} of {population:>8,}")
    print(f"  wrote {rows} sales to {sheet.relative_to(PROJECT_ROOT).as_posix()}")


def recheck(config: dict, n_rows: int = 30) -> None:
    """Copy a random subset of the sheet, with answers cleared, for a consistency re-label."""
    folder = PROJECT_ROOT / config["paths"]["interim"] / "hand_check"
    target = folder / RECHECK_NAME
    if target.exists():
        raise SystemExit(f"{target} already exists; delete it deliberately to redraw it.")
    sheet = pd.read_csv(folder / SHEET_NAME, encoding="utf-8-sig", keep_default_na=False)
    subset = sheet.sample(n=n_rows, random_state=config["matching"]["hand_check"]["seed"])
    subset = subset.sort_values("review_id").assign(answer="", notes="")
    subset.to_csv(target, index=False, encoding="utf-8-sig")
    print(f"  wrote {len(subset)} rows to {target.relative_to(PROJECT_ROOT).as_posix()}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["sample", "recheck"])
    args = parser.parse_args()
    if args.command == "sample":
        sample(load_config())
    else:
        recheck(load_config())


if __name__ == "__main__":
    main()
