"""Model performance report: does machine learning beat the baseline, and where?

Reads model_predictions and model_input, and writes reports/model_performance.md (aggregated
figures only, no addresses) with two charts in reports/figures/. Every figure carries a
bootstrap 95% confidence interval (validation.py). The model taken forward to Week 3 is chosen
on the calibration period, never on the test period.

Run after the models:
    py -3.12 -m valuation_monitor.modelling        # trains, then writes this report
    py -3.12 -m valuation_monitor.model_report     # report only, from saved predictions
"""

from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from valuation_monitor.config import PROJECT_ROOT, load_config  # noqa: E402
from valuation_monitor.db import connect  # noqa: E402
from valuation_monitor.validation import accuracy_metrics, bootstrap_comparison  # noqa: E402

BLUE, ORANGE, GREEN = "#2A78D6", "#EB6834", "#1BAF7A"  # colour-blind-checked (dashboards theme)
INK, MUTED = "#13212A", "#4B5B64"
TYPE_NAMES = {"D": "Detached", "S": "Semi-detached", "T": "Terraced", "F": "Flat/maisonette"}
NAMES = {"baseline": "Baseline", "lightgbm": "LightGBM", "catboost": "CatBoost"}
METRIC_NAMES = {"mdape": "MdAPE", "ppe10": "PPE10", "ppe20": "PPE20", "bias": "Bias"}


def _table(headers: list[str], rows: list[tuple]) -> str:
    rule = ["---"] + ["---:"] * (len(headers) - 1)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(rule) + " |"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def _ci(row) -> str:
    return f"{row['value']:.1%} ({row['ci_lower']:.1%} to {row['ci_upper']:.1%})"


def _diff(row) -> str:
    sign = "+" if row["value"] >= 0 else "−"
    lo, hi = row["ci_lower"] * 100, row["ci_upper"] * 100
    return f"{sign}{abs(row['value']) * 100:.1f} pts ({lo:+.1f} to {hi:+.1f})"


def load_results(con) -> pd.DataFrame:
    return con.execute(
        """
        SELECT p.transaction_id, p.split, p.fold, p.estimator, p.estimate, m.price, m.period,
               m.property_type, m.lad_code, a.lad_name
        FROM model_predictions AS p
        JOIN model_input AS m USING (transaction_id)
        JOIN study_area AS a ON m.lad_code = a.lad_code
        """
    ).df()


def _wide(df: pd.DataFrame) -> pd.DataFrame:
    """One row per sale, one estimate column per estimator (paired by transaction)."""
    keys = ["transaction_id", "price", "property_type", "lad_name"]
    return df.pivot(index=keys, columns="estimator", values="estimate").reset_index()


def _compare(wide: pd.DataFrame, estimators: list[str], n_resamples: int) -> pd.DataFrame:
    return bootstrap_comparison(
        wide["price"].to_numpy(),
        {e: wide[e].to_numpy() for e in estimators},
        reference="baseline",
        n_resamples=n_resamples,
    ).set_index(["estimator", "metric"])


def collect(df: pd.DataFrame, n_resamples: int) -> dict:
    time_split = df[df["split"] == "time"]
    calibration = time_split[time_split["period"] == "calibration"]
    selection = {
        e: accuracy_metrics(g["price"], g["estimate"])["mdape"]
        for e, g in calibration.groupby("estimator")
        if e != "baseline"
    }
    selected = min(selection, key=selection.get)
    models = [e for e in NAMES if e != "baseline"]

    test = _wide(time_split[time_split["period"] == "test"])
    m = {
        "selected": selected,
        "selection": selection,
        "test_n": len(test),
        "overall": _compare(test, ["baseline", *models], n_resamples),
        "by_area": {
            name: _compare(group, ["baseline", selected], n_resamples)
            for name, group in test.groupby("lad_name")
        },
        "by_type": {
            code: _compare(group, ["baseline", selected], n_resamples)
            for code, group in test.groupby("property_type")
        },
    }
    holdout = df[df["split"] == "la_holdout"]
    m["holdout"] = {
        name: _compare(_wide(group), ["baseline", *models], n_resamples)
        for name, group in holdout.groupby("lad_name")
    }
    m["holdout_pooled"] = _compare(
        pd.concat(_wide(g) for _, g in holdout.groupby("fold")),
        ["baseline", *models],
        n_resamples,
    )
    return m


