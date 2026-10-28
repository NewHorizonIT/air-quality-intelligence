"""
Build feature matrix for PM2.5 next-day prediction per ADR-003.

Pipeline:
    1.  Filter PM2.5, dedup per (date, location_name), sort
    2.  Target: pm25 shifted -1 per station
    3.  Lag features: pm25 lag 1/2/3/7
    4.  Rolling features: mean 7/14/30d, std 7/14d  ← shift(1) first to prevent leakage
    5.  Cyclical temporal: month sin/cos, DOW sin/cos
    6.  Season dummies (autumn = baseline, dropped)
    7.  Merge weather on (date, location_name)
    8.  Industrial features per station (static, Haversine)
    9.  Drop NaN rows (target + rolling warmup)
    10. Temporal split → train / val / test

Usage:
    python -m src.features.build_features

Input:
    data/cleaned/air_quality.parquet
    data/external/weather.parquet
    data/external/industrial.parquet

Output:
    data/features/train.parquet
    data/features/val.parquet
    data/features/test.parquet
"""
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT         = Path(__file__).parents[2]
CLEANED_DIR  = ROOT / "data" / "cleaned"
EXTERNAL_DIR = ROOT / "data" / "external"
FEATURES_DIR = ROOT / "data" / "features"

TRAIN_END = pd.Timestamp("2025-06-30")
VAL_END   = pd.Timestamp("2025-09-30")

WEATHER_COLS = [
    "temperature", "wind_speed", "wind_direction",
    "precipitation", "humidity", "et0",
]

# Explicit declaration — never derive feature list by column exclusion
FEATURE_COLS = [
    # Temporal — lag
    "pm25_lag1", "pm25_lag2", "pm25_lag3", "pm25_lag7",
    # Temporal — rolling
    "pm25_roll7_mean", "pm25_roll14_mean", "pm25_roll30_mean",
    "pm25_roll7_std",  "pm25_roll14_std",
    # Cyclical
    "month_sin", "month_cos", "dow_sin", "dow_cos",
    # Season dummies (autumn = baseline, excluded)
    "season_winter", "season_spring", "season_monsoon",
    # Weather
    "temperature", "wind_speed", "wind_direction",
    "precipitation", "humidity", "et0",
    # Industrial
    "dist_nearest_plant_km", "capacity_weighted_dist", "n_plants_50km",
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    )
    return float(2 * R * np.arcsin(np.sqrt(a)))


def get_season(month: int) -> str:
    if month in [12, 1, 2]:    return "winter"
    if month in [3, 4, 5]:     return "spring"
    if month in [6, 7, 8, 9]:  return "monsoon"
    return "autumn"


