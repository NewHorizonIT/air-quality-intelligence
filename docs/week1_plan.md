# Tuần 1 — Phase 1: Data Ingestion
**2026-10-13 → 2026-10-17**

---

## Mục tiêu cuối tuần

Toàn bộ raw data đã fetch xong, lưu đúng chỗ, verify sạch:
- `data/raw/delhi_raw.parquet` ← OpenAQ 2022–2024
- `data/external/weather.parquet` ← Open-Meteo 46 stations
- `data/external/industrial.parquet` ← WRI GPPD Delhi NCR
- `data/.cache/delhi_locations.json` + `delhi_sensors.json`

---

## Thứ 2 — 2026-10-13: Setup + OpenAQ Client

### Buổi sáng: Setup project structure + install packages

**Bước 1: Tạo thư mục**
```
data/
  raw/
  external/
  cleaned/
  features/
  predictions/
  .cache/
  exports/

src/
  __init__.py
  ingestion/
    __init__.py
  processing/
    __init__.py
  features/
    __init__.py
  models/
    __init__.py

models/          ← lưu .pkl files
reports/
  figures/

app/
  pages/
  components/
  utils/

notebooks/
```

**Bước 2: Install packages còn thiếu**
```bash
pip install lightgbm optuna shap openmeteo-requests geopy \
            scikit-learn matplotlib seaborn streamlit scipy joblib \
            plotly folium
```

**Bước 3: Update requirements.txt**
```bash
pip freeze > requirements.txt
```

---

### Buổi chiều: Viết `src/ingestion/openaq_client.py`

File này là wrapper cho OpenAQ v3 API. Cần có:

```python
class OpenAQClient:
    BASE_URL = "https://api.openaq.org/v3"

    def __init__(self, api_key: str)
        # Session với retry logic + rate limiting

    def get_delhi_locations(self) -> list[dict]
        # Fetch tất cả locations trong bounding box Delhi NCR
        # DELHI_BBOX = "76.84,28.40,77.35,28.88"
        # Paginate đến hết

    def get_sensors(self, location_id: int) -> list[dict]
        # Fetch sensors của location
        # Filter: chỉ giữ pm25, pm10, no2, o3, so2, co

    def get_measurements(self, sensor_id: int, date_from: str, date_to: str) -> list[dict]
        # Fetch daily measurements (endpoint /sensors/{id}/days)
        # Paginate đến hết
```

**Checklist hôm nay:**
- [ ] Tất cả thư mục đã tạo
- [ ] 11 packages đã install
- [ ] requirements.txt đã update
- [ ] `src/ingestion/openaq_client.py` đã viết xong
- [ ] Test quick: gọi `get_delhi_locations()` ra được ít nhất 1 location

---

## Thứ 3 — 2026-10-14: Fetch Air Quality Data

### Viết `src/ingestion/fetch_air_quality.py`

Script này fetch toàn bộ raw data từ OpenAQ và save vào `data/raw/`.

**Logic:**
```
1. Load cache locations nếu có → nếu không thì fetch + save cache
2. Load cache sensors nếu có  → nếu không thì fetch + save cache
3. Với mỗi sensor:
   - Kiểm tra file đã tồn tại chưa (resumable)
   - Fetch measurements 2022-01-01 → 2024-12-31
   - Save vào data/raw/<param>/sensor_<id>.parquet
4. Merge tất cả sensors thành delhi_raw.parquet
```

**Chạy script:**
```bash
python -m src.ingestion.fetch_air_quality
```

> ⚠️ Script này chạy lâu (~30–60 phút). Chạy xong rồi làm việc khác.

**Checklist hôm nay:**
- [ ] `fetch_air_quality.py` đã viết xong
- [ ] Script đang chạy (background)
- [ ] `data/.cache/delhi_locations.json` đã có
- [ ] `data/.cache/delhi_sensors.json` đã có

---

## Thứ 4 — 2026-10-15: Fetch Weather Data

### Buổi sáng: Verify air quality data

Trong lúc chờ hoặc sau khi fetch xong, verify:
```python
import pandas as pd
df = pd.read_parquet("data/raw/delhi_raw.parquet")
print(df.shape)               # expect ~42,000 rows
print(df["parameter"].value_counts())
print(df["date"].min(), df["date"].max())
```

### Buổi chiều: Viết `src/ingestion/fetch_weather.py`

Dùng Open-Meteo Historical API — **miễn phí, không cần API key**.

**Logic:**
```
1. Load tọa độ 46 trạm từ delhi_locations.json
2. Với mỗi trạm:
   - Gọi Open-Meteo API với lat/lon của trạm
   - Fetch 6 variables: temperature, wind_speed, wind_direction,
     precipitation, humidity, boundary_layer_height
   - Date range: 2022-01-01 → 2024-12-31
3. Merge tất cả thành weather.parquet
```

**API endpoint:**
```
https://archive-api.open-meteo.com/v1/archive
  ?latitude=28.65
  &longitude=77.31
  &start_date=2022-01-01
  &end_date=2024-12-31
  &daily=temperature_2m_mean,windspeed_10m_mean,
         winddirection_10m_dominant,precipitation_sum,
         relativehumidity_2m_mean,boundary_layer_height
```