def _charts(m: dict, figures) -> list[str]:
    figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    selected = m["selected"]

    # Figure 3: MdAPE by local authority for the baseline, the model, and the model on an
    # unseen area, with 95% intervals.
    areas = sorted(m["by_area"], key=lambda a: m["by_area"][a].loc[(selected, "mdape"), "value"])
    series = [
        ("Baseline", ORANGE, [m["by_area"][a].loc[("baseline", "mdape")] for a in areas]),
        (
            f"{NAMES[selected]}, time split",
            BLUE,
            [m["by_area"][a].loc[(selected, "mdape")] for a in areas],
        ),
        (
            f"{NAMES[selected]}, area held out",
            GREEN,
            [m["holdout"][a].loc[(selected, "mdape")] for a in areas],
        ),
    ]
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    y = np.arange(len(areas))
    height = 0.26
    for i, (label, colour, rows) in enumerate(series):
        values = np.array([r["value"] for r in rows])
        errors = np.array([[r["value"] - r["ci_lower"], r["ci_upper"] - r["value"]] for r in rows])
        ax.barh(
            y + (1 - i) * height,
            values,
            height,
            color=colour,
            label=label,
            xerr=errors.T,
            error_kw={"ecolor": INK, "elinewidth": 0.8, "capsize": 2},
        )
    ax.set_yticks(y, areas)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Median absolute percentage error, test months (lower is better)", color=MUTED)
    ax.set_title("Valuation error by local authority, Sep 2025 to Aug 2026", loc="left", color=INK)
    ax.legend(frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=MUTED)
    fig.tight_layout()
    first = "03_mdape_by_area.png"
    fig.savefig(figures / first, dpi=160)
    plt.close(fig)

    # Figure 4: share of estimates within 10% by property type.
    codes = [c for c in TYPE_NAMES if c in m["by_type"]]
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    x = np.arange(len(codes))
    width = 0.38
    for i, (estimator, colour) in enumerate([("baseline", ORANGE), (selected, BLUE)]):
        rows = [m["by_type"][c].loc[(estimator, "ppe10")] for c in codes]
        values = np.array([r["value"] for r in rows])
        errors = np.array([[r["value"] - r["ci_lower"], r["ci_upper"] - r["value"]] for r in rows])
        bars = ax.bar(
            x + (i - 0.5) * width,
            values,
            width,
            color=colour,
            label=NAMES[estimator],
            yerr=errors.T,
            error_kw={"ecolor": INK, "elinewidth": 0.8, "capsize": 2},
        )
        for bar, value in zip(bars, values, strict=True):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.03,
                f"{value:.0%}",
                ha="center",
                color=INK,
                fontsize=9,
            )
    ax.set_xticks(x, [TYPE_NAMES[c] for c in codes])
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_ylabel("Estimates within 10% of price", color=MUTED)
    ax.set_title("Share of valuations within 10% (PPE10), test months", loc="left", color=INK)
    ax.legend(frameon=False, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=MUTED)
    fig.tight_layout()
    second = "04_ppe10_by_property_type.png"
    fig.savefig(figures / second, dpi=160)
    plt.close(fig)
    return [first, second]


def _group_table(groups: dict, selected: str, label) -> str:
    rows = []
    for key, t in groups.items():
        rows.append(
            (
                label(key),
                f"{int(t.loc[('baseline', 'mdape'), 'n']):,}",
                _ci(t.loc[("baseline", "mdape")]),
                _ci(t.loc[(selected, "mdape")]),
                _ci(t.loc[("baseline", "ppe10")]),
                _ci(t.loc[(selected, "ppe10")]),
            )
        )
    model = NAMES[selected]
    headers = [
        "",
        "Test sales",
        "Baseline MdAPE",
        f"{model} MdAPE",
        "Baseline PPE10",
        f"{model} PPE10",
    ]
    return _table(headers, rows)


