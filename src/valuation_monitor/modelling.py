"""Train and compare the valuation models (Week 2).

LightGBM and CatBoost learn log_ratio_target = ln(price) - ln(baseline): how far a home sits
above or below the HPI-indexed local median (decision D-022). The estimate is then
baseline x exp(prediction). Learning the ratio, not the price level, lets tree models follow a
moving market, which they cannot extrapolate on their own.

Both models are fitted on the time split and on each local-authority holdout fold
(validation.py), with early stopping on the last training months only. Every run is logged
to MLflow. Predictions are written to the model_predictions table for the report, the
conformal ranges (Week 3) and the Power BI export.

The local-authority code is deliberately not a feature: location enters only through
features that exist for any area (local price history and the ONS area classification), so
the holdout test is meaningful.

Usage:
    py -3.12 -m valuation_monitor.modelling
"""

import time

import catboost
import lightgbm as lgb
import mlflow
import numpy as np
import pandas as pd

from valuation_monitor.baseline import baseline_estimate
from valuation_monitor.config import load_config
from valuation_monitor.db import connect
from valuation_monitor.validation import accuracy_metrics, la_holdout_splits, time_split

TARGET = "log_ratio_target"

NUMERIC_FEATURES = [
    "floor_area",
    "habitable_rooms",
    "current_energy_efficiency",
    "construction_year",
    "floor_number",
    "extension_count",
    "open_fireplaces",
    "certificate_age_years",
    "log_baseline",
    "district_comparables",
    "district_sales",
    "msoa_sales",
    "years_since_previous_sale",
    "log_district_sqm_value_vs_baseline",
    "log_msoa_sqm_value_vs_baseline",
    "log_msoa_price_vs_baseline",
    "log_previous_price_vs_baseline",
]
BOOLEAN_FEATURES = ["is_new_build", "is_top_storey", "has_mains_gas"]
CATEGORICAL_FEATURES = [
    "property_type",
    "tenure",
    "area_classification",
    "epc_property_type",
    "built_form",
    "current_energy_rating",
    "main_fuel_group",
    "certificate_reason",
    "baseline_level",
]
FEATURES = NUMERIC_FEATURES + BOOLEAN_FEATURES + CATEGORICAL_FEATURES

RARE_CATEGORY_SHARE = 0.005  # categories rarer than this are grouped as "other"

LIGHTGBM_PARAMS = {
    "objective": "regression",
    "learning_rate": 0.05,
    "num_leaves": 63,
    "min_data_in_leaf": 50,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "lambda_l2": 1.0,
    "verbosity": -1,
}
CATBOOST_PARAMS = {
    "loss_function": "RMSE",
    "learning_rate": 0.12,
    "depth": 8,
    "l2_leaf_reg": 3.0,
    "verbose": False,
}
MAX_ROUNDS = 5000
EARLY_STOPPING_ROUNDS = 200


