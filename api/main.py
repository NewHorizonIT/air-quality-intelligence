"""
api/main.py — FastAPI backend cho Air Quality Intelligence Demo.

Luồng dữ liệu khi khởi động:
  1. Load models/lgbm_exp3_best.pkl (LightGBM tốt nhất, Optuna-tuned, 25 features)
  2. Đọc data/features/test.parquet (Q4-2025, 4 622 rows × 31 cols)
  3. Chạy model.predict() cho toàn bộ test set → lưu vào df["predicted"]
  4. Khởi tạo shap.TreeExplainer một lần để tái dùng per request

POST /api/predict có 2 đường:
  - Fast path   : (station, date) có trong test.parquet → dùng pre-computed features
  - Live path   : (station, date) KHÔNG trong test.parquet → gọi api/live.py:
                    * OpenAQ API → 31 ngày PM2.5 lịch sử
                    * Open-Meteo ERA5 → weather cho ngày đó
                    * Tính 25 features on-the-fly → model.predict() → SHAP

Chạy:
  uvicorn api.main:app --reload --port 8000
"""

import logging
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
import requests
import shap
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Live feature engineering cho dự đoán ngoài Q4-2025
from api.live import build_live_features, get_sensor_map

logger = logging.getLogger(__name__)

# ── Đường dẫn tệp ──────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "lgbm_exp3_best.pkl"
TEST_PATH  = ROOT / "data" / "features" / "test.parquet"

# ── Danh sách features theo đúng thứ tự model kỳ vọng ────────────────────
# Thứ tự này phải khớp hoàn toàn với model.feature_name_ khi training
# (xem src/models/train_lgbm.py — danh sách ALL_FEATS Exp3)
MODEL_FEATS = [
    # Temporal lag: PM2.5 của 1, 2, 3, 7 ngày trước
    "pm25_lag1", "pm25_lag2", "pm25_lag3", "pm25_lag7",
    # Rolling statistics: mean 7/14/30 ngày, std 7/14 ngày
    "pm25_roll7_mean", "pm25_roll14_mean", "pm25_roll30_mean",
    "pm25_roll7_std", "pm25_roll14_std",
    # Cyclical temporal encoding (tháng & ngày trong tuần)
    "month_sin", "month_cos", "dow_sin", "dow_cos",
    # Season dummies (autumn là baseline — bị drop khi training)
    "season_winter", "season_spring", "season_monsoon",
    # Weather features từ Open-Meteo ERA5
    "temperature", "wind_speed", "wind_direction",
    "precipitation", "humidity", "et0",
    # Industrial proximity features (static per station)
    "dist_nearest_plant_km", "capacity_weighted_dist", "n_plants_50km",
]

# ── Ngưỡng AQI (phải khớp với web/src/utils/levels.js) ───────────────────
def _level(pm25: float) -> str:
    """
    Chuyển giá trị PM2.5 (µg/m³) thành chuỗi mức độ AQI 5 bậc.
    Ngưỡng lấy từ dự án (không phải thang US-AQI chuẩn).
    """
    if pm25 <= 30:   return "Good"
    if pm25 <= 60:   return "Moderate"
    if pm25 <= 120:  return "Unhealthy"
    if pm25 <= 250:  return "Very Unhealthy"
    return "Hazardous"


# ══════════════════════════════════════════════════════════════════════════════
# Startup: load model + data vào singleton module-level
# Làm 1 lần khi uvicorn import module này — không làm lại per request.
# ══════════════════════════════════════════════════════════════════════════════
print("[api] Loading lgbm_exp3_best.pkl …")
with open(MODEL_PATH, "rb") as fh:
    _model = pickle.load(fh)

print("[api] Reading data/features/test.parquet …")
_df = pd.read_parquet(TEST_PATH)
_df["date"] = pd.to_datetime(_df["date"])

# Pre-compute predictions cho toàn bộ test set.
# "predicted" = next-day PM2.5 forecast của lgbm_exp3_best.
# bool columns (season_*) tự động cast sang float64 khi gọi .values
_df["predicted"] = _model.predict(_df[MODEL_FEATS])

# SHAP explainer khởi tạo 1 lần — TreeExplainer nhanh hơn KernelExplainer
# vì khai thác cấu trúc cây nội tại của LightGBM.
print("[api] Initialising shap.TreeExplainer …")
_explainer = shap.TreeExplainer(_model)

# Station metadata lookup: {name → {lat, lng}} cho live predict path
# Lấy từ test.parquet (đại diện đầy đủ 53 stations)
_station_meta: dict = (
    _df.groupby("location_name")
       .first()[["latitude", "longitude"]]
       .rename(columns={"latitude": "lat", "longitude": "lng"})
       .to_dict("index")
)

