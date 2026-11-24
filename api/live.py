"""
api/live.py — Live feature engineering cho real-time prediction.

Dùng khi (station, date) KHÔNG có trong test.parquet (ngoài Q4-2025).

Pipeline mỗi request:
  1. Tra sensor_id từ cache  data/.cache/delhi_sensors.json
  2. Fetch 31 ngày PM2.5 từ  OpenAQ v3 API  (cần OPENAQ_API_KEY)
  3. Fetch weather cho ngày D từ  Open-Meteo ERA5  (miễn phí, không cần key)
  4. Tính 25 features giống build_features.py
  5. Trả dict features → gọi model.predict() trong main.py

Phân tách trách nhiệm:
  - api/live.py  : lấy dữ liệu raw + tính features
  - api/main.py  : load model, gọi live.py nếu cần, tính SHAP, trả response
"""

import json
import logging
import math
import os
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

ROOT              = Path(__file__).resolve().parent.parent
CACHE_DIR         = ROOT / "data" / ".cache"
INDUSTRIAL_PATH   = ROOT / "data" / "external" / "industrial.parquet"

# ── Open-Meteo API URLs ──────────────────────────────────────────────────────
# ERA5 archive: dữ liệu lịch sử từ 1940, lag ~5 ngày so với hôm nay
ERA5_URL          = "https://archive-api.open-meteo.com/v1/era5"
# Forecast API: bao gồm cả "past_days" cho dữ liệu rất gần đây (<7 ngày)
FORECAST_URL      = "https://api.open-meteo.com/v1/forecast"

# Daily weather variables (phải khớp với tên trong Open-Meteo API)
DAILY_VARS = [
    "temperature_2m_mean",           # → temperature
    "precipitation_sum",             # → precipitation
    "wind_speed_10m_max",            # → wind_speed
    "wind_direction_10m_dominant",   # → wind_direction
    "et0_fao_evapotranspiration",    # → et0
]
HOURLY_VARS = ["relative_humidity_2m"]  # aggregate to daily mean → humidity


# ══════════════════════════════════════════════════════════════════════════════
# Sensor ID lookup
# ══════════════════════════════════════════════════════════════════════════════

def _build_sensor_map() -> dict:
    """
    Đọc data/.cache/delhi_sensors.json (được tạo bởi fetch_air_quality.py)
    và build mapping  {location_name → pm25_sensor_id}.

    Nếu cache không tồn tại → trả {} (live predict sẽ trả 503).
    Nếu 1 station có nhiều pm25 sensor → chọn sensor_id nhỏ nhất (oldest/stable).
    """
    cache_path = CACHE_DIR / "delhi_sensors.json"
    if not cache_path.exists():
        logger.warning(
            f"Sensor cache not found at {cache_path}. "
            "Run: python -m src.ingestion.fetch_air_quality"
        )
        return {}

    sensors = json.loads(cache_path.read_text(encoding="utf-8"))
    sensor_map = {}
    for s in sensors:
        # Chỉ lấy sensor đo PM2.5
        if s.get("parameter", {}).get("name", "").lower() != "pm25":
            continue
        name = s.get("_location_name", "")
        if not name:
            continue
        sid = s["id"]
        # Dùng sensor_id nhỏ nhất nếu nhiều sensor per station
        if name not in sensor_map or sid < sensor_map[name]:
            sensor_map[name] = sid

    logger.info(f"Sensor map loaded: {len(sensor_map)} PM2.5 stations")
    return sensor_map


# Module-level singleton — tải 1 lần khi import
_SENSOR_MAP: dict | None = None


def get_sensor_map() -> dict:
    global _SENSOR_MAP
    if _SENSOR_MAP is None:
        _SENSOR_MAP = _build_sensor_map()
    return _SENSOR_MAP


# ══════════════════════════════════════════════════════════════════════════════
# Industrial features (static per station)
# ══════════════════════════════════════════════════════════════════════════════

_PLANTS_DF: pd.DataFrame | None = None