def render(m: dict, charts: list[str], n_resamples: int) -> str:
    sel, overall = m["selected"], m["overall"]
    model = NAMES[sel]
    models = [e for e in NAMES if e != "baseline"]
    o = lambda e, k: overall.loc[(e, k)]  # noqa: E731
    pooled = m["holdout_pooled"]
    lines = [
        "# Model performance: baseline against LightGBM and CatBoost",
        "",
        f"_Generated {date.today():%d %B %Y} by `py -3.12 -m valuation_monitor.modelling`. "
        "Aggregated figures only; no addresses. Periods: decision D-020; metrics: D-021; "
        f"intervals: percentile bootstrap over sales, {n_resamples:,} resamples._",
        "",
        "## Headline",
        f"- **Test period (Sep 2025 to Aug 2026, {m['test_n']:,} matched sales never used in "
        f"training):** {model} has a median absolute error of **{o(sel, 'mdape')['value']:.1%}** "
        f"against **{o('baseline', 'mdape')['value']:.1%}** for the HPI-indexed district median. "
        f"It values **{o(sel, 'ppe10')['value']:.1%}** of homes within 10% of the price, against "
        f"{o('baseline', 'ppe10')['value']:.1%}.",
        f"- **Unseen areas:** trained on six local authorities and tested on the seventh, "
        f"{model} reaches a pooled MdAPE of **{pooled.loc[(sel, 'mdape'), 'value']:.1%}** "
        f"(baseline {pooled.loc[('baseline', 'mdape'), 'value']:.1%}).",
        f"- **Model choice:** {model} is taken forward to the conformal ranges in Week 3 "
        "because it had the lower MdAPE on the calibration period ("
        + ", ".join(f"{NAMES[e]} {v:.2%}" for e, v in m["selection"].items())
        + "). The test period played no part in the choice.",
        "",
        "## Time split: test period",
        "Point estimate with 95% confidence interval. MdAPE: lower is better. PPE10 and PPE20: "
        "higher is better. Bias: median percentage error, where positive means over-valuation.",
        "",
        _table(
            ["Estimator", *METRIC_NAMES.values()],
            [(NAMES[e], *(_ci(o(e, k)) for k in METRIC_NAMES)) for e in NAMES],
        ),
        "",
        "Paired difference from the baseline (same bootstrap resamples):",
        "",
        _table(
            ["Model", *(f"{v} change" for v in METRIC_NAMES.values())],
            [(NAMES[e], *(_diff(o(f"{e} - baseline", k)) for k in METRIC_NAMES)) for e in models],
        ),
        "",
        f"![MdAPE by local authority](figures/{charts[0]})",
        "",
        "## By local authority (time split, test period)",
        _group_table(m["by_area"], sel, lambda k: k),
        "",
        "## By property type (time split, test period)",
        _group_table(m["by_type"], sel, lambda k: TYPE_NAMES[k]),
        "",
        f"![PPE10 by property type](figures/{charts[1]})",
        "",
        "## Local-authority holdout: does it work in an area it has never seen?",
        "Each row: models trained on the other six local authorities (training period), tested "
        "on this one (test period). The baseline needs no training, so it is the same as in the "
        "time split. MdAPE with 95% confidence interval.",
        "",
        _table(
            [
                "Held-out area",
                "Test sales",
                *(NAMES[e] for e in NAMES),
                f"{model}: change from time split",
            ],
            [
                (
                    area,
                    f"{int(t.loc[('baseline', 'mdape'), 'n']):,}",
                    *(_ci(t.loc[(e, "mdape")]) for e in NAMES),
                    f"{(t.loc[(sel, 'mdape'), 'value'] - m['by_area'][area].loc[(sel, 'mdape'), 'value']) * 100:+.1f} pts",  # noqa: E501
                )
                for area, t in m["holdout"].items()
            ]
            + [
                (
                    "**All areas pooled**",
                    f"{int(pooled.loc[('baseline', 'mdape'), 'n']):,}",
                    *(_ci(pooled.loc[(e, "mdape")]) for e in NAMES),
                    "",
                )
            ],
        ),
        "",
        "## Method notes and limitations",
        "- **What is modelled:** matched Category A sales only. Unmatched sales, which include "
        "more high-value flats (see `match_quality.md`), are excluded, so accuracy on them is "
        "unknown.",
        "- **Information cut-off (decision D-022):** every feature, and the baseline, uses only "
        "sales completed and HPI months published before the first day of the month three "
        "months ahead of the sale. Tests in `tests/test_features.py` check this.",
        "- **Target (decision D-022):** the models predict ln(price ÷ baseline), so the estimate "
        "is the baseline × the predicted ratio. The models refine the baseline rather than "
        "replace it.",
        "- **Area held out:** the local-authority code is not a feature. In the holdout, the "
        "held-out area's own public sales history still feeds its local price features, as it "
        "would in practice; only its sales are absent from model training.",
        "- **Tuning:** hyperparameters are sensible defaults with early stopping on the last "
        "three training months, not a tuned search. The comparison is therefore conservative "
        "for the models.",
        "- **Truth:** the sale price is treated as the true value. Some sales are not at market "
        "value even within Category A.",
        "",
    ]
    return "\n".join(lines)


def write_model_report(config: dict) -> None:
    n_resamples = config["validation"]["bootstrap_resamples"]
    with connect(config, read_only=True) as con:
        df = load_results(con)
    m = collect(df, n_resamples)
    charts = _charts(m, PROJECT_ROOT / config["paths"]["figures"])
    text = render(m, charts, n_resamples)
    target = PROJECT_ROOT / "reports" / "model_performance.md"
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"  wrote reports/model_performance.md and {', '.join(charts)}")


if __name__ == "__main__":
    write_model_report(load_config())