**Dùng library:** `openmeteo-requests` có sẵn retry + cache

**Chạy:**
```bash
python -m src.ingestion.fetch_weather
```

**Checklist hôm nay:**
- [ ] Air quality data đã verify (shape đúng)
- [ ] `fetch_weather.py` đã viết xong
- [ ] Script đang chạy (46 API calls, ~5 phút)
- [ ] `data/external/weather.parquet` đã có

---

## Thứ 5 — 2026-10-16: Fetch Industrial Data

### Buổi sáng: Download WRI GPPD

**Bước 1: Download thủ công**
- Vào: `https://datasets.wri.org/dataset/globalpowerplantdatabase`
- Download file: `global_power_plant_database.csv`
- Save vào: `data/external/global_power_plant_database.csv`

**Bước 2: Viết `src/ingestion/fetch_industrial.py`**

```python
# Filter logic:
df = pd.read_csv("data/external/global_power_plant_database.csv")

# 1. Chỉ giữ Ấn Độ
df = df[df["country_long"] == "India"]

# 2. Bounding box Delhi + 50km buffer
df = df[
    (df["latitude"]  >= 27.5) & (df["latitude"]  <= 29.5) &
    (df["longitude"] >= 76.0) & (df["longitude"] <= 78.5)
]

# 3. Chỉ fossil fuels
FOSSIL = ["Coal", "Oil", "Gas", "Petcoke", "Coke", "Waste"]
df = df[df["primary_fuel"].isin(FOSSIL)]

# 4. Drop missing coords + zero capacity
df = df.dropna(subset=["latitude", "longitude"])
df = df[df["capacity_mw"] > 0]

# 5. Save
df[["name","latitude","longitude","capacity_mw","primary_fuel"]]\
  .to_parquet("data/external/industrial.parquet", index=False)
```

**Chạy:**
```bash
python -m src.ingestion.fetch_industrial
```

**Checklist hôm nay:**
- [ ] WRI GPPD CSV đã download
- [ ] `fetch_industrial.py` đã viết xong
- [ ] `data/external/industrial.parquet` đã có
- [ ] Verify: in ra tên các nhà máy trong buffer

---

## Thứ 6 — 2026-10-17: Verify Toàn Bộ + Fix Issues

### Viết `src/ingestion/verify_data.py`

Script tổng hợp kiểm tra tất cả data trước khi chuyển sang Phase 2:

```
=== AIR QUALITY ===
□ Shape: expect ~42,000 rows × 9 cols
□ Date range: 2022-01-01 → 2024-12-31
□ Parameters: pm25, pm10, no2, o3, so2, co
□ Null count per parameter
□ Value range hợp lý (không có giá trị cực đoan)

=== WEATHER ===
□ Shape: expect ~46 stations × ~1,095 days × 6 variables
□ Date range: 2022-01-01 → 2024-12-31
□ Null count per variable
□ temperature range: -5°C → 50°C
□ wind_speed >= 0

=== INDUSTRIAL ===
□ Số nhà máy trong buffer: expect 5–20 nhà máy
□ Tất cả có coordinates hợp lệ
□ capacity_mw > 0
□ Chỉ fossil fuels

=== CACHE ===
□ delhi_locations.json: có locations
□ delhi_sensors.json: có sensors
```

**Checklist cuối tuần — Definition of Done:**
- [ ] `data/raw/delhi_raw.parquet` — shape ~42k rows
- [ ] `data/external/weather.parquet` — đủ 46 stations × 3 năm
- [ ] `data/external/industrial.parquet` — có nhà máy hợp lệ
- [ ] `data/.cache/` — có 2 file JSON
- [ ] Verify script chạy không có lỗi nghiêm trọng
- [ ] Update tracking trong `project_plan.md`: Phase 1 → 🟢 Hoàn thành

---

## Packages Cần Install Thứ 2

```bash
pip install lightgbm optuna shap openmeteo-requests geopy \
            scikit-learn matplotlib seaborn streamlit scipy \
            joblib plotly folium
```

---

## Files Sẽ Tạo Tuần Này

```
src/
  __init__.py
  ingestion/
    __init__.py
    openaq_client.py     ← Thứ 2
    fetch_air_quality.py ← Thứ 3
    fetch_weather.py     ← Thứ 4
    fetch_industrial.py  ← Thứ 5
    verify_data.py       ← Thứ 6

data/
  raw/
    delhi_raw.parquet    ← Thứ 3 (sau khi fetch xong)
  external/
    weather.parquet      ← Thứ 4
    industrial.parquet   ← Thứ 5
  .cache/
    delhi_locations.json ← Thứ 3
    delhi_sensors.json   ← Thứ 3
```

---

## Rủi ro Tuần Này

| Rủi ro | Xác suất | Xử lý |
|---|---|---|
| OpenAQ API rate limit | Trung bình | Retry logic + sleep 0.2s giữa calls |
| Fetch air quality mất > 1 ngày | Thấp | Resumable script — chạy lại từ chỗ dừng |
| WRI website down | Thấp | Mirror trên Kaggle: `datasets/global-power-plant-database` |
| Open-Meteo thiếu boundary_layer_height | Trung bình | Dùng `et0_fao_evapotranspiration` làm proxy tạm |
