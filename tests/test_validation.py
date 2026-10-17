"""Tests for the accuracy metrics, bootstrap and validation splits in validation.py."""

import numpy as np
import pandas as pd
import pytest

from valuation_monitor.validation import (
    accuracy_metrics,
    bootstrap_comparison,
    la_holdout_splits,
    time_split,
)

PERIODS = {
    "train_start": "2021-01-01",
    "calibration_start": "2025-03-01",
    "test_start": "2025-09-01",
    "test_end": "2026-08-31",
}
CONFIG = {"validation": {"periods": PERIODS, "early_stopping_months": 3}}


def test_accuracy_metrics_on_known_errors():
    price = np.array([100.0, 100.0, 100.0, 100.0])
    estimate = np.array([105.0, 85.0, 130.0, 100.0])  # errors +5%, -15%, +30%, 0%
    metrics = accuracy_metrics(price, estimate)
    assert metrics["n"] == 4
    assert metrics["mdape"] == pytest.approx(0.10)  # median of 0.05, 0.15, 0.30, 0
    assert metrics["ppe10"] == pytest.approx(0.50)
    assert metrics["ppe20"] == pytest.approx(0.75)
    # Percentage error is (estimate - price) / price: positive means over-valuation.
    assert metrics["bias"] == pytest.approx(0.025)


def test_bootstrap_interval_contains_point_and_difference_is_paired():
    rng = np.random.default_rng(0)
    price = rng.uniform(1e5, 5e5, 2000)
    good = price * (1 + rng.normal(0, 0.05, price.size))
    bad = price * (1 + rng.normal(0, 0.20, price.size))
    table = bootstrap_comparison(
        price, {"baseline": bad, "model": good}, reference="baseline", n_resamples=200, seed=1
    )
    row = table.set_index(["estimator", "metric"]).loc[("model", "mdape")]
    assert row["ci_lower"] <= row["value"] <= row["ci_upper"]
    diff = table.set_index(["estimator", "metric"]).loc[("model - baseline", "mdape")]
    assert diff["ci_upper"] < 0  # clearly better than the reference


def _sales():
    months = pd.date_range("2020-01-01", "2026-08-01", freq="MS")
    rows = [(m, la) for m in months for la in ["A", "B", "C"]]
    df = pd.DataFrame(rows, columns=["sale_date", "lad_code"])
    df["period"] = np.select(
        [
            df["sale_date"] < "2021-01-01",
            df["sale_date"] < "2025-03-01",
            df["sale_date"] < "2025-09-01",
        ],
        ["history", "train", "calibration"],
        default="test",
    )
    return df


def test_time_split_holds_out_last_training_months_for_early_stopping():
    df = _sales()
    split = time_split(df, CONFIG)
    fit_dates = df.loc[split["fit"], "sale_date"]
    stop_dates = df.loc[split["early_stop"], "sale_date"]
    assert fit_dates.min() == pd.Timestamp("2021-01-01")
    assert fit_dates.max() == pd.Timestamp("2024-11-01")
    assert stop_dates.min() == pd.Timestamp("2024-12-01")
    assert stop_dates.max() == pd.Timestamp("2025-02-01")
    assert not (split["fit"] & split["early_stop"]).any()
    assert (df.loc[split["test"], "period"] == "test").all()
    assert (df.loc[split["calibration"], "period"] == "calibration").all()


def test_la_holdout_never_trains_on_the_held_out_area():
    df = _sales()
    folds = list(la_holdout_splits(df, CONFIG))
    assert [fold["held_out"] for fold in folds] == ["A", "B", "C"]
    for fold in folds:
        held_out = df["lad_code"] == fold["held_out"]
        assert not (fold["fit"] & held_out).any()
        assert not (fold["early_stop"] & held_out).any()
        assert (fold["test"] <= held_out).all()
        assert (df.loc[fold["test"], "period"] == "test").all()
