"""Probabilistic address matching with Splink, for comparison with the SQL rules (Week 2).

Splink (Ministry of Justice) scores every sale-property pair in the same postcode with a
Fellegi-Sunter model, so the comparison with the SQL rules is like for like: same inputs,
same blocking, different decision rule (decision D-009).

Comparisons, each with several levels of agreement:
- postcode_key: exact match. Pairs are only generated within a postcode, but the postcode
  must still be a comparison, or the model would ignore the strong evidence that two
  records share one and every probability would be far too low;
- address_full: the normalised address line (exact, then Jaro-Winkler 0.95 and 0.88);
- identifiers: the sorted house/flat numbers (identical, overlapping, both absent, other);
- words: the address without its numbers (Jaro-Winkler 0.95, 0.85 and 0.70).

Training is unsupervised: u probabilities from random pairs, the prior from exact-address
links, and m probabilities by expectation-maximisation in two sessions (blocked on postcode,
which trains the address comparisons, then on the full address, which trains the postcode).
The hand-checked labels are not used for training, so they remain a fair test.

Each sale takes its highest-scoring property if its probability reaches the threshold in
config/project_config.yaml; a tie at the top is left unmatched, as in the SQL rules. Ranking
and ties use the match weight, because probabilities saturate at 1.0 in floating point.

Outputs (local database only):
- splink_link: the property chosen for each sale, if any;
- splink_scores: every scored pair for the hand-checked sales, so that the threshold can be
  re-chosen from the labels.

Usage:
    py -3.12 -m valuation_monitor.match_splink
"""

import splink.comparison_level_library as cll
import splink.comparison_library as cl
from splink import Linker, SettingsCreator, block_on
from splink.backends.duckdb import DuckDBAPI

from valuation_monitor.config import load_config
from valuation_monitor.db import connect

SALES_SQL = """
SELECT
    transaction_id AS unique_id,
    postcode_key,
    address_norm AS address_full,
    address_tokens AS identifiers,
    NULLIF(address_words, '') AS words
FROM match_sales
WHERE postcode_key IS NOT NULL
"""

# One row per property: the address on its most recent certificate.
PROPERTIES_SQL = """
SELECT
    property_key AS unique_id,
    postcode_key,
    ARG_MAX(line_norm, lodgement_date) AS address_full,
    ARG_MAX(address_tokens, lodgement_date) AS identifiers,
    NULLIF(ARG_MAX(address_words, lodgement_date), '') AS words
FROM match_epc
WHERE postcode_key IS NOT NULL
GROUP BY property_key, postcode_key
"""

IDENTIFIERS = cl.CustomComparison(
    output_column_name="identifiers",
    comparison_levels=[
        cll.NullLevel("identifiers"),
        cll.CustomLevel("len(identifiers_l) = 0 AND len(identifiers_r) = 0", "Neither has numbers"),
        cll.CustomLevel(
            "len(identifiers_l) > 0 AND identifiers_l = identifiers_r", "Identical numbers"
        ),
        cll.ArrayIntersectLevel("identifiers", min_intersection=1),
        cll.ElseLevel(),
    ],
    comparison_description="House and flat numbers",
)


def build_settings(config: dict) -> SettingsCreator:
    return SettingsCreator(
        link_type="link_only",
        comparisons=[
            cl.ExactMatch("postcode_key"),
            cl.JaroWinklerAtThresholds("address_full", [0.95, 0.88]),
            IDENTIFIERS,
            cl.JaroWinklerAtThresholds("words", [0.95, 0.85, 0.70]),
        ],
        blocking_rules_to_generate_predictions=[block_on("postcode_key")],
        retain_intermediate_calculation_columns=True,
    )


