"""
Fetch historical weather data from Open-Meteo ERA5 (free, no API key).

Usage:
    python -m src.ingestion.fetch_weather

Requires:
    data/.cache/delhi_locations.json  (run fetch_air_quality.py first)

Output:
    data/external/weather.parquet

Columns: date, location_name, latitude, longitude,
         temperature, wind_speed, wind_direction, precipitation,
         humidity, boundary_layer_height
"""

import json
import logging
import time
from pathlib import Path

import openmeteo_requests
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parents[2]
CACHE_DIR = ROOT / "data" / ".cache"
EXTERNAL_DIR = ROOT / "data" / "external"
DATE_FROM = "2022-01-01"
DATE_TO = "2025-12-31"

OM_URL = "https://archive-api.open-meteo.com/v1/era5"

# Daily variables available in ERA5 archive
DAILY_VARS = [
    "temperature_2m_mean",  # → temperature
    "precipitation_sum",  # → precipitation
    "wind_speed_10m_max",  # → wind_speed
    "wind_direction_10m_dominant",  # → wind_direction
    "et0_fao_evapotranspiration",  # → et0 (mm/day)
]

# Hourly variables, aggregated to daily mean
HOURLY_VARS = [
    "relative_humidity_2m",  # → humidity
]


def build_client() -> openmeteo_requests.Client:
    session = requests.Session()
    retry = Retry(
        total=10,
        backoff_factor=2.0,          # waits: 2s, 4s, 8s, 16s, 32s …
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return openmeteo_requests.Client(session=session)


def fetch_station(
    om: openmeteo_requests.Client, name: str, lat: float, lon: float
) -> pd.DataFrame:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": DATE_FROM,
        "end_date": DATE_TO,
        "daily": DAILY_VARS,
        "hourly": HOURLY_VARS,
        "timezone": "Asia/Kolkata",
    }
    response = om.weather_api(OM_URL, params=params)[0]

    # --- Daily ---
    daily = response.Daily()
    daily_dates = pd.date_range(
        start=pd.Timestamp(daily.Time(), unit="s"),
        end=pd.Timestamp(daily.TimeEnd(), unit="s"),
        freq=pd.Timedelta(seconds=daily.Interval()),
        inclusive="left",
    )
    df = pd.DataFrame(
        {
            "date": daily_dates,
            "temperature": daily.Variables(0).ValuesAsNumpy(),
            "precipitation": daily.Variables(1).ValuesAsNumpy(),
            "wind_speed": daily.Variables(2).ValuesAsNumpy(),
            "wind_direction": daily.Variables(3).ValuesAsNumpy(),
            "et0": daily.Variables(4).ValuesAsNumpy(),
        }
    )
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()

    # --- Hourly humidity → daily mean ---
    hourly = response.Hourly()
    hourly_dates = pd.date_range(
        start=pd.Timestamp(hourly.Time(), unit="s"),
        end=pd.Timestamp(hourly.TimeEnd(), unit="s"),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left",
    )
    df_h = pd.DataFrame(
        {
            "date": pd.to_datetime(hourly_dates).normalize(),
            "humidity": hourly.Variables(0).ValuesAsNumpy(),
        }
    )
    humidity_daily = df_h.groupby("date", as_index=False)["humidity"].mean()

    df = df.merge(humidity_daily, on="date", how="left")
    df["location_name"] = name
    df["latitude"] = lat
    df["longitude"] = lon

    return df[
        [
            "date",
            "location_name",
            "latitude",
            "longitude",
            "temperature",
            "wind_speed",
            "wind_direction",
            "precipitation",
            "humidity",
            "et0",
        ]
    ]


def load_station_coords() -> list[dict]:
    cache_path = CACHE_DIR / "delhi_locations.json"
    if not cache_path.exists():
        raise FileNotFoundError(
            f"{cache_path} not found — run fetch_air_quality.py first"
        )
    locations = json.loads(cache_path.read_text(encoding="utf-8"))
    stations, seen = [], set()
    for loc in locations:
        name = loc.get("name", str(loc["id"]))
        coords = loc.get("coordinates", {})
        lat = coords.get("latitude")
        lon = coords.get("longitude")
        if lat is None or lon is None or name in seen:
            continue
        seen.add(name)
        stations.append({"name": name, "lat": lat, "lon": lon})
    return stations


def main():
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    stations = load_station_coords()
    logger.info(
        f"Fetching weather for {len(stations)} stations ({DATE_FROM} → {DATE_TO})"
    )

    om = build_client()
    frames = []
    for i, s in enumerate(stations, 1):
        logger.info(
            f"[{i}/{len(stations)}] {s['name']} ({s['lat']:.4f}, {s['lon']:.4f})"
        )
        df = fetch_station(om, s["name"], s["lat"], s["lon"])
        frames.append(df)
        time.sleep(1.0)  # 1 req/s — tránh 429 từ Open-Meteo free tier

    weather = pd.concat(frames, ignore_index=True)
    weather["date"] = pd.to_datetime(weather["date"])

    out_path = EXTERNAL_DIR / "weather.parquet"
    weather.to_parquet(out_path, index=False)
    logger.info(
        f"✓ {out_path.name}: {weather.shape[0]:,} rows × {weather.shape[1]} cols"
    )
    logger.info(f"  Stations: {weather['location_name'].nunique()}")
    logger.info(
        f"  Date: {weather['date'].min().date()} → {weather['date'].max().date()}"
    )
    logger.info(f"  Null %:\n{(weather.isna().mean() * 100).round(1).to_string()}")


if __name__ == "__main__":
    main()