def _get_plants() -> pd.DataFrame:
    global _PLANTS_DF
    if _PLANTS_DF is None:
        if INDUSTRIAL_PATH.exists():
            _PLANTS_DF = pd.read_parquet(INDUSTRIAL_PATH)
        else:
            logger.warning(f"industrial.parquet not found: {INDUSTRIAL_PATH}")
            _PLANTS_DF = pd.DataFrame(columns=["latitude", "longitude", "capacity_mw"])
    return _PLANTS_DF


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Khoảng cách Haversine (km) giữa 2 điểm địa lý."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def _compute_industrial(lat: float, lng: float) -> dict:
    """
    Tính 3 industrial proximity features cho 1 station.
    Giống hàm build_industrial_features() trong build_features.py.
    """
    plants = _get_plants()
    if plants.empty:
        return {
            "dist_nearest_plant_km": 0.0,
            "capacity_weighted_dist": 0.0,
            "n_plants_50km": 0,
        }

    # Tính khoảng cách đến từng nhà máy, clip ≥ 0.1 km tránh chia 0
    dists = plants.apply(
        lambda p: max(0.1, _haversine_km(lat, lng, p["latitude"], p["longitude"])),
        axis=1,
    )

    return {
        # Khoảng cách đến nhà máy gần nhất
        "dist_nearest_plant_km": float(dists.min()),
        # Inverse-square weighted capacity — đo mật độ công nghiệp
        "capacity_weighted_dist": float((plants["capacity_mw"] / dists ** 2).sum()),
        # Số nhà máy trong bán kính 50 km
        "n_plants_50km": int((dists <= 50).sum()),
    }


# ══════════════════════════════════════════════════════════════════════════════
# OpenAQ — PM2.5 history
# ══════════════════════════════════════════════════════════════════════════════

def fetch_pm25_history(sensor_id: int, target_date: date, days: int = 31) -> dict:
    """
    Fetch daily PM2.5 từ OpenAQ v3 API cho 1 sensor trong khoảng
    [target_date - days, target_date] (inclusive).

    Returns:
        {date_obj: pm25_float}

    Raises:
        EnvironmentError: OPENAQ_API_KEY chưa được set
        requests.HTTPError: lỗi từ OpenAQ API
    """
    api_key = os.getenv("OPENAQ_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "OPENAQ_API_KEY chưa được cấu hình. "
            "Thêm vào file .env: OPENAQ_API_KEY=your_key_here"
        )

    date_from = (target_date - timedelta(days=days)).isoformat()
    date_to   = target_date.isoformat()

    resp = requests.get(
        f"https://api.openaq.org/v3/sensors/{sensor_id}/days",
        params={
            "date_from": date_from,
            "date_to":   date_to,
            "limit":     100,  # 31 ngày nên luôn < 100
        },
        headers={"X-API-Key": api_key},
        timeout=30,
    )
    resp.raise_for_status()

    history = {}
    for m in resp.json().get("results", []):
        # OpenAQ v3: period.datetimeFrom.local = "2026-11-24T05:30:00+05:30"
        dt_str = m.get("period", {}).get("datetimeFrom", {}).get("local", "")[:10]
        val    = m.get("value")
        if dt_str and val is not None:
            history[date.fromisoformat(dt_str)] = float(val)

    logger.info(
        f"OpenAQ sensor {sensor_id}: {len(history)} days "
        f"({date_from} → {date_to})"
    )
    return history


# ══════════════════════════════════════════════════════════════════════════════
# Open-Meteo — Weather
# ══════════════════════════════════════════════════════════════════════════════

