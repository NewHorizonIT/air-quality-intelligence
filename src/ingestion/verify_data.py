"""
Verify all raw data sources are complete before Phase 2 (cleaning).

Usage:
    python -m src.ingestion.verify_data
"""
import json
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parents[2]
RAW_DIR = ROOT / "data" / "raw"
EXTERNAL_DIR = ROOT / "data" / "external"
CACHE_DIR = ROOT / "data" / ".cache"

SEP = "=" * 55


def ok(passed: bool, msg: str):
    logger.info(f"  {'✓' if passed else '✗'} {msg}")


# ── Air Quality ────────────────────────────────────────────
def verify_air_quality():
    print(f"\n{SEP}\nAIR QUALITY  data/raw/delhi_raw.parquet\n{SEP}")
    path = RAW_DIR / "delhi_raw.parquet"
    if not path.exists():
        logger.info("  ✗ File not found — run fetch_air_quality.py")
        return

    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])

    ok(len(df) >= 10_000, f"Row count: {len(df):,}")
    ok(df["date"].min().year <= 2022, f"Date from: {df['date'].min().date()}")
    ok(df["date"].max().year >= 2022, f"Date to:   {df['date'].max().date()}")
    ok(df["value"].isna().sum() == 0, f"Null values: {df['value'].isna().sum()}")
    ok((df["value"] < 0).sum() == 0, f"Negative values: {(df['value'] < 0).sum()}")

    logger.info(f"\n  Stations : {df['location_name'].nunique()}")
    logger.info(f"  Parameters:\n{df['parameter'].value_counts().to_string()}")
    logger.info("\n  Value ranges (min / max / p99):")
    for param, g in df.groupby("parameter"):
        logger.info(
            f"    {param:6s}: {g['value'].min():8.1f} / {g['value'].max():10.1f} / {g['value'].quantile(0.99):8.1f}"
        )


# ── Weather ────────────────────────────────────────────────
def verify_weather():
    print(f"\n{SEP}\nWEATHER  data/external/weather.parquet\n{SEP}")
    path = EXTERNAL_DIR / "weather.parquet"
    if not path.exists():
        logger.info("  ✗ File not found — run fetch_weather.py")
        return

    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])

    ok(df["location_name"].nunique() >= 40, f"Stations: {df['location_name'].nunique()}")
    ok(df["date"].min().year <= 2022, f"Date from: {df['date'].min().date()}")
    ok(df["date"].max().year >= 2024, f"Date to:   {df['date'].max().date()}")

    WEATHER_COLS = ["temperature", "wind_speed", "wind_direction",
                    "precipitation", "humidity", "boundary_layer_height"]
    logger.info("\n  Null % per column:")
    for col in WEATHER_COLS:
        if col in df.columns:
            pct = df[col].isna().mean() * 100
            ok(pct < 10, f"{col}: {pct:.1f}% null")
        else:
            logger.info(f"  ✗ Missing column: {col}")


# ── Industrial ─────────────────────────────────────────────
def verify_industrial():
    print(f"\n{SEP}\nINDUSTRIAL  data/external/industrial.parquet\n{SEP}")
    path = EXTERNAL_DIR / "industrial.parquet"
    if not path.exists():
        logger.info("  ✗ File not found — run fetch_industrial.py")
        return

    df = pd.read_parquet(path)

    ok(5 <= len(df) <= 50, f"Plant count: {len(df)} (expect 5–50)")
    ok(df["capacity_mw"].isna().sum() == 0, "No null capacity_mw")
    ok((df["capacity_mw"] > 0).all(), "All capacity_mw > 0")
    ok(df[["latitude", "longitude"]].isna().sum().sum() == 0, "All coordinates present")

    logger.info(f"\n  Plants:\n{df[['name','primary_fuel','capacity_mw']].to_string(index=False)}")


# ── Cache ──────────────────────────────────────────────────
def verify_cache():
    print(f"\n{SEP}\nCACHE  data/.cache/\n{SEP}")
    for fname in ["delhi_locations.json", "delhi_sensors.json"]:
        path = CACHE_DIR / fname
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            ok(len(data) > 0, f"{fname}: {len(data)} entries")
        else:
            ok(False, f"{fname}: MISSING")


def main():
    verify_air_quality()
    verify_weather()
    verify_industrial()
    verify_cache()
    print(f"\n{SEP}")
    print("Fix all ✗ before moving to Phase 2 (data cleaning).")
    print(SEP)


if __name__ == "__main__":
    main()
