"""Build the modelling table from the matched data (Week 2).

Runs sql/03_features/ in order and prints how many sales each period holds and how complete
the main features are. The SQL files state their own assumptions; the key ones are the
information cut-off (decision D-022) and the periods (decision D-020).

Usage:
    py -3.12 -m valuation_monitor.features
"""

from valuation_monitor.config import load_config
from valuation_monitor.db import connect, run_sql_folder, sql_params

CHECKED_FEATURES = [
    "baseline_estimate",
    "floor_area",
    "construction_year",
    "area_classification",
    "log_district_sqm_value_vs_baseline",
    "log_msoa_sqm_value_vs_baseline",
    "log_previous_price_vs_baseline",
]


def build_features(config: dict) -> None:
    with connect(config) as con:
        run_sql_folder(con, "03_features", sql_params(config))
        periods = con.execute(
            "SELECT period, COUNT(*) FROM model_input GROUP BY period ORDER BY MIN(sale_date)"
        ).fetchall()
        print("  sales by period: " + ", ".join(f"{p} {n:,}" for p, n in periods))
        filled = ", ".join(f"AVG(({c} IS NOT NULL)::INT)" for c in CHECKED_FEATURES)
        shares = con.execute(
            f"SELECT {filled} FROM model_input WHERE period <> 'history'"
        ).fetchone()
        for column, share in zip(CHECKED_FEATURES, shares, strict=True):
            print(f"  {column:40s} present for {share:.1%} of modelled sales")


if __name__ == "__main__":
    build_features(load_config())
