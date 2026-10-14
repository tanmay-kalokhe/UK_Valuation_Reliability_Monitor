"""Link Price Paid sales to EPC certificates (Week 1).

The rules live in sql/02_matching/:
- addresses are normalised in SQL and compared only within the same postcode;
- three rule tiers (exact, numbers + street, named house), strongest first;
- ties between properties are left unmatched (precision first);
- each matched sale takes the latest certificate lodged on or before the sale date.

Splink (probabilistic matching) is compared against these rules in Week 2, using a
hand-checked sample of 300 pairs.

Usage:
    python -m valuation_monitor.matching          # run the matching SQL and write the report
"""

from valuation_monitor.config import load_config
from valuation_monitor.db import connect, run_sql_folder, sql_params


def run_matching(config: dict) -> None:
    """Run sql/02_matching/ and print the headline match rate."""
    with connect(config) as con:
        run_sql_folder(con, "02_matching", sql_params(config))
        total, matched = con.execute(
            "SELECT count(*), count(*) FILTER (WHERE match_status = 'matched') FROM match_outcome"
        ).fetchone()
        print(f"  matched {matched:,} of {total:,} Category A sales ({matched / total:.1%})")


def main() -> None:
    config = load_config()
    run_matching(config)
    from valuation_monitor.match_report import write_match_report

    write_match_report(config)


if __name__ == "__main__":
    main()
