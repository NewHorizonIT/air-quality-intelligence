"""
Clean raw OpenAQ air quality data per ADR-005.

Pipeline:
    0. Drop stations with < 30 days of data
    1. Convert all units to µg/m³ BEFORE any filtering
       - O3 ppm  × 2000
       - NO2 ppb × 1.882
       - SO2 ppb × 2.619
       - CO "ppb" (mislabeled ppm) × 1145
    2. Drop value < 0
    3. Apply outlier caps
    4. Aggregate to daily mean per (location, date, parameter)
    5. Add WHO exceedance labels
    6. Cross-station suspicious flag (soft flag, no drops)

Usage:
    python -m src.processing.clean_air_quality

Input:  data/raw/delhi_raw.parquet
Output: data/cleaned/air_quality.parquet
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

ROOT = Path(__file__).parents[2]
RAW_DIR = ROOT / "data" / "raw"
CLEANED_DIR = ROOT / "data" / "cleaned"

MIN_STATION_DAYS = 30

# µg/m³ conversion factors (25°C, 1 atm)
UNIT_CONVERSIONS: list[tuple[str, str, float]] = [
    ("o3",  "ppm",  2000.0),   # 1 ppm O3  = 2000 µg/m³
    ("no2", "ppb",  1.882),    # 1 ppb NO2 = 1.882 µg/m³
    ("so2", "ppb",  2.619),    # 1 ppb SO2 = 2.619 µg/m³
    ("co",  "ppb",  1145.0),   # CO "ppb" is mislabeled ppm; 1 ppm CO = 1145 µg/m³
]

OUTLIER_CAPS = {
    "pm25": 1000.0,
    "pm10": 2000.0,
    "no2":   600.0,
    "o3":    600.0,
    "so2":   500.0,
    "co":  10000.0,
}

# WHO AQG 2021 daily guidelines (µg/m³)
WHO_THRESHOLDS = {
    "pm25":   15.0,
    "pm10":   45.0,
    "no2":    25.0,
    "o3":    100.0,
    "so2":    40.0,
    "co":   4000.0,
}

SPATIAL_THRESHOLD_KM = 5.0
RATIO_THRESHOLD = 5.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    )
    return float(2 * R * np.arcsin(np.sqrt(a)))


def find_close_pairs(df: pd.DataFrame) -> list[tuple[str, str]]:
    stations = (
        df[["location_name", "latitude", "longitude"]]
        .drop_duplicates("location_name")
        .reset_index(drop=True)
    )
    pairs = []
    for i in range(len(stations)):
        for j in range(i + 1, len(stations)):
            a, b = stations.iloc[i], stations.iloc[j]
            d = haversine_km(a["latitude"], a["longitude"], b["latitude"], b["longitude"])
            if d <= SPATIAL_THRESHOLD_KM:
                pairs.append((a["location_name"], b["location_name"]))
    return pairs


def flag_suspicious(df: pd.DataFrame, close_pairs: list[tuple[str, str]]) -> pd.Series:
    result = pd.Series(False, index=df.index)
    if not close_pairs:
        return result

    suspicious_idx: set[int] = set()
    for loc_a, loc_b in close_pairs:
        df_a = (
            df[df["location_name"] == loc_a][["date", "parameter", "value"]]
            .rename(columns={"value": "val_a"})
        )
        df_b = (
            df[df["location_name"] == loc_b][["date", "parameter", "value"]]
            .rename(columns={"value": "val_b"})
        )
        merged = df_a.merge(df_b, on=["date", "parameter"])
        if merged.empty:
            continue

        lo = merged[["val_a", "val_b"]].min(axis=1).replace(0, np.nan)
        hi = merged[["val_a", "val_b"]].max(axis=1)
        flagged = merged[(hi / lo) > RATIO_THRESHOLD]
        if flagged.empty:
            continue

        for _, row in flagged.iterrows():
            mask = (
                df["location_name"].isin([loc_a, loc_b])
                & (df["date"] == row["date"])
                & (df["parameter"] == row["parameter"])
            )
            suspicious_idx.update(df.index[mask].tolist())

    if suspicious_idx:
        result.loc[list(suspicious_idx)] = True
    return result


def main():
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)

    src = RAW_DIR / "delhi_raw.parquet"
    if not src.exists():
        raise FileNotFoundError(f"{src} — run fetch_air_quality.py first")

    df = pd.read_parquet(src)
    df["date"] = pd.to_datetime(df["date"])
    logger.info(f"Loaded {len(df):,} rows, {df['location_name'].nunique()} stations")

    # 0. Drop stations with insufficient data
    days_per_station = df.groupby("location_name")["date"].nunique()
    valid = days_per_station[days_per_station >= MIN_STATION_DAYS].index
    dropped = sorted(set(df["location_name"].unique()) - set(valid))
    df = df[df["location_name"].isin(valid)].copy()
    logger.info(f"  Drop stations < {MIN_STATION_DAYS} days: {dropped}")
    logger.info(f"  Remaining: {df['location_name'].nunique()} stations, {len(df):,} rows")

    # 1. Convert all units to µg/m³ BEFORE any filtering
    for param, unit_label, factor in UNIT_CONVERSIONS:
        mask = (df["parameter"] == param) & (
            df["unit"].str.strip().str.lower() == unit_label
        )
        n = mask.sum()
        if n > 0:
            df.loc[mask, "value"] = df.loc[mask, "value"] * factor
            df.loc[mask, "unit"] = "µg/m³"
            logger.info(f"  Convert {param} {unit_label}→µg/m³ (×{factor}): {n:,} rows")

    # 2. Drop negative values
    n_before = len(df)
    df = df[df["value"] >= 0].copy()
    logger.info(f"  Drop negatives: -{n_before - len(df)} rows")

    # 3. Apply outlier caps
    n_before = len(df)
    cap_series = df["parameter"].map(OUTLIER_CAPS)
    df = df[df["value"] <= cap_series].copy()
    logger.info(f"  Apply caps: -{n_before - len(df)} rows")

    # 4. Aggregate to daily mean
    df = (
        df.groupby(
            ["date", "location_id", "location_name", "latitude", "longitude", "parameter"],
            as_index=False,
        )
        .agg(value=("value", "mean"), unit=("unit", "first"))
    )
    logger.info(f"  After daily aggregation: {len(df):,} rows")

    # 5. WHO exceedance label
    df["who_threshold"] = df["parameter"].map(WHO_THRESHOLDS)
    df["exceeds_who"] = df["value"] > df["who_threshold"]

    # 6. Cross-station suspicious flag
    close_pairs = find_close_pairs(df)
    logger.info(f"  Station pairs ≤{SPATIAL_THRESHOLD_KM}km: {len(close_pairs)}")
    df["is_suspicious"] = flag_suspicious(df, close_pairs)
    n_sus = df["is_suspicious"].sum()
    logger.info(f"  Suspicious rows: {n_sus} ({n_sus / len(df) * 100:.1f}%)")

    # Final column order (ADR-005)
    df = df[[
        "date", "location_id", "location_name", "latitude", "longitude",
        "parameter", "unit", "value", "exceeds_who", "who_threshold", "is_suspicious",
    ]]

    out_path = CLEANED_DIR / "air_quality.parquet"
    df.to_parquet(out_path, index=False)
    logger.info(f"✓ {out_path.name}: {len(df):,} rows × {df.shape[1]} cols")
    logger.info(f"  Stations: {df['location_name'].nunique()}")
    logger.info(f"  Date: {df['date'].min().date()} → {df['date'].max().date()}")

    logger.info("\n  WHO exceedance rate per parameter:")
    for param, grp in df.groupby("parameter"):
        rate = grp["exceeds_who"].mean() * 100
        logger.info(f"    {param:6s}: {rate:.1f}%")


if __name__ == "__main__":
    main()
