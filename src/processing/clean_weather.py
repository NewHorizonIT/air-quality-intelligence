"""
Clean Open-Meteo weather data per ADR-005.

Pipeline:
    1. Validate bounds — replace out-of-range values with NaN
    2. Forward fill per station, max 3 consecutive days
       Gap > 3 days: keep NaN → row will be dropped in feature engineering

Usage:
    python -m src.processing.clean_weather

Input/Output: data/external/weather.parquet  (overwrite in-place)
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
WEATHER_PATH = ROOT / "data" / "external" / "weather.parquet"

# Valid ranges for Delhi NCR (ADR-005)
# wind_direction (0–360°) is excluded — no physical bound to filter
WEATHER_BOUNDS: dict[str, tuple[float, float]] = {
    "temperature":           (-5.0,   50.0),
    "wind_speed":            ( 0.0,  150.0),
    "precipitation":         ( 0.0,  300.0),
    "humidity":              ( 0.0,  100.0),
    "boundary_layer_height": ( 0.0, 4000.0),
}


def main():
    if not WEATHER_PATH.exists():
        raise FileNotFoundError(f"{WEATHER_PATH} — run fetch_weather.py first")

    df = pd.read_parquet(WEATHER_PATH)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["location_name", "date"]).reset_index(drop=True)
    logger.info(f"Loaded {len(df):,} rows, {df['location_name'].nunique()} stations")

    # 1. Replace out-of-bounds values with NaN
    logger.info("\n  Bounds validation:")
    for col, (lo, hi) in WEATHER_BOUNDS.items():
        if col not in df.columns:
            logger.warning(f"  Column '{col}' not found — skip")
            continue
        n_before = df[col].isna().sum()
        df.loc[df[col] < lo, col] = np.nan
        df.loc[df[col] > hi, col] = np.nan
        n_new = df[col].isna().sum() - n_before
        logger.info(f"    {col}: {n_new} new NaN (out of [{lo}, {hi}])")

    # 2. Forward fill per station, max 3 consecutive days
    cols_to_fill = [c for c in WEATHER_BOUNDS if c in df.columns]
    df[cols_to_fill] = (
        df.groupby("location_name")[cols_to_fill]
        .transform(lambda x: x.ffill(limit=3))
    )
    logger.info("\n  After forward fill (limit=3):")
    logger.info("  Null % per column:")
    for col in cols_to_fill:
        pct = df[col].isna().mean() * 100
        logger.info(f"    {col}: {pct:.2f}%")

    # Overwrite in-place (ADR-006)
    df.to_parquet(WEATHER_PATH, index=False)
    logger.info(f"\n✓ {WEATHER_PATH.name}: {len(df):,} rows × {df.shape[1]} cols")
    logger.info(f"  Date: {df['date'].min().date()} → {df['date'].max().date()}")
    logger.info(f"  Stations: {df['location_name'].nunique()}")


if __name__ == "__main__":
    main()
