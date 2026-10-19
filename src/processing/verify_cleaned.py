"""
Verify all cleaned data sources before moving to Phase 3 (feature engineering).

Usage:
    python -m src.processing.verify_cleaned
"""
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parents[2]
CLEANED_DIR = ROOT / "data" / "cleaned"
EXTERNAL_DIR = ROOT / "data" / "external"

SEP = "=" * 55


def ok(passed: bool, msg: str):
    logger.info(f"  {'✓' if passed else '✗'} {msg}")


# ── Air Quality ────────────────────────────────────────────
def verify_air_quality():
    print(f"\n{SEP}\nAIR QUALITY  data/cleaned/air_quality.parquet\n{SEP}")
    path = CLEANED_DIR / "air_quality.parquet"
    if not path.exists():
        logger.info("  ✗ File not found — run clean_air_quality.py")
        return

    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])

    expected_cols = {
        "date", "location_id", "location_name", "latitude", "longitude",
        "parameter", "unit", "value", "exceeds_who", "who_threshold", "is_suspicious",
    }
    ok(expected_cols.issubset(df.columns), f"Schema: {len(df.columns)} cols")
    ok(len(df) > 50_000, f"Row count: {len(df):,}")
    ok(df["value"].isna().sum() == 0, f"No null values: {df['value'].isna().sum()} nulls")
    ok((df["value"] < 0).sum() == 0, f"No negatives: {(df['value'] < 0).sum()}")
    ok((df["unit"] == "µg/m³").all(), f"All units µg/m³: {df['unit'].unique()}")
    ok(df["location_name"].nunique() >= 55, f"Stations: {df['location_name'].nunique()}")
    ok(df["date"].min().year <= 2022, f"Date from: {df['date'].min().date()}")
    ok(df["date"].max().year >= 2025, f"Date to:   {df['date'].max().date()}")

    # Cap check
    CAPS = {"pm25": 1000, "pm10": 2000, "no2": 600, "o3": 600, "so2": 500, "co": 10000}
    logger.info("\n  Value ranges after cleaning:")
    for param, grp in df.groupby("parameter"):
        cap = CAPS.get(param, 9999)
        over = (grp["value"] > cap).sum()
        ok(over == 0, f"{param:6s}: max={grp['value'].max():.1f}  (cap={cap})  over_cap={over}")

    # WHO exceedance
    logger.info("\n  WHO exceedance rate:")
    for param, grp in df.groupby("parameter"):
        rate = grp["exceeds_who"].mean() * 100
        logger.info(f"    {param:6s}: {rate:.1f}%")

    sus_pct = df["is_suspicious"].mean() * 100
    logger.info(f"\n  Suspicious rows: {df['is_suspicious'].sum()} ({sus_pct:.1f}%)")


# ── Weather ────────────────────────────────────────────────
def verify_weather():
    print(f"\n{SEP}\nWEATHER  data/external/weather.parquet\n{SEP}")
    path = EXTERNAL_DIR / "weather.parquet"
    if not path.exists():
        logger.info("  ✗ File not found — run clean_weather.py")
        return

    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])

    ok(df["location_name"].nunique() >= 55, f"Stations: {df['location_name'].nunique()}")
    ok(df["date"].min().year <= 2022, f"Date from: {df['date'].min().date()}")
    ok(df["date"].max().year >= 2025, f"Date to:   {df['date'].max().date()}")

    BOUNDS = {
        "temperature":           (-5.0,   50.0),
        "wind_speed":            ( 0.0,  150.0),
        "precipitation":         ( 0.0,  300.0),
        "humidity":              ( 0.0,  100.0),
        "boundary_layer_height": ( 0.0, 4000.0),
    }
    logger.info("\n  Bounds & null % per column:")
    for col, (lo, hi) in BOUNDS.items():
        if col not in df.columns:
            logger.info(f"  ✗ Missing column: {col}")
            continue
        out_of_range = ((df[col] < lo) | (df[col] > hi)).sum()
        null_pct = df[col].isna().mean() * 100
        ok(out_of_range == 0 and null_pct < 10,
           f"{col}: out_of_range={out_of_range}  null={null_pct:.1f}%")


# ── Industrial ─────────────────────────────────────────────
def verify_industrial():
    print(f"\n{SEP}\nINDUSTRIAL  data/external/industrial.parquet\n{SEP}")
    path = EXTERNAL_DIR / "industrial.parquet"
    if not path.exists():
        logger.info("  ✗ File not found — run clean_industrial.py")
        return

    df = pd.read_parquet(path)

    ok(len(df) >= 3, f"Plant count: {len(df)}")
    ok(df["capacity_mw"].isna().sum() == 0, "No null capacity_mw")
    ok((df["capacity_mw"] > 0).all(), "All capacity_mw > 0")
    ok(df[["latitude", "longitude"]].isna().sum().sum() == 0, "All coords present")
    ok(df.duplicated(subset=["latitude", "longitude"]).sum() == 0, "No duplicate coords")

    logger.info(f"\n  Plants:\n{df[['name','primary_fuel','capacity_mw']].to_string(index=False)}")


def main():
    verify_air_quality()
    verify_weather()
    verify_industrial()
    print(f"\n{SEP}")
    print("Fix all ✗ before moving to Phase 3 (feature engineering).")
    print(SEP)


if __name__ == "__main__":
    main()