def load_model_input(config: dict) -> pd.DataFrame:
    """Modelled sales (all periods except history) with a baseline estimate."""
    with connect(config, read_only=True) as con:
        df = con.execute(
            "SELECT * FROM model_input WHERE period <> 'history' AND baseline_estimate IS NOT NULL "
            "ORDER BY sale_date, transaction_id"
        ).df()
    return df.reset_index(drop=True)


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature matrix: numeric as float, booleans as 0/1, categories with rare levels grouped.

    Which levels count as rare is decided on the training period only, so the test period
    cannot influence the features.
    """
    x = df[NUMERIC_FEATURES].astype(float)
    for column in BOOLEAN_FEATURES:
        x[column] = df[column].astype(float)
    in_training = df["period"] == "train"
    for column in CATEGORICAL_FEATURES:
        values = df[column].fillna("missing").astype(str)
        shares = values[in_training].value_counts(normalize=True)
        common = shares[shares >= RARE_CATEGORY_SHARE].index
        values = values.where(values.isin(common), "other")
        x[column] = pd.Categorical(values, categories=sorted(values.unique()))
    return x[FEATURES]


def fit_lightgbm(x_fit, y_fit, x_stop, y_stop, seed: int):
    model = lgb.train(
        {**LIGHTGBM_PARAMS, "seed": seed},
        lgb.Dataset(x_fit, y_fit),
        num_boost_round=MAX_ROUNDS,
        valid_sets=[lgb.Dataset(x_stop, y_stop)],
        callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False)],
    )
    return model, model.best_iteration


def _catboost_frame(x: pd.DataFrame) -> pd.DataFrame:
    out = x.copy()
    for column in CATEGORICAL_FEATURES:
        out[column] = out[column].astype(str)
    return out


def fit_catboost(x_fit, y_fit, x_stop, y_stop, seed: int):
    model = catboost.CatBoostRegressor(
        **CATBOOST_PARAMS,
        iterations=MAX_ROUNDS,
        od_type="Iter",
        od_wait=EARLY_STOPPING_ROUNDS,
        random_seed=seed,
        cat_features=CATEGORICAL_FEATURES,
        thread_count=-1,
    )
    model.fit(_catboost_frame(x_fit), y_fit, eval_set=(_catboost_frame(x_stop), y_stop))
    return model, model.get_best_iteration()


def predict_log_ratio(name: str, model, x: pd.DataFrame) -> np.ndarray:
    if name == "catboost":
        return model.predict(_catboost_frame(x))
    return model.predict(x, num_iteration=model.best_iteration)


FITTERS = {"lightgbm": fit_lightgbm, "catboost": fit_catboost}


def _fit_and_predict(name, x, y, masks, predict_on, seed):
    """Fit one model on a split and return (estimates for predict_on rows, best iteration)."""
    started = time.perf_counter()
    model, best_iteration = FITTERS[name](
        x[masks["fit"]], y[masks["fit"]], x[masks["early_stop"]], y[masks["early_stop"]], seed
    )
    log_ratio = predict_log_ratio(name, model, x[predict_on])
    return log_ratio, best_iteration, time.perf_counter() - started


def run_experiments(config: dict) -> pd.DataFrame:
    """Fit both models on every split, log to MLflow, and return all predictions."""
    seed = config["modelling"]["random_seed"]
    df = load_model_input(config)
    x = prepare_features(df)
    y = df[TARGET].to_numpy()
    baseline = baseline_estimate(df)
    price = df["price"].to_numpy(dtype=float)

    jobs = [("time", "all", time_split(df, config), ["calibration", "test"])]
    for fold in la_holdout_splits(df, config):
        jobs.append(("la_holdout", fold["held_out"], fold, ["test"]))

    mlflow.set_experiment("valuation_models")
    frames = []
    for split, fold_name, masks, scored in jobs:
        predict_on = np.logical_or.reduce([masks[s].to_numpy() for s in scored])
        test_rows = masks["test"].to_numpy()[predict_on]
        frames.append(
            pd.DataFrame(
                {
                    "transaction_id": df.loc[predict_on, "transaction_id"].to_numpy(),
                    "split": split,
                    "fold": fold_name,
                    "estimator": "baseline",
                    "estimate": baseline[predict_on],
                }
            )
        )
        for name in FITTERS:
            log_ratio, best_iteration, seconds = _fit_and_predict(
                name, x, y, masks, predict_on, seed
            )
            estimate = baseline[predict_on] * np.exp(log_ratio)
            metrics = accuracy_metrics(price[predict_on][test_rows], estimate[test_rows])
            with mlflow.start_run(run_name=f"{name}-{split}-{fold_name}"):
                mlflow.set_tags({"model": name, "split": split, "fold": fold_name})
                params = LIGHTGBM_PARAMS if name == "lightgbm" else CATBOOST_PARAMS
                mlflow.log_params({**params, "best_iteration": best_iteration, "seed": seed})
                mlflow.log_params({"n_fit": int(masks["fit"].sum()), "features": len(FEATURES)})
                mlflow.log_metrics({f"test_{k}": float(v) for k, v in metrics.items()})
                mlflow.log_metric("fit_seconds", seconds)
            print(
                f"  {name:9s} {split:10s} {fold_name:10s} iterations {best_iteration:>5} "
                f"test MdAPE {metrics['mdape']:.1%} PPE10 {metrics['ppe10']:.1%} "
                f"({seconds:.0f}s)"
            )
            frames.append(
                pd.DataFrame(
                    {
                        "transaction_id": df.loc[predict_on, "transaction_id"].to_numpy(),
                        "split": split,
                        "fold": fold_name,
                        "estimator": name,
                        "estimate": estimate,
                    }
                )
            )
    return pd.concat(frames, ignore_index=True)


def write_predictions(config: dict, predictions: pd.DataFrame) -> None:
    with connect(config) as con:
        con.register("predictions_df", predictions)
        con.execute("CREATE OR REPLACE TABLE model_predictions AS SELECT * FROM predictions_df")
    print(f"  wrote model_predictions: {len(predictions):,} rows")


def main() -> None:
    config = load_config()
    write_predictions(config, run_experiments(config))
    from valuation_monitor.model_report import write_model_report

    write_model_report(config)


if __name__ == "__main__":
    main()
