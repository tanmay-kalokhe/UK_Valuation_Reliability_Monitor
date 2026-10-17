"""Score the SQL rules and Splink against the hand-checked labels (Week 2).

Reads the labelled sheet (docs/hand_check_protocol.md), validates it, and estimates for each
method, at property level:
- precision: of the sales a method links, the weighted share linked to the labelled property;
- recall: of the sales whose property is among the candidates, the weighted share a method
  links correctly.

Each sale is weighted by its stratum (population / sampled, decision D-019), so the
over-sampling of rare outcomes does not distort the overall figures. Intervals come from a
bootstrap that resamples within each stratum, mirroring the sampling design. "?" answers are
excluded and counted. Candidates whose certificate shows exactly the same address as the
labelled one are also accepted, because a person cannot tell them apart.

Splink is also scored across a range of thresholds, from the stored pair scores, so that the
threshold can be chosen on the labels.

Writes reports/match_accuracy.md (aggregated figures only, no addresses).

Usage:
    py -3.12 -m valuation_monitor.match_accuracy
"""

from datetime import date

import duckdb
import numpy as np
import pandas as pd

from valuation_monitor.config import PROJECT_ROOT, load_config
from valuation_monitor.db import connect
from valuation_monitor.match_review import RECHECK_NAME, SHEET_NAME

VALID_ANSWERS = {str(n) for n in range(0, 9)} | {"?"}
SPLINK_THRESHOLDS = [0.5, 0.7, 0.8, 0.9, 0.95, 0.99]

# Every candidate shown for each sale, with the normalised address of its latest certificate.
CANDIDATES_SQL = """
SELECT c.review_id, c.candidate_number, c.property_key, e.line_norm
FROM hand_check_candidates AS c
JOIN match_epc AS e ON c.latest_certificate = e.certificate_number
"""

LINKS_SQL = """
SELECT
    h.review_id,
    h.stratum,
    h.sample_weight,
    CASE WHEN p.n_properties = 1 THEN p.property_key END AS sql_key,
    CASE WHEN s.is_linked THEN s.property_key END AS splink_key
FROM hand_check_sample AS h
LEFT JOIN match_property AS p ON h.transaction_id = p.transaction_id
LEFT JOIN splink_link AS s ON h.transaction_id = s.transaction_id
"""


def load_labels(path) -> pd.DataFrame:
    """Read and validate a labelled sheet; returns review_id and answer (text)."""
    sheet = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    sheet["answer"] = sheet["answer"].str.strip()
    blank = sheet["answer"] == ""
    invalid = ~sheet["answer"].isin(VALID_ANSWERS) & ~blank
    if blank.any() or invalid.any():
        raise SystemExit(
            f"{path.name}: {int(blank.sum())} blank and {int(invalid.sum())} invalid answers "
            f"(rows {sheet.loc[blank | invalid, 'review_id'].head(10).tolist()}). "
            "Every answer must be 0 to 8 or ?."
        )
    return sheet[["review_id", "answer"]].astype({"review_id": int})


