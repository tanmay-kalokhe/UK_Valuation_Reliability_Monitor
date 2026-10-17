"""Validation splits and accuracy metrics (Week 2).

Splits (decision D-020):
- time split: fit on the training period, minus its last few months, which are held out for
  early stopping only; calibration and test periods are never used for fitting;
- local-authority holdout: for each area in turn, fit on the other areas' training period and
  test on the held-out area's test period.

Metrics (decision D-021), with percentage error = (estimate - price) / price:
- MdAPE: median absolute percentage error;
- PPE10 and PPE20: share of estimates within 10% and 20% of the price;
- bias: median percentage error (positive means over-valuation).

Confidence intervals come from a percentile bootstrap over sales. Differences between an
estimator and the reference (the baseline) use the same resamples for both, so they are
paired.
"""

from collections.abc import Iterator

import numpy as np
import pandas as pd

METRICS = ["mdape", "ppe10", "ppe20", "bias"]


def accuracy_metrics(price: np.ndarray, estimate: np.ndarray) -> dict[str, float]:
    """Point metrics for one set of estimates."""
    error = (np.asarray(estimate, float) - np.asarray(price, float)) / np.asarray(price, float)
    absolute = np.abs(error)
    return {
        "n": int(error.size),
        "mdape": float(np.median(absolute)),
        "ppe10": float(np.mean(absolute <= 0.10)),
        "ppe20": float(np.mean(absolute <= 0.20)),
        "bias": float(np.median(error)),
    }


def _resampled_metrics(error: np.ndarray, index: np.ndarray) -> dict[str, np.ndarray]:
    """Metric values for each bootstrap resample (rows of index)."""
    sampled = error[index]
    absolute = np.abs(sampled)
    return {
        "mdape": np.median(absolute, axis=1),
        "ppe10": np.mean(absolute <= 0.10, axis=1),
        "ppe20": np.mean(absolute <= 0.20, axis=1),
        "bias": np.median(sampled, axis=1),
    }


def bootstrap_comparison(
    price: np.ndarray,
    estimates: dict[str, np.ndarray],
    reference: str,
    n_resamples: int = 1000,
    seed: int = 42,
    batch: int = 100,
) -> pd.DataFrame:
    """Metrics with 95% percentile intervals for each estimator, plus paired differences.

    Returns one row per (estimator, metric). Rows named "<estimator> - <reference>" hold the
    difference from the reference: for MdAPE and |bias| lower is better, for PPE higher is.
    """
    price = np.asarray(price, float)
    errors = {name: (np.asarray(est, float) - price) / price for name, est in estimates.items()}
    rng = np.random.default_rng(seed)
    draws: dict[str, dict[str, list]] = {name: {m: [] for m in METRICS} for name in errors}
    for start in range(0, n_resamples, batch):
        size = min(batch, n_resamples - start)
        index = rng.integers(0, price.size, size=(size, price.size))
        for name, error in errors.items():
            for metric, values in _resampled_metrics(error, index).items():
                draws[name][metric].append(values)
    samples = {
        name: {m: np.concatenate(v) for m, v in by_metric.items()}
        for name, by_metric in draws.items()
    }

    rows = []
    for name, error in errors.items():
        point = accuracy_metrics(price, price * (1 + error))
        for metric in METRICS:
            lower, upper = np.percentile(samples[name][metric], [2.5, 97.5])
            rows.append((name, metric, point[metric], lower, upper, point["n"]))
        if name == reference:
            continue
        ref_point = accuracy_metrics(price, price * (1 + errors[reference]))
        for metric in METRICS:
            diff = samples[name][metric] - samples[reference][metric]
            lower, upper = np.percentile(diff, [2.5, 97.5])
            value = point[metric] - ref_point[metric]
            rows.append((f"{name} - {reference}", metric, value, lower, upper, point["n"]))
    return pd.DataFrame(rows, columns=["estimator", "metric", "value", "ci_lower", "ci_upper", "n"])


def _early_stop_start(config: dict) -> pd.Timestamp:
    periods = config["validation"]["periods"]
    months = config["validation"]["early_stopping_months"]
    return pd.Timestamp(periods["calibration_start"]) - pd.DateOffset(months=months)


def time_split(df: pd.DataFrame, config: dict) -> dict[str, pd.Series]:
    """Boolean masks for the time-based split."""
    early_stop_start = _early_stop_start(config)
    dates = pd.to_datetime(df["sale_date"])
    train = df["period"] == "train"
    return {
        "fit": train & (dates < early_stop_start),
        "early_stop": train & (dates >= early_stop_start),
        "calibration": df["period"] == "calibration",
        "test": df["period"] == "test",
    }


def la_holdout_splits(df: pd.DataFrame, config: dict) -> Iterator[dict]:
    """One fold per local authority: fit and early-stop on the others, test on it."""
    base = time_split(df, config)
    for lad_code in sorted(df["lad_code"].unique()):
        held_out = df["lad_code"] == lad_code
        yield {
            "held_out": lad_code,
            "fit": base["fit"] & ~held_out,
            "early_stop": base["early_stop"] & ~held_out,
            "test": base["test"] & held_out,
        }