def fetch_weather(lat: float, lng: float, target_date: date) -> dict:
    """
    Fetch weather cho 1 ngày cụ thể từ Open-Meteo (miễn phí, không cần API key).

    - Dùng ERA5 archive cho ngày cũ hơn 7 ngày (độ chính xác cao hơn)
    - Dùng Forecast API (past_days) cho ngày rất gần đây (ERA5 có lag ~5 ngày)

    Returns:
        {temperature, wind_speed, wind_direction, precipitation, humidity, et0}

    Raises:
        requests.HTTPError: lỗi từ Open-Meteo API
    """
    today = date.today()
    # ERA5 có lag ~5 ngày: nếu target_date trong vòng 7 ngày → dùng forecast
    use_era5 = (today - target_date).days > 7
    base_url  = ERA5_URL if use_era5 else FORECAST_URL

    date_str = target_date.isoformat()
    params = {
        "latitude":   lat,
        "longitude":  lng,
        "start_date": date_str,
        "end_date":   date_str,
        "daily":      ",".join(DAILY_VARS),
        "hourly":     ",".join(HOURLY_VARS),
        "timezone":   "Asia/Kolkata",
        "format":     "json",  # nhận JSON thay vì FlatBuffers binary
    }

    # Forecast API dùng past_days thay vì start_date/end_date
    if not use_era5:
        days_back = (today - target_date).days
        params = {
            "latitude":   lat,
            "longitude":  lng,
            "daily":      ",".join(DAILY_VARS),
            "hourly":     ",".join(HOURLY_VARS),
            "timezone":   "Asia/Kolkata",
            "past_days":  max(days_back + 1, 1),
            "forecast_days": 1,
            "format":     "json",
        }

    resp = requests.get(base_url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    daily  = data.get("daily", {})
    hourly = data.get("hourly", {})

    # Với forecast API + past_days, kết quả trả nhiều ngày → tìm đúng ngày target
    dates_in_response = daily.get("time", [date_str])

    def get_val_for_date(key: str) -> float:
        """Lấy giá trị của key tại ngày target_date trong daily response."""
        vals = daily.get(key, [])
        if not vals:
            return 0.0
        try:
            idx = dates_in_response.index(date_str)
            v = vals[idx]
            return float(v) if v is not None else 0.0
        except (ValueError, IndexError):
            # Fallback: lấy phần tử cuối cùng (gần nhất)
            v = vals[-1]
            return float(v) if v is not None else 0.0

    # Hourly humidity: lọc các giờ trong ngày target_date, rồi lấy mean
    hourly_times = hourly.get("time", [])
    hourly_rh    = hourly.get("relative_humidity_2m", [])
    day_humidity = [
        float(v) for t, v in zip(hourly_times, hourly_rh)
        if t[:10] == date_str and v is not None
    ]
    humidity = float(np.mean(day_humidity)) if day_humidity else 0.0

    result = {
        "temperature":    get_val_for_date("temperature_2m_mean"),
        "precipitation":  get_val_for_date("precipitation_sum"),
        "wind_speed":     get_val_for_date("wind_speed_10m_max"),
        "wind_direction": get_val_for_date("wind_direction_10m_dominant"),
        "et0":            get_val_for_date("et0_fao_evapotranspiration"),
        "humidity":       humidity,
    }

    logger.info(
        f"Open-Meteo ({'ERA5' if use_era5 else 'Forecast'}) "
        f"[{lat:.3f},{lng:.3f}] {date_str}: "
        f"T={result['temperature']:.1f}°C, ws={result['wind_speed']:.1f}m/s, "
        f"RH={result['humidity']:.0f}%, P={result['precipitation']:.1f}mm"
    )
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Feature assembly
# ══════════════════════════════════════════════════════════════════════════════

def _get_season(month: int) -> str:
    """Mùa vụ — phải nhất quán với build_features.py."""
    if month in [12, 1, 2]:    return "winter"
    if month in [3, 4, 5]:     return "spring"
    if month in [6, 7, 8, 9]:  return "monsoon"
    return "autumn"


def build_live_features(
    station: str,
    lat: float,
    lng: float,
    target_date: date,
) -> dict:
    """
    Hàm chính: orchestrate toàn bộ live feature engineering cho 1 (station, date).

    target_date = ngày D (ngày có observations làm đầu vào cho model).
    Model sẽ dự đoán PM2.5 ngày D+1.

    Returns:
        dict với đúng 25 keys = MODEL_FEATS trong main.py

    Raises:
        KeyError:          station không có trong sensor cache
        EnvironmentError:  OPENAQ_API_KEY chưa set
        ValueError:        không đủ PM2.5 lịch sử
        requests.HTTPError: lỗi API
    """
    # ── Sensor lookup ──────────────────────────────────────────────────────
    sensor_map = get_sensor_map()
    if station not in sensor_map:
        raise KeyError(
            f"Station '{station}' không có trong sensor cache. "
            "Hãy chạy lại: python -m src.ingestion.fetch_air_quality"
        )
    sensor_id = sensor_map[station]

    # ── Step 1: PM2.5 history (OpenAQ) ────────────────────────────────────
    # Cần 31 ngày: D-30 … D để tính rolling-30 và lag-7
    history = fetch_pm25_history(sensor_id, target_date, days=31)

    if len(history) < 7:
        raise ValueError(
            f"Không đủ dữ liệu PM2.5 cho '{station}': "
            f"cần ≥7 ngày, chỉ có {len(history)} ngày trong 31 ngày gần nhất."
        )

    def pm25_at(d: date) -> float:
        return float(history.get(d, float("nan")))

    # ── Step 2: Lag features ───────────────────────────────────────────────
    # pm25_lagN = PM2.5 quan sát N ngày trước target_date
    lag_feats = {
        "pm25_lag1": pm25_at(target_date - timedelta(1)),
        "pm25_lag2": pm25_at(target_date - timedelta(2)),
        "pm25_lag3": pm25_at(target_date - timedelta(3)),
        "pm25_lag7": pm25_at(target_date - timedelta(7)),
    }

    # ── Step 3: Rolling features ───────────────────────────────────────────
    # Mirrors build_features.py shift(1)-before-rolling:
    # window bắt đầu từ D-1 trở về trước (không include ngày D)
    def _window_vals(w: int) -> list:
        vals = [pm25_at(target_date - timedelta(i)) for i in range(1, w + 1)]
        return [v for v in vals if not math.isnan(v)]

    r7, r14, r30 = _window_vals(7), _window_vals(14), _window_vals(30)

    # min_periods tương tự build_features.py (window // 2)
    rolling_feats = {
        "pm25_roll7_mean":  float(np.mean(r7))  if len(r7)  >= 4  else float("nan"),
        "pm25_roll14_mean": float(np.mean(r14)) if len(r14) >= 7  else float("nan"),
        "pm25_roll30_mean": float(np.mean(r30)) if len(r30) >= 15 else float("nan"),
        "pm25_roll7_std":   float(np.std(r7, ddof=1))  if len(r7)  >= 4  else float("nan"),
        "pm25_roll14_std":  float(np.std(r14, ddof=1)) if len(r14) >= 7  else float("nan"),
    }

    # ── Step 4: Cyclical temporal ──────────────────────────────────────────
    month  = target_date.month
    dow    = target_date.weekday()   # 0 = Monday (pandas default)
    season = _get_season(month)

    temporal_feats = {
        "month_sin":      math.sin(2 * math.pi * month / 12),
        "month_cos":      math.cos(2 * math.pi * month / 12),
        "dow_sin":        math.sin(2 * math.pi * dow / 7),
        "dow_cos":        math.cos(2 * math.pi * dow / 7),
        "season_winter":  season == "winter",
        "season_spring":  season == "spring",
        "season_monsoon": season == "monsoon",
    }

    # ── Step 5: Weather (Open-Meteo) ───────────────────────────────────────
    weather_feats = fetch_weather(lat, lng, target_date)

    # ── Step 6: Industrial proximity (static) ─────────────────────────────
    industrial_feats = _compute_industrial(lat, lng)

    # ── Merge tất cả 25 features ───────────────────────────────────────────
    features = {
        **lag_feats,
        **rolling_feats,
        **temporal_feats,
        **weather_feats,
        **industrial_feats,
    }

    # Kiểm tra NaN trong các features quan trọng
    nan_keys = [k for k, v in features.items() if isinstance(v, float) and math.isnan(v)]
    if nan_keys:
        logger.warning(f"NaN trong features: {nan_keys} — model vẫn chạy nhưng độ chính xác giảm")

    return features