# Warm-up sensor cache ở background (không block startup)
print("[api] Loading sensor cache for live predictions …")
get_sensor_map()

print("[api] API ready on http://localhost:8000")


# ══════════════════════════════════════════════════════════════════════════════
# FastAPI app + CORS
# ══════════════════════════════════════════════════════════════════════════════
app = FastAPI(title="Air Quality Intelligence API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    # Cho phép Vite dev server (:5173) và CRA (:3000) gọi API
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic schema cho POST /predict ───────────────────────────────────────
class PredictRequest(BaseModel):
    station: str  # location_name chính xác từ endpoint /stations
    date: str     # ISO date string, e.g. "2025-10-15" (phải có trong test set)


# ══════════════════════════════════════════════════════════════════════════════
# GET /api/stations
#
# Trả về 1 bản ghi tóm tắt per station:
#   - Toạ độ địa lý (lat/lng)
#   - PM2.5 quan sát mới nhất + mức AQI
#   - PM2.5 trung bình toàn test period (Q4-2025)
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/stations")
def get_stations():
    # Lấy index của ngày muộn nhất cho mỗi station
    latest_idx = _df.groupby("location_name")["date"].idxmax()
    latest = _df.loc[
        latest_idx, ["location_name", "latitude", "longitude", "pm25", "date"]
    ].copy()

    # Trung bình PM2.5 của từng station qua toàn bộ test period
    avg = _df.groupby("location_name")["pm25"].mean().rename("avg_pm25")
    latest = latest.join(avg, on="location_name")

    result = []
    for _, row in latest.iterrows():
        result.append({
            "name":        row["location_name"],
            "lat":         round(float(row["latitude"]),  6),
            "lng":         round(float(row["longitude"]), 6),
            "latest_pm25": round(float(row["pm25"]),      1),
            "avg_pm25":    round(float(row["avg_pm25"]),  1),
            "level":       _level(float(row["pm25"])),
            "date":        row["date"].date().isoformat(),
        })
    # Sort theo avg_pm25 giảm dần để Top-10 table hiển thị đúng mà không cần sort lại
    result.sort(key=lambda x: x["avg_pm25"], reverse=True)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# GET /api/daily
#
# Trung bình thành phố theo ngày: PM2.5 thực tế vs dự đoán của model.
#
# Lưu ý về alignment ngày:
#   - Mỗi row trong test.parquet chứa features của ngày D
#     và model dự đoán pm25_target = PM2.5 ngày D+1
#   - Để so sánh "actual vs predicted" trên cùng trục ngày,
#     ta shift cột "predicted" lên 1 ngày (prediction made on D-1 → target D)
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/daily")
def get_daily():
    # Aggregate daily mean qua tất cả 53 stations
    daily = (
        _df.groupby("date")
           .agg(actual=("pm25", "mean"), predicted=("predicted", "mean"))
           .reset_index()
           .sort_values("date")
    )
    # Shift predicted lên 1 ngày: prediction ngày D → hiển thị ở ngày D+1
    daily["predicted"] = daily["predicted"].shift(1)
    daily = daily.dropna(subset=["predicted"])

    return [
        {
            "date":      row["date"].date().isoformat(),
            "actual":    round(float(row["actual"]),    1),
            "predicted": round(float(row["predicted"]), 1),
        }
        for _, row in daily.iterrows()
    ]


# ══════════════════════════════════════════════════════════════════════════════
# GET /api/history/{station}?days=N
#
# Trả về N ngày cuối của PM2.5 quan sát cho 1 station.
# Default days=30 (1 tháng để hiển thị context chart trên Prediction page).
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/history/{station}")
def get_history(station: str, days: int = 30):
    sub = _df[_df["location_name"] == station].sort_values("date")
    if sub.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Station '{station}' not found. "
                   "Call /api/stations to get valid station names.",
        )
    # tail(days): lấy N hàng cuối = N ngày gần nhất
    sub = sub.tail(days)
    return [
        {
            "date": row["date"].date().isoformat(),
            "pm25": round(float(row["pm25"]), 1),
        }
        for _, row in sub.iterrows()
    ]


