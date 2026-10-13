"""
Fetch raw air quality data from OpenAQ v3 API and save to data/raw/.

Usage:
    python -m src.ingestion.fetch_air_quality
    (API key loaded from .env automatically)

Output:
    data/raw/delhi_raw.parquet       — all sensors merged
    data/raw/<param>/sensor_<id>.parquet  — per-sensor files (resumable)
    data/.cache/delhi_locations.json
    data/.cache/delhi_sensors.json
"""
import json
import logging
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from src.ingestion.openaq_client import OpenAQClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parents[2]
RAW_DIR = ROOT / "data" / "raw"
CACHE_DIR = ROOT / "data" / ".cache"
DATE_FROM = "2022-01-01"
DATE_TO = "2025-12-31"


def load_or_fetch_locations(client: OpenAQClient) -> list[dict]:
    cache_path = CACHE_DIR / "delhi_locations.json"
    if cache_path.exists():
        logger.info("Locations: loading from cache")
        return json.loads(cache_path.read_text(encoding="utf-8"))
    logger.info("Fetching locations from OpenAQ...")
    locations = client.get_delhi_locations()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(locations, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Cached {len(locations)} locations → {cache_path.name}")
    return locations


def load_or_fetch_sensors(client: OpenAQClient, locations: list[dict]) -> list[dict]:
    cache_path = CACHE_DIR / "delhi_sensors.json"
    if cache_path.exists():
        logger.info("Sensors: loading from cache")
        return json.loads(cache_path.read_text(encoding="utf-8"))
    logger.info(f"Fetching sensors for {len(locations)} locations...")
    all_sensors = []
    for loc in locations:
        loc_id = loc["id"]
        loc_name = loc.get("name", str(loc_id))
        coords = loc.get("coordinates", {})
        sensors = client.get_sensors(loc_id)
        for s in sensors:
            s["_location_id"] = loc_id
            s["_location_name"] = loc_name
            s["_latitude"] = coords.get("latitude")
            s["_longitude"] = coords.get("longitude")
        all_sensors.extend(sensors)
        logger.info(f"  {loc_name}: {len(sensors)} sensors")
    cache_path.write_text(json.dumps(all_sensors, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Cached {len(all_sensors)} sensors → {cache_path.name}")
    return all_sensors


def fetch_sensor(client: OpenAQClient, sensor: dict) -> pd.DataFrame:
    sensor_id = sensor["id"]
    param = sensor.get("parameter", {}).get("name", "unknown").lower()
    unit = sensor.get("parameter", {}).get("units", "")
    loc_id = sensor["_location_id"]
    loc_name = sensor["_location_name"]
    lat = sensor["_latitude"]
    lon = sensor["_longitude"]

    out_path = RAW_DIR / param / f"sensor_{sensor_id}.parquet"
    if out_path.exists():
        existing = pd.read_parquet(out_path)
        existing_max = pd.to_datetime(existing["date"]).max()
        target_end = pd.Timestamp(DATE_TO)
        if existing_max >= target_end - pd.Timedelta(days=7):
            logger.info(f"  Skip {param}@{loc_name} — up to date ({existing_max.date()})")
            return existing
        logger.info(f"  Re-fetch {param}@{loc_name} — only up to {existing_max.date()}, need {DATE_TO}")

    raw = client.get_measurements(sensor_id, DATE_FROM, DATE_TO)
    if not raw:
        logger.warning(f"  No data: sensor {sensor_id} ({param}@{loc_name})")
        return pd.DataFrame()

    rows = []
    for m in raw:
        period = m.get("period", {})
        dt_local = period.get("datetimeFrom", {}).get("local", "")
        date_str = dt_local[:10] if dt_local else ""
        if not date_str:
            continue
        rows.append({
            "date": date_str,
            "location_id": loc_id,
            "location_name": loc_name,
            "latitude": lat,
            "longitude": lon,
            "parameter": param,
            "unit": unit,
            "value": m.get("value"),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["value"])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    logger.info(f"  Saved sensor_{sensor_id}.parquet: {len(df)} rows")
    return df


def merge_all() -> pd.DataFrame:
    frames = [pd.read_parquet(f) for f in sorted(RAW_DIR.rglob("sensor_*.parquet"))]
    if not frames:
        raise RuntimeError("No sensor parquet files found — run fetch first")
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["date", "location_name", "parameter"]).reset_index(drop=True)


def main():
    api_key = os.environ.get("OPENAQ_API_KEY", "")
    if not api_key:
        raise EnvironmentError("OPENAQ_API_KEY environment variable is not set")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    client = OpenAQClient(api_key)

    locations = load_or_fetch_locations(client)
    logger.info(f"Total locations: {len(locations)}")

    sensors = load_or_fetch_sensors(client, locations)
    logger.info(f"Total sensors: {len(sensors)}")

    logger.info(f"Fetching measurements ({DATE_FROM} → {DATE_TO})...")
    for i, sensor in enumerate(sensors, 1):
        param = sensor.get("parameter", {}).get("name", "?")
        loc_name = sensor.get("_location_name", "?")
        logger.info(f"[{i}/{len(sensors)}] {param} @ {loc_name}")
        fetch_sensor(client, sensor)

    logger.info("Merging all sensor files...")
    df = merge_all()
    out_path = RAW_DIR / "delhi_raw.parquet"
    df.to_parquet(out_path, index=False)
    logger.info(f"✓ {out_path.name}: {df.shape[0]:,} rows × {df.shape[1]} cols")
    logger.info(f"  Date: {df['date'].min().date()} → {df['date'].max().date()}")
    logger.info(f"  Stations: {df['location_name'].nunique()}")
    logger.info(f"  Parameters:\n{df['parameter'].value_counts().to_string()}")


if __name__ == "__main__":
    main()
