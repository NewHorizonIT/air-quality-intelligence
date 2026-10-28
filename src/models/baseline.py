"""
Phase 4 baselines: Persistence + Ridge regression.

Persistence  predict tomorrow = today (pm25_lag1) — zero params
Ridge        StandardScaler + Ridge(alpha=1.0) on all 25 FEATURE_COLS

Output:
    models/ridge.pkl
"""
import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT         = Path(__file__).parents[2]
FEATURES_DIR = ROOT / "data" / "features"
MODELS_DIR   = ROOT / "models"

FEATURE_COLS = [
    "pm25_lag1", "pm25_lag2", "pm25_lag3", "pm25_lag7",
    "pm25_roll7_mean", "pm25_roll14_mean", "pm25_roll30_mean",
    "pm25_roll7_std", "pm25_roll14_std",
    "month_sin", "month_cos", "dow_sin", "dow_cos",
    "season_winter", "season_spring", "season_monsoon",
    "temperature", "wind_speed", "wind_direction",
    "precipitation", "humidity", "et0",
    "dist_nearest_plant_km", "capacity_weighted_dist", "n_plants_50km",
]


def report(y_true, y_pred, name: str) -> dict:
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2   = r2_score(y_true, y_pred)
    logger.info(f"  {name:22s}  MAE={mae:.2f}  RMSE={rmse:.2f}  R²={r2:.3f}")
    return {"model": name, "mae": mae, "rmse": rmse, "r2": r2}


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    train = pd.read_parquet(FEATURES_DIR / "train.parquet")
    val   = pd.read_parquet(FEATURES_DIR / "val.parquet")
    test  = pd.read_parquet(FEATURES_DIR / "test.parquet")
    logger.info(f"Train {len(train):,} | Val {len(val):,} | Test {len(test):,}")

    X_train = train[FEATURE_COLS]
    y_train = train["pm25_target"]
    X_val   = val[FEATURE_COLS]
    y_val   = val["pm25_target"]
    X_test  = test[FEATURE_COLS]
    y_test  = test["pm25_target"]

    logger.info("\n── Val ─────────────────────────────────────────────────")
    report(y_val,  val["pm25_lag1"],  "Persistence")

    ridge = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
    ridge.fit(X_train, y_train)
    report(y_val, ridge.predict(X_val), "Ridge")

    logger.info("\n── Test ────────────────────────────────────────────────")
    report(y_test, test["pm25_lag1"],       "Persistence")
    report(y_test, ridge.predict(X_test),   "Ridge")

    with open(MODELS_DIR / "ridge.pkl", "wb") as f:
        pickle.dump(ridge, f)
    logger.info("\n✓ Saved models/ridge.pkl")


if __name__ == "__main__":
    main()