def build_industrial_features(
    stations: pd.DataFrame,
    plants: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute 3 static industrial proximity features per station.

    - dist_nearest_plant_km  : distance to closest plant
    - capacity_weighted_dist : Σ capacity_mw / dist_km²  (inverse-square law)
    - n_plants_50km          : count of plants within 50 km
    """
    records = []
    for _, st in stations.iterrows():
        dists = plants.apply(
            lambda p: haversine_km(
                st["latitude"], st["longitude"],
                p["latitude"], p["longitude"],
            ),
            axis=1,
        ).clip(lower=0.1)  # prevent zero-division for co-located station+plant

        records.append({
            "location_name":         st["location_name"],
            "dist_nearest_plant_km": float(dists.min()),
            "capacity_weighted_dist": float((plants["capacity_mw"] / dists ** 2).sum()),
            "n_plants_50km":         int((dists <= 50).sum()),
        })
    return pd.DataFrame(records)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load ──────────────────────────────────────────────────────────────────
    logger.info("Loading cleaned data...")
    aq      = pd.read_parquet(CLEANED_DIR / "air_quality.parquet")
    weather = pd.read_parquet(EXTERNAL_DIR / "weather.parquet")
    plants  = pd.read_parquet(EXTERNAL_DIR / "industrial.parquet")

    # Rename legacy column from parquets fetched before the et0 rename
    if "boundary_layer_height" in weather.columns and "et0" not in weather.columns:
        weather = weather.rename(columns={"boundary_layer_height": "et0"})
        logger.info("Renamed weather column boundary_layer_height → et0")

    # ── Step 1: PM2.5, dedup per (date, location_name), sort ─────────────────
    df = (
        aq[aq["parameter"] == "pm25"]
        [["date", "location_name", "latitude", "longitude", "value"]]
        .rename(columns={"value": "pm25"})
        .copy()
    )
    df["date"] = pd.to_datetime(df["date"])

    # Multiple sensors at same station → take mean (clean_air_quality groups by
    # location_id, so duplicates per location_name are possible)
    n_before = len(df)
    df = (
        df.groupby(["date", "location_name"], as_index=False)
        .agg(pm25=("pm25", "mean"), latitude=("latitude", "first"), longitude=("longitude", "first"))
    )
    if len(df) < n_before:
        logger.info(f"Deduped {n_before - len(df)} duplicate (date, location_name) pm25 rows")

    df = df.sort_values(["location_name", "date"]).reset_index(drop=True)
    logger.info(f"PM2.5 rows: {len(df):,}  stations: {df['location_name'].nunique()}")

    # ── Step 2: Target ────────────────────────────────────────────────────────
    df["pm25_target"] = df.groupby("location_name")["pm25"].shift(-1)

    # ── Step 3: Lag features ──────────────────────────────────────────────────
    for lag in [1, 2, 3, 7]:
        df[f"pm25_lag{lag}"] = df.groupby("location_name")["pm25"].shift(lag)

    # ── Step 4: Rolling features (shift BEFORE rolling → no leakage) ──────────
    grp = df.groupby("location_name")["pm25"]

    for window in [7, 14, 30]:
        df[f"pm25_roll{window}_mean"] = grp.transform(
            lambda x, w=window: x.shift(1).rolling(w, min_periods=w // 2).mean()
        )
    for window in [7, 14]:
        df[f"pm25_roll{window}_std"] = grp.transform(
            lambda x, w=window: x.shift(1).rolling(w, min_periods=w // 2).std()
        )

    # ── Step 5: Cyclical temporal ─────────────────────────────────────────────
    df["month_sin"] = np.sin(2 * np.pi * df["date"].dt.month / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["date"].dt.month / 12)
    df["dow_sin"]   = np.sin(2 * np.pi * df["date"].dt.dayofweek / 7)
    df["dow_cos"]   = np.cos(2 * np.pi * df["date"].dt.dayofweek / 7)

    # ── Step 6: Season dummies (autumn = baseline) ────────────────────────────
    df["season_winter"]  = df["date"].dt.month.map(get_season) == "winter"
    df["season_spring"]  = df["date"].dt.month.map(get_season) == "spring"
    df["season_monsoon"] = df["date"].dt.month.map(get_season) == "monsoon"

    # ── Step 7: Merge weather ─────────────────────────────────────────────────
    weather["date"] = pd.to_datetime(weather["date"])
    df = df.merge(
        weather[["date", "location_name"] + WEATHER_COLS],
        on=["date", "location_name"],
        how="left",
    )
    n_missing = df["temperature"].isna().sum()
    logger.info(
        f"Weather merge: {len(df) - n_missing:,} matched, "
        f"{n_missing} unmatched ({n_missing / len(df) * 100:.1f}%)"
    )

    # ── Step 8: Industrial features (static per station) ─────────────────────
    stations = df[["location_name", "latitude", "longitude"]].drop_duplicates("location_name")
    ind_feats = build_industrial_features(stations, plants)
    df = df.merge(ind_feats, on="location_name", how="left")
    logger.info(
        f"Industrial: dist_nearest min={ind_feats['dist_nearest_plant_km'].min():.1f}km "
        f"max={ind_feats['dist_nearest_plant_km'].max():.1f}km"
    )

    # ── Step 9: Drop NaN rows ─────────────────────────────────────────────────
    before = len(df)
    df = df.dropna(subset=["pm25_target"])
    logger.info(f"Dropped {before - len(df)} rows: NaN target (last day per station)")

    before = len(df)
    df = df.dropna(subset=FEATURE_COLS)
    logger.info(f"Dropped {before - len(df)} rows: NaN features (rolling warmup)")

    logger.info(f"Features ({len(FEATURE_COLS)}): {FEATURE_COLS}")
    logger.info(f"Final dataset: {len(df):,} rows")

    # ── Step 10: Temporal split ───────────────────────────────────────────────
    train = df[df["date"] <= TRAIN_END].copy()
    val   = df[(df["date"] > TRAIN_END) & (df["date"] <= VAL_END)].copy()
    test  = df[df["date"] > VAL_END].copy()

    for name, split in [("Train", train), ("Val", val), ("Test", test)]:
        if split.empty:
            logger.warning(f"{name:5s}: 0 rows — check TRAIN_END/VAL_END constants")
        else:
            logger.info(
                f"{name:5s}: {len(split):,} rows  "
                f"{split['date'].min().date()} -> {split['date'].max().date()}"
            )

    # ── Save ──────────────────────────────────────────────────────────────────
    train.to_parquet(FEATURES_DIR / "train.parquet", index=False)
    val.to_parquet(FEATURES_DIR / "val.parquet", index=False)
    test.to_parquet(FEATURES_DIR / "test.parquet", index=False)
    logger.info("Saved train/val/test.parquet -> data/features/")


if __name__ == "__main__":
    main()