# ══════════════════════════════════════════════════════════════════════════════
# POST /api/predict
# Body: { "station": "...", "date": "YYYY-MM-DD" }
#
# Dual-path pipeline:
#   FAST PATH  : (station, date) có trong test.parquet → lookup features ngay
#   LIVE PATH  : (station, date) KHÔNG có → gọi api/live.py:
#                  * OpenAQ v3 → 31 ngày PM2.5 lịch sử của station
#                  * Open-Meteo ERA5/Forecast → weather cho ngày đó
#                  * Tính 25 features on-the-fly → model.predict() → SHAP
#
# Response bổ sung field "source": "test_set" | "live" để UI hiển thị badge.
# "actual_pm25" = null cho live path (ground truth chưa tồn tại).
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/api/predict")
def predict(req: PredictRequest):
    # Parse date — bắt lỗi format trước khi truy vấn bất cứ thứ gì
    try:
        req_date = pd.to_datetime(req.date).normalize()
    except Exception:
        raise HTTPException(
            status_code=422,
            detail=f"Định dạng ngày không hợp lệ: '{req.date}'. Dùng YYYY-MM-DD.",
        )

    # Kiểm tra station hợp lệ — cần trước cả 2 path
    if req.station not in _station_meta:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy trạm '{req.station}'. Gọi /api/stations để xem danh sách.",
        )

    # ── FAST PATH: lookup trong test.parquet ────────────────────────────────
    mask = (_df["location_name"] == req.station) & (_df["date"] == req_date)
    rows = _df[mask]

    if not rows.empty:
        row = rows.iloc[0]
        # astype(float) cast bool columns (season_*) → 0.0/1.0
        X = row[MODEL_FEATS].values.reshape(1, -1).astype(float)
        predicted_pm25 = float(_model.predict(X)[0])
        shap_vals      = _explainer.shap_values(X)[0]
        return _build_predict_response(
            station        = req.station,
            date_str       = req.date,
            X              = X,
            shap_vals      = shap_vals,
            predicted_pm25 = predicted_pm25,
            actual_pm25    = float(row["pm25_target"]),   # ground truth có sẵn
            is_live        = False,
        )

    # ── LIVE PATH: gọi OpenAQ + Open-Meteo để tính features real-time ───────
    logger.info("[predict] live-path cho station=%s date=%s", req.station, req.date)
    meta = _station_meta[req.station]   # {lat, lng} đã verify station tồn tại ở trên

    try:
        feat_dict = build_live_features(
            station     = req.station,
            lat         = meta["lat"],
            lng         = meta["lng"],
            target_date = req_date.date(),
        )
    except KeyError as e:
        # Thường do station không có sensor_id trong delhi_sensors.json
        raise HTTPException(status_code=503, detail=str(e))
    except EnvironmentError as e:
        # OPENAQ_API_KEY chưa được cấu hình trong .env
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        # Không đủ lịch sử PM2.5 để tính rolling features (< 30 ngày dữ liệu)
        raise HTTPException(status_code=422, detail=str(e))
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Lỗi từ API bên ngoài: {e}")

    # Chuyển feature dict → numpy array theo đúng thứ tự MODEL_FEATS
    X = np.array(
        [float(feat_dict[f]) for f in MODEL_FEATS],
        dtype=float,
    ).reshape(1, -1)

    predicted_pm25 = float(_model.predict(X)[0])
    shap_vals      = _explainer.shap_values(X)[0]

    return _build_predict_response(
        station        = req.station,
        date_str       = req.date,
        X              = X,
        shap_vals      = shap_vals,
        predicted_pm25 = predicted_pm25,
        actual_pm25    = None,   # ground truth không có cho ngày ngoài test set
        is_live        = True,
    )


def _build_predict_response(
    station: str,
    date_str: str,
    X: "np.ndarray",
    shap_vals: "np.ndarray",
    predicted_pm25: float,
    actual_pm25: "float | None",
    is_live: bool,
) -> dict:
    """
    Tạo dict response chuẩn cho cả fast path và live path.
    actual_pm25 = None khi là live prediction.
    is_live = True để UI hiển thị badge "Live" thay vì "Test Set".
    """
    # SHAP: sort by |value| desc, top-10
    shap_items = sorted(
        [
            {
                "feature":       feat,
                "value":         round(float(sv), 3),      # contribution in µg/m³
                "feature_value": round(float(X[0, i]), 3), # actual feature value
            }
            for i, (feat, sv) in enumerate(zip(MODEL_FEATS, shap_vals))
        ],
        key=lambda x: abs(x["value"]),
        reverse=True,
    )[:10]

    # Confidence interval ± MAE (Exp3 test MAE ≈ 10 µg/m³)
    MAE = 10.0
    return {
        "station":         station,
        "date":            date_str,
        "predicted_pm25":  round(predicted_pm25, 1),
        "actual_pm25":     round(actual_pm25, 1) if actual_pm25 is not None else None,
        "level":           _level(predicted_pm25),
        "confidence_low":  round(max(0.0, predicted_pm25 - MAE), 1),
        "confidence_high": round(predicted_pm25 + MAE, 1),
        "shap_values":     shap_items,
        # Badge: "test_set" hiện "(Q4-2025)" | "live" hiện "(Real-time)"
        "source":          "live" if is_live else "test_set",
    }