def truth_sets(labels: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    """review_id, answer and the set of property keys accepted as correct."""
    chosen = labels[~labels["answer"].isin(["0", "?"])].astype({"answer": int})
    chosen = chosen.merge(
        candidates, left_on=["review_id", "answer"], right_on=["review_id", "candidate_number"]
    )[["review_id", "line_norm"]]
    same_address = candidates.merge(chosen, on=["review_id", "line_norm"])
    keys = same_address.groupby("review_id")["property_key"].agg(frozenset)
    out = labels.copy()
    out["truth"] = out["review_id"].map(keys)
    out["truth"] = out["truth"].apply(lambda k: k if isinstance(k, frozenset) else frozenset())
    return out


def weighted_scores(df: pd.DataFrame, key_column: str) -> dict[str, float]:
    """Weighted precision and recall of one method's links (rows with a usable label)."""
    linked = df[key_column].notna().to_numpy()
    correct = np.array(
        [k in t for k, t in zip(df[key_column], df["truth"], strict=True)], dtype=bool
    )
    has_truth = df["truth"].apply(bool).to_numpy()
    w = df["sample_weight"].to_numpy(dtype=float)
    precision = (w * (linked & correct)).sum() / max((w * linked).sum(), 1e-12)
    recall = (w * (linked & correct)).sum() / max((w * has_truth).sum(), 1e-12)
    return {"precision": float(precision), "recall": float(recall)}


def stratified_bootstrap(
    df: pd.DataFrame, key_column: str, n_resamples: int, seed: int
) -> dict[str, tuple[float, float]]:
    """95% percentile intervals, resampling sales within each stratum."""
    rng = np.random.default_rng(seed)
    groups = [g.index.to_numpy() for _, g in df.groupby("stratum")]
    draws = {"precision": [], "recall": []}
    for _ in range(n_resamples):
        index = np.concatenate([rng.choice(g, size=g.size, replace=True) for g in groups])
        scores = weighted_scores(df.loc[index], key_column)
        for metric, value in scores.items():
            draws[metric].append(value)
    return {m: tuple(np.percentile(v, [2.5, 97.5])) for m, v in draws.items()}


def score(con: duckdb.DuckDBPyConnection, labels: pd.DataFrame, n_resamples: int, seed: int):
    candidates = con.execute(CANDIDATES_SQL).df()
    df = con.execute(LINKS_SQL).df().merge(truth_sets(labels, candidates), on="review_id")
    usable = df[df["answer"] != "?"].reset_index(drop=True)
    results = {}
    for method, column in [("SQL rules", "sql_key"), ("Splink", "splink_key")]:
        results[method] = {
            **weighted_scores(usable, column),
            "ci": stratified_bootstrap(usable, column, n_resamples, seed),
        }
    pairs = con.execute(
        "SELECT h.review_id, s.property_key, s.match_probability, s.match_weight "
        "FROM splink_scores AS s "
        "JOIN hand_check_sample AS h USING (transaction_id)"
    ).df()
    curve = []
    for threshold in SPLINK_THRESHOLDS:
        # Rank on the weight, which does not saturate; the threshold is on the probability.
        top = pairs.groupby("review_id")["match_weight"].transform("max")
        best = pairs[(pairs["match_weight"] == top) & (pairs["match_probability"] >= threshold)]
        untied = best.groupby("review_id").filter(lambda g: len(g) == 1)
        keys = untied.set_index("review_id")["property_key"]
        trial = usable.assign(splink_trial=usable["review_id"].map(keys))
        curve.append((threshold, weighted_scores(trial, "splink_trial")))
    return {
        "results": results,
        "curve": curve,
        "n_labelled": len(df),
        "n_unsure": int((df["answer"] == "?").sum()),
        "n_none": int((df["answer"] == "0").sum()),
    }


def _agreement(folder) -> str:
    path = folder / RECHECK_NAME
    if not path.exists():
        return "The consistency re-check has not been done yet."
    try:
        recheck = load_labels(path)
    except SystemExit:
        return "The consistency re-check sheet is not complete yet."
    first = load_labels(folder / SHEET_NAME).set_index("review_id")["answer"]
    same = (recheck.set_index("review_id")["answer"] == first.loc[recheck["review_id"]]).mean()
    return f"Re-labelling {len(recheck)} rows blind gave the same answer for {same:.0%} of them."


def render(m: dict, agreement: str, threshold: float) -> str:
    def ci(value, interval):
        return f"{value:.1%} ({interval[0]:.1%} to {interval[1]:.1%})"

    rows = [
        f"| {method} | {ci(r['precision'], r['ci']['precision'])} | "
        f"{ci(r['recall'], r['ci']['recall'])} |"
        for method, r in m["results"].items()
    ]
    curve = [f"| {t:.2f} | {s['precision']:.1%} | {s['recall']:.1%} |" for t, s in m["curve"]]
    return "\n".join(
        [
            "# Matching accuracy: SQL rules against Splink, on hand-checked labels",
            "",
            f"_Generated {date.today():%d %B %Y} by `py -3.12 -m valuation_monitor.match_accuracy`"
            ". Aggregated figures only; no addresses. Sample design: decision D-019; protocol: "
            "`docs/hand_check_protocol.md`._",
            "",
            f"- **Labelled sales:** {m['n_labelled']}; {m['n_unsure']} marked unsure (excluded), "
            f"{m['n_none']} with no matching candidate.",
            f"- **Label consistency:** {agreement}",
            "",
            "## Property-level precision and recall (weighted, 95% intervals)",
            "| Method | Precision | Recall |",
            "|---|---:|---:|",
            *rows,
            "",
            f"Splink links at match probability ≥ {threshold} (configured threshold).",
            "",
            "## Splink across thresholds",
            "| Threshold | Precision | Recall |",
            "|---:|---:|---:|",
            *curve,
            "",
        ]
    )


def write_accuracy_report(config: dict) -> None:
    folder = PROJECT_ROOT / config["paths"]["interim"] / "hand_check"
    labels = load_labels(folder / SHEET_NAME)
    settings = config["matching"]
    with connect(config, read_only=True) as con:
        m = score(
            con, labels, config["validation"]["bootstrap_resamples"], settings["hand_check"]["seed"]
        )
    text = render(m, _agreement(folder), settings["splink"]["match_threshold"])
    target = PROJECT_ROOT / "reports" / "match_accuracy.md"
    target.write_text(text, encoding="utf-8", newline="\n")
    print("  wrote reports/match_accuracy.md")


if __name__ == "__main__":
    write_accuracy_report(load_config())
