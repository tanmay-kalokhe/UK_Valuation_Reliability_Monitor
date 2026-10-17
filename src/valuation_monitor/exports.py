"""Export address-free tables for the Power BI dashboard.

Writes Parquet files to dashboards/power_bi/data/ (git-ignored):
- dim_local_authority, dim_area, dim_property_type
- fact_sales: one row per Category A sale with no address fields. Market and match
  columns exist from Week 1; model columns (estimate, price range, error, decision) are
  added in Weeks 2 and 3.
- fact_monitoring: one row per local authority and month (Week 3)

The date table is built in DAX inside Power BI.
Table definitions are in dashboards/power_bi/data_model.md.

Usage:
    python -m valuation_monitor.exports
"""

from valuation_monitor.config import PROJECT_ROOT, load_config
from valuation_monitor.db import connect

EXPORTS = {
    "dim_local_authority": """
        SELECT
            lad_code AS local_authority_code,
            lad_name AS local_authority_name,
            market,
            CASE WHEN lad_code LIKE 'W%' THEN 'Wales' ELSE 'England' END AS nation
        FROM study_area
    """,
    "dim_area": """
        SELECT DISTINCT
            lad_code || '|' || postcode_district AS area_key,
            postcode_district,
            lad_code AS local_authority_code
        FROM match_sales
        WHERE postcode_district IS NOT NULL
    """,
    "dim_property_type": """
        SELECT * FROM (VALUES
            ('D', 'Detached', 1),
            ('S', 'Semi-detached', 2),
            ('T', 'Terraced', 3),
            ('F', 'Flat/Maisonette', 4)
        ) AS t(property_type_code, property_type_name, sort_order)
    """,
    # Model columns: the time-split test period, for the model chosen on the calibration period
    # (as in reports/model_performance.md). Sales outside the test period have no estimate.
    "fact_sales": """
        WITH selected AS (
            SELECT p.estimator
            FROM model_predictions AS p
            INNER JOIN model_input AS m ON p.transaction_id = m.transaction_id
            WHERE p.split = 'time' AND m.period = 'calibration' AND p.estimator <> 'baseline'
            GROUP BY p.estimator
            ORDER BY MEDIAN(ABS(p.estimate / m.price - 1))
            LIMIT 1
        ),

        test AS (
            SELECT
                p.transaction_id,
                MAX(p.estimate) FILTER (
                    WHERE p.estimator = (SELECT estimator FROM selected)
                ) AS estimate_model,
                MAX(p.estimate) FILTER (WHERE p.estimator = 'baseline') AS estimate_baseline
            FROM model_predictions AS p
            INNER JOIN model_input AS m ON p.transaction_id = m.transaction_id
            WHERE p.split = 'time' AND m.period = 'test'
            GROUP BY p.transaction_id
        )

        SELECT
            ROW_NUMBER() OVER (ORDER BY s.sale_date, s.transaction_id) AS sale_key,
            s.sale_date,
            s.lad_code || '|' || s.postcode_district AS area_key,
            s.postcode_district,
            s.property_type AS property_type_code,
            s.is_new_build AS new_build,
            s.tenure,
            s.price,
            o.match_status = 'matched' AS epc_matched,
            o.match_status,
            o.match_tier,
            t.transaction_id IS NOT NULL AS in_test_set,
            CAST(ROUND(t.estimate_model) AS BIGINT) AS estimate_model,
            CAST(ROUND(t.estimate_baseline) AS BIGINT) AS estimate_baseline,
            ABS(t.estimate_model - s.price) / s.price AS ape_model,
            ABS(t.estimate_baseline - s.price) / s.price AS ape_baseline
        FROM match_sales AS s
        INNER JOIN match_outcome AS o ON s.transaction_id = o.transaction_id
        LEFT JOIN test AS t ON s.transaction_id = t.transaction_id
        WHERE s.postcode_district IS NOT NULL
    """,
}


def export_power_bi(config: dict) -> None:
    out_dir = PROJECT_ROOT / "dashboards" / "power_bi" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    with connect(config, read_only=True) as con:
        for name, query in EXPORTS.items():
            target = out_dir / f"{name}.parquet"
            con.execute(f"COPY ({query}) TO '{target.as_posix()}' (FORMAT parquet)")
            rows = con.execute(f"SELECT count(*) FROM '{target.as_posix()}'").fetchone()[0]
            print(f"  wrote {target.name}: {rows:,} rows")


if __name__ == "__main__":
    export_power_bi(load_config())
