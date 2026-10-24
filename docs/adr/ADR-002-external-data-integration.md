# ADR-002: External Data Integration Strategy

**Status:** Accepted  
**Date:** 2026-10-10  
**Author:** [Tên nhóm]  
**Liên quan:** [[ADR-001-research-scope]]

---

## Context

ADR-001 đã xác định research question: *"Dữ liệu khí tượng và nguồn phát thải công nghiệp cải thiện độ chính xác dự đoán PM2.5 tại Delhi như thế nào?"*

Để trả lời câu hỏi này, pipeline cần bổ sung 2 nguồn data bên ngoài:
1. **Meteorological data** — các yếu tố thời tiết ảnh hưởng trực tiếp đến nồng độ PM2.5
2. **Industrial emission data** — vị trí và quy mô các nguồn phát thải cố định

OpenAQ data hiện có không chứa thông tin thời tiết. Không có weather features, model không thể giải thích được seasonal pattern quan trọng nhất của Delhi (winter temperature inversion, monsoon washout).

---

## Decisions

### 1. Nguồn Weather Data: Open-Meteo

**Chọn:** Open-Meteo Historical Weather API

**Lý do:**
- Free, không cần API key, không giới hạn calls
- Có Python library `openmeteo-requests` hỗ trợ sẵn
- Cung cấp `boundary_layer_height` — feature quan trọng nhất cho PM2.5 accumulation
- Đủ cho scope hội thảo; ghi rõ nguồn trong paper là được

**Variables cần fetch:**

| Variable | Tên trong API | Đơn vị | Lý do cần |
|---|---|---|---|
| Nhiệt độ TB ngày | `temperature_2m_mean` | °C | Temperature inversion |
| Tốc độ gió | `windspeed_10m_mean` | km/h | Dispersion pollutants |
| Hướng gió | `winddirection_10m_dominant` | degrees | Upwind/downwind |
| Lượng mưa | `precipitation_sum` | mm | Wet deposition — rửa PM2.5 |
| Độ ẩm | `relativehumidity_2m_mean` | % | Hygroscopic growth |
| Boundary layer height | `boundary_layer_height` | m | PM2.5 accumulation |

**Không chọn ERA5** vì: yêu cầu đăng ký, download file netCDF nặng, xử lý phức tạp — không tương xứng với scope hội thảo.

---

### 2. Weather Granularity: Per-Station

**Chọn:** Fetch weather theo tọa độ riêng của từng trạm (46 API calls)

**Lý do:**
- Các trạm phân tán trên vùng Delhi NCR rộng ~50km
- Trạm ở Gurugram (phía Nam) và Narela (phía Bắc) có microclimate khác nhau đáng kể
- Open-Meteo miễn phí nên 46 calls không có chi phí

**Không chọn city-center** vì: 1 điểm tọa độ không đại diện được cho 46 trạm phân tán, gây noise cho spatial features.

---

### 3. Industrial Data: WRI Global Power Plant Database

**Chọn:** WRI Global Power Plant Database (GPPD)

**Download:** `global_power_plant_database.csv` từ resourcewatch.org / datasets.wri.org

**Filter áp dụng:**
```python
country_long == "India"
latitude:  27.5°N → 29.5°N
longitude: 76.0°E → 78.5°E   # Delhi + buffer 50km
primary_fuel in ["Coal", "Oil", "Gas", "Petcoke"]  # Loại bỏ renewable
```

**Buffer 50km** — đủ bắt được nhà máy nhiệt điện lớn ở rìa Delhi NCR có ảnh hưởng khi gió mạnh. Buffer > 100km sẽ thêm noise nhiều hơn signal.

**Columns giữ lại:**
- `name`, `latitude`, `longitude`
- `capacity_mw` — quy mô nhà máy (proxy cho emission intensity)
- `primary_fuel` — loại nhiên liệu (coal > oil > gas về PM emission)

---

### 4. Industrial Feature Engineering: Distance + Wind (Option B)

**Chọn:** Đưa `dist_nearest_plant_km`, `wind_direction`, `wind_speed` vào model như 3 features độc lập — để LightGBM tự học interaction.

**Lý do:**
- LightGBM đủ mạnh để học interaction giữa distance và wind direction
- Không cần implement upwind formula phức tạp
- Dễ reproduce, dễ explain trong paper
- Nếu kết quả chưa đủ tốt, nâng lên Option C ở vòng sau

**Features industrial cụ thể:**

| Feature | Mô tả | Cách tính |
|---|---|---|
| `dist_nearest_plant_km` | Khoảng cách đến nhà máy gần nhất | Haversine distance |
| `n_plants_within_20km` | Số nhà máy trong vòng 20km | Count filter |
| `total_capacity_within_20km` | Tổng công suất nhà máy trong 20km | Sum `capacity_mw` |

**Không chọn Option A** (distance only): bỏ qua hoàn toàn wind direction — feature quan trọng.  
**Không chọn Option C** (upwind score tay): phức tạp không cần thiết cho scope này — để Future Work.

---

## Implementation Plan

```
Step 1: Fetch weather data
  Script: src/ingestion/fetch_weather.py
  Input:  data/.cache/delhi_locations.json (có sẵn tọa độ 46 trạm)
  Output: data/external/weather_delhi.parquet

Step 2: Download + process industrial data
  Script: src/ingestion/fetch_industrial.py
  Input:  global_power_plant_database.csv (download thủ công)
  Output: data/external/industrial_delhi.parquet

Step 3: Merge vào feature pipeline
  Script: src/features/build_features.py
  Input:  delhi_cleaned.parquet + weather_delhi.parquet + industrial_delhi.parquet
  Output: data/features/train_features.parquet
```

---

## Schema sau khi tích hợp

```
Mỗi row = (station, date)

--- Air Quality (đã có) ---
pm25_lag1, pm25_lag3, pm25_lag7
pm10_lag1
pm25_roll7_mean, pm25_roll14_mean, pm25_roll7_std
month, day_of_week, season

--- Weather (ADR-002) ---
temperature_mean
wind_speed
wind_direction
precipitation
humidity
boundary_layer_height

--- Industrial (ADR-002) ---
dist_nearest_plant_km
n_plants_within_20km
total_capacity_within_20km

--- Target ---
target_pm25_next_day
```

**Tổng: 21 features**

---

## Consequences

### Tích cực
- Weather features giải thích được seasonal pattern Delhi
- Industrial features capture được spatial variation giữa các trạm
- Per-station weather tăng accuracy cho trạm ở rìa NCR
- Schema đủ cho ablation study 4 tầng (ADR-001)

### Rủi ro & Mitigation

| Rủi ro | Mitigation |
|---|---|
| Open-Meteo thay đổi API | Pin version, cache kết quả vào parquet |
| WRI data thiếu nhà máy nhỏ | Ghi nhận là limitation trong paper |
| `boundary_layer_height` null một số ngày | Forward fill hoặc interpolate |
| 46 API calls mất thời gian | Cache vào file, không re-fetch nếu đã có |

---

## Alternatives Considered

| Option | Lý do không chọn |
|---|---|
| ERA5 thay Open-Meteo | Phức tạp, không tương xứng scope |
| City-center weather | Không đại diện cho trạm rìa NCR |
| Buffer 100km industrial | Noise nhiều hơn signal |
| Upwind score tay (Option C) | Để Future Work |
| EDGAR emission inventory | Gridded data phức tạp, khó merge với station data |
