"""
Phase 4 LightGBM training — 3 ablation experiments + Optuna tuning.

Exp1  temporal only              (16 features)
Exp2  temporal + weather         (22 features)
Exp3  temporal + weather + industry (25 features)  ← Optuna 100 trials

Output:
    models/lgbm_exp1.pkl
    models/lgbm_exp2.pkl
    models/lgbm_exp3_best.pkl
    models/optuna_exp3.pkl        (study — for notebook inspection)
"""
import logging
import pickle
from pathlib import Path

import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
optuna.logging.set_verbosity(optuna.logging.WARNING)

ROOT         = Path(__file__).parents[2]
FEATURES_DIR = ROOT / "data" / "features"
MODELS_DIR   = ROOT / "models"

TEMPORAL_FEATURES = [
    "pm25_lag1", "pm25_lag2", "pm25_lag3", "pm25_lag7",
    "pm25_roll7_mean", "pm25_roll14_mean", "pm25_roll30_mean",
    "pm25_roll7_std",  "pm25_roll14_std",
    "month_sin", "month_cos", "dow_sin", "dow_cos",
    "season_winter", "season_spring", "season_monsoon",
]  # 16

WEATHER_FEATURES = [
    "temperature", "wind_speed", "wind_direction",
    "precipitation", "humidity", "et0",
]  # 6

INDUSTRIAL_FEATURES = [
    "dist_nearest_plant_km", "capacity_weighted_dist", "n_plants_50km",
]  # 3

EXPERIMENTS: dict[str, list[str]] = {
    "exp1": TEMPORAL_FEATURES,
    "exp2": TEMPORAL_FEATURES + WEATHER_FEATURES,
    "exp3": TEMPORAL_FEATURES + WEATHER_FEATURES + INDUSTRIAL_FEATURES,
}

DEFAULT_PARAMS = {
    "objective":     "regression_l1",   # optimise MAE directly
    "metric":        "mae",
    "n_estimators":  500,
    "learning_rate": 0.05,
    "num_leaves":    63,
    "random_state":  42,
    "n_jobs":        -1,
    "verbose":       -1,
}

EARLY_STOP_ROUNDS = 50


def report(y_true, y_pred, name: str) -> dict:
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2   = r2_score(y_true, y_pred)
    logger.info(f"  {name:30s}  MAE={mae:.2f}  RMSE={rmse:.2f}  R²={r2:.3f}")
    return {"model": name, "mae": mae, "rmse": rmse, "r2": r2}


def train_default(
    exp_name: str,
    features: list[str],
    X_train: pd.DataFrame, y_train: pd.Series,
    X_val:   pd.DataFrame, y_val:   pd.Series,
) -> lgb.LGBMRegressor:
    logger.info(f"\n── {exp_name.upper()} ({len(features)} features, default params) ──")

    model = lgb.LGBMRegressor(**DEFAULT_PARAMS)
    model.fit(
        X_train[features], y_train,
        eval_X=[X_val[features]], eval_y=[y_val],
        callbacks=[
            lgb.early_stopping(stopping_rounds=EARLY_STOP_ROUNDS, verbose=False),
            lgb.log_evaluation(period=100),
        ],
    )
    logger.info(f"  Best iteration: {model.best_iteration_}")
    report(y_val, model.predict(X_val[features]), f"{exp_name} val")
    return model


def tune_exp3(
    features: list[str],
    X_train: pd.DataFrame, y_train: pd.Series,
    X_val:   pd.DataFrame, y_val:   pd.Series,
    n_trials: int = 100,
) -> lgb.LGBMRegressor:
    logger.info(f"\n── EXP3 Optuna ({n_trials} trials) ──")

    def objective(trial: optuna.Trial) -> float:
        params = {
            "objective":         "regression_l1",
            "metric":            "mae",
            "n_estimators":      trial.suggest_int("n_estimators", 200, 1000),
            "num_leaves":        trial.suggest_int("num_leaves", 31, 255),
            "max_depth":         trial.suggest_int("max_depth", 3, 12),
            "learning_rate":     trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 100),
            "subsample":         trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree":  trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_alpha":         trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True),
            "reg_lambda":        trial.suggest_float("reg_lambda", 1e-4, 10.0, log=True),
            "random_state":      42,
            "n_jobs":            -1,
            "verbose":           -1,
        }
        m = lgb.LGBMRegressor(**params)
        m.fit(
            X_train[features], y_train,
            eval_X=[X_val[features]], eval_y=[y_val],
            callbacks=[lgb.early_stopping(stopping_rounds=EARLY_STOP_ROUNDS, verbose=False)],
        )
        return float(mean_absolute_error(y_val, m.predict(X_val[features])))

    study = optuna.create_study(direction="minimize", study_name="lgbm_exp3")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    logger.info(f"  Best val MAE : {study.best_value:.3f}")
    logger.info(f"  Best params  : {study.best_params}")

    # Retrain final model with best hyperparams
    best_params = {
        "objective":    "regression_l1",
        "metric":       "mae",
        "random_state": 42,
        "n_jobs":       -1,
        "verbose":      -1,
        **study.best_params,
    }
    best_model = lgb.LGBMRegressor(**best_params)
    best_model.fit(
        X_train[features], y_train,
        eval_X=[X_val[features]], eval_y=[y_val],
        callbacks=[
            lgb.early_stopping(stopping_rounds=EARLY_STOP_ROUNDS, verbose=False),
            lgb.log_evaluation(period=100),
        ],
    )
    report(y_val, best_model.predict(X_val[features]), "exp3_best val")

    with open(MODELS_DIR / "optuna_exp3.pkl", "wb") as f:
        pickle.dump(study, f)
    logger.info("  ✓ Saved models/optuna_exp3.pkl")

    return best_model


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    train = pd.read_parquet(FEATURES_DIR / "train.parquet")
    val   = pd.read_parquet(FEATURES_DIR / "val.parquet")
    test  = pd.read_parquet(FEATURES_DIR / "test.parquet")
    logger.info(f"Train {len(train):,} | Val {len(val):,} | Test {len(test):,}")

    X_train, y_train = train, train["pm25_target"]
    X_val,   y_val   = val,   val["pm25_target"]
    X_test,  y_test  = test,  test["pm25_target"]

    # ── Default experiments ──────────────────────────────────────────────────
    m1 = train_default("exp1", EXPERIMENTS["exp1"], X_train, y_train, X_val, y_val)
    m2 = train_default("exp2", EXPERIMENTS["exp2"], X_train, y_train, X_val, y_val)

    # ── Optuna on Exp3 ───────────────────────────────────────────────────────
    m3 = tune_exp3(EXPERIMENTS["exp3"], X_train, y_train, X_val, y_val, n_trials=100)

    # ── Test set evaluation ──────────────────────────────────────────────────
    logger.info("\n── Test set ────────────────────────────────────────────")
    for name, model, feats in [
        ("exp1",     m1, EXPERIMENTS["exp1"]),
        ("exp2",     m2, EXPERIMENTS["exp2"]),
        ("exp3_best", m3, EXPERIMENTS["exp3"]),
    ]:
        report(y_test, model.predict(X_test[feats]), f"{name} test")

    # ── Save ─────────────────────────────────────────────────────────────────
    for name, model in [("lgbm_exp1", m1), ("lgbm_exp2", m2), ("lgbm_exp3_best", m3)]:
        path = MODELS_DIR / f"{name}.pkl"
        with open(path, "wb") as f:
            pickle.dump(model, f)
        logger.info(f"✓ Saved models/{name}.pkl")


if __name__ == "__main__":
    main()