def train_and_predict(sales, properties, config: dict):
    """Train the Splink model and return all scored postcode-blocked pairs (pandas)."""
    settings = config["matching"]["splink"]
    db_api = DuckDBAPI()
    linker = Linker(
        [
            db_api.register(sales, dataset_display_name="sales"),
            db_api.register(properties, dataset_display_name="certificates"),
        ],
        build_settings(config),
    )
    linker.training.estimate_probability_two_random_records_match(
        [block_on("postcode_key", "address_full")], recall=settings["exact_match_recall"]
    )
    linker.training.estimate_u_using_random_sampling(
        max_pairs=settings["u_max_pairs"], seed=settings["seed"]
    )
    for blocking_rule in [block_on("postcode_key"), block_on("address_full")]:
        linker.training.estimate_parameters_using_expectation_maximisation(
            blocking_rule, record_sample_proportion=1.0
        )
    pairs = linker.inference.predict(threshold_match_probability=0.01)
    return pairs.as_pandas_dataframe()


def _orient(pairs, sale_ids):
    """Name the columns by role, whichever side Splink put each dataset on."""
    sales_left = pairs["unique_id_l"].isin(sale_ids)
    out = pairs[["match_probability", "match_weight"]].copy()
    out["transaction_id"] = pairs["unique_id_l"].where(sales_left, pairs["unique_id_r"])
    out["property_key"] = pairs["unique_id_r"].where(sales_left, pairs["unique_id_l"])
    return out


def run_splink(config: dict) -> None:
    threshold = config["matching"]["splink"]["match_threshold"]
    with connect(config, read_only=True) as con:
        sales = con.execute(SALES_SQL).df()
        properties = con.execute(PROPERTIES_SQL).df()
    print(f"  sales {len(sales):,}, properties {len(properties):,}")
    scored = _orient(train_and_predict(sales, properties, config), set(sales["unique_id"]))
    print(f"  scored pairs above 0.01: {len(scored):,}")

    with connect(config) as con:
        con.register("scored_df", scored)
        con.execute(
            f"""
            CREATE OR REPLACE TABLE splink_link AS
            WITH ranked AS (
                SELECT
                    *,
                    MAX(match_weight) OVER (PARTITION BY transaction_id) AS top_weight
                FROM scored_df
            ),

            best AS (
                SELECT
                    transaction_id,
                    MAX(match_probability) AS match_probability,
                    MAX(top_weight) AS match_weight,
                    ARG_MAX(property_key, match_weight) AS property_key,
                    COUNT(*) FILTER (WHERE match_weight = top_weight) AS n_tied
                FROM ranked
                GROUP BY transaction_id
            )

            SELECT
                transaction_id,
                CASE WHEN n_tied = 1 THEN property_key END AS property_key,
                match_probability,
                match_weight,
                n_tied,
                n_tied = 1 AND match_probability >= {float(threshold)} AS is_linked
            FROM best
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE splink_scores AS
            SELECT s.* FROM scored_df AS s
            WHERE s.transaction_id IN (SELECT transaction_id FROM hand_check_sample)
            """
        )
        linked, total = con.execute(
            "SELECT COUNT(*) FILTER (WHERE is_linked), (SELECT COUNT(*) FROM match_sales) "
            "FROM splink_link"
        ).fetchone()
        agree = con.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE s.is_linked AND p.n_properties = 1
                                 AND s.property_key = p.property_key) AS same,
                COUNT(*) FILTER (WHERE s.is_linked AND p.n_properties = 1
                                 AND s.property_key <> p.property_key) AS different,
                COUNT(*) FILTER (WHERE s.is_linked AND (p.transaction_id IS NULL
                                 OR p.n_properties > 1)) AS splink_only,
                COUNT(*) FILTER (WHERE NOT s.is_linked AND p.n_properties = 1) AS sql_only
            FROM splink_link AS s
            LEFT JOIN match_property AS p USING (transaction_id)
            """
        ).fetchone()
    print(
        f"  Splink links {linked:,} of {total:,} Category A sales ({linked / total:.1%}) "
        f"at probability >= {threshold}"
    )
    print(
        "  against the SQL rules (property level): same {:,}, different {:,}, "
        "Splink only {:,}, SQL only {:,}".format(*agree)
    )


if __name__ == "__main__":
    run_splink(load_config())
