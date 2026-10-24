# ADR-005: Data Quality & Cleaning Strategy

**Status:** Accepted (Updated 2026-10-13)
**Date:** 2026-10-10  
**Author:** [Tên nhóm]  
**Liên quan:** [[ADR-001-research-scope]] [[ADR-002-external-data-integration]] [[ADR-003-feature-engineering]]

---

## Context

Project sử dụng 3 nguồn data (ADR-002): OpenAQ, Open-Meteo, WRI GPPD. Mỗi nguồn có các vấn đề chất lượng riêng cần xử lý trước khi feature engineering.

**Vấn đề phát hiện từ exploration raw data ban đầu:**
- O3 có 2 đơn vị: `µg/m³` và `ppm`
- CO có giá trị 1.5×10²⁵ — sensor glitch rõ ràng
- Negative values trên nhiều parameters — sensor calibration error

**Vấn đề bổ sung sau khi extend fetch đến 2025 (124,161 rows, 59 stations):**
- CO, NO2, SO2 từ sensors mới có unit `ppb` — cần convert sang µg/m³
- CO "ppb" thực tế bị mislabel: giá trị median 1.0 khớp ppm hơn ppb → convert × 1,145
- Extreme negative values mới: NO2 = −1,540; O3 = −1,990; PM2.5 = −4,210 (sensor glitch)
- 1 station "East Arjun Nagar" chỉ có 2 ngày → drop

Thầy hướng dẫn đề xuất bổ sung cross-station consistency check để phát hiện sensor báo sai.

---

## Decisions

### Nguồn 1: OpenAQ Air Quality Data

#### 1.0 Drop stations < 30 ngày

**Chọn:** Drop station nếu tổng số ngày có dữ liệu < 30 — không đủ để học pattern.

```python
MIN_DAYS = 30
days_per_station = df.groupby("location_name")["date"].nunique()
valid_stations = days_per_station[days_per_station >= MIN_DAYS].index
df = df[df["location_name"].isin(valid_stations)]
# → Drop "East Arjun Nagar" (2 ngày)
```

---

#### 1.1 Unit Conversion — Convert tất cả về µg/m³ TRƯỚC mọi filter

**Lý do:** WHO AQG 2021 dùng µg/m³. Mọi filter, cap, và label đều dựa trên µg/m³. Convert trước để tránh drop nhầm giá trị hợp lệ.

**O3 ppm → µg/m³** (64 rows):
```python
mask = (df["parameter"] == "o3") & (df["unit"] == "ppm")
df.loc[mask, "value"] *= 2000   # 1 ppm O3 = 2000 µg/m³ @ 25°C
df.loc[mask, "unit"] = "µg/m³"
```

**NO2 ppb → µg/m³** (13,777 rows):
```python
mask = (df["parameter"] == "no2") & (df["unit"] == "ppb")
df.loc[mask, "value"] *= 1.882  # 1 ppb NO2 = 1.882 µg/m³ @ 25°C
df.loc[mask, "unit"] = "µg/m³"
```

**SO2 ppb → µg/m³** (11,452 rows):
```python
mask = (df["parameter"] == "so2") & (df["unit"] == "ppb")
df.loc[mask, "value"] *= 2.619  # 1 ppb SO2 = 2.619 µg/m³ @ 25°C
df.loc[mask, "unit"] = "µg/m³"
```

**CO ppb → µg/m³** (13,402 rows — mislabeled ppm):
```python
mask = (df["parameter"] == "co") & (df["unit"] == "ppb")
df.loc[mask, "value"] *= 1145   # Treat "ppb" as ppm: 1 ppm CO = 1145 µg/m³
df.loc[mask, "unit"] = "µg/m³"
```

> **Lý do CO × 1145:** CO "ppb" có median = 1.0, trong khi CO µg/m³ median = 1,010 µg/m³.
> 1.0 × 1145 = 1,145 µg/m³ ≈ 1,010 — khớp. Nếu dùng ppb thật (× 1.145): 1.0 ppb = 1.1 µg/m³ — quá thấp so với thực tế Delhi.
> Kết luận: sensor label sai, giá trị thực là ppm.

**Conversion factors tham chiếu (25°C, 1 atm):**

| Parameter | Unit gốc | Factor | Nguồn |
|---|---|---|---|
| O3 | ppm | × 2,000 | WHO/EPA standard |
| NO2 | ppb | × 1.882 | Molecular weight 46 g/mol |
| SO2 | ppb | × 2.619 | Molecular weight 64 g/mol |
| CO | ppb* | × 1,145 | *Mislabeled ppm; MW 28 g/mol |

---

#### 1.2 Outlier Caps

Distribution thực tế từ raw data:

| Parameter | p99 | Max thực tế | Cap | Lý do |
|---|---|---|---|---|
| pm25 | 348 | 5,620 | **1,000** | Delhi Diwali/winter có thể đạt 400–900 thật |
| pm10 | 534 | 7,220 | **2,000** | Bão bụi có thể đẩy PM10 rất cao |
| no2 | 118 | 543 | **600** | Nâng từ 500 — max thực tế 543 |
| o3 | 113 | 1,090 | **600** | Nâng từ 500 — sau convert ppm, O3 Delhi hiếm > 200 |
| so2 | 66 | 362 | **500** | Giữ nguyên — margin đủ rộng |
| co | 3,660 | 1.5×10²⁵ | **10,000** | Giảm từ 50,000 — max hợp lệ thực tế ~8,800 |

```python
OUTLIER_CAPS = {
    "pm25": 1000.0,
    "pm10": 2000.0,
    "no2":   600.0,
    "o3":    600.0,
    "so2":   500.0,
    "co":  10000.0,
}
df = df[df["value"] <= OUTLIER_CAPS[df["parameter"]]]
```

---

#### 1.3 Negative Values

**Chọn:** Drop tất cả `value < 0` — không có ý nghĩa vật lý với bất kỳ parameter nào.

```python
df = df[df["value"] >= 0]
```

---

#### 1.4 Cross-Station Consistency Check — Soft Flag

**Chọn:** Soft flag `is_suspicious = True/False` — không drop, chỉ đánh dấu.

```python
# Với mỗi (date, parameter):
# 1. Tìm cặp trạm cách nhau ≤ 5km (Haversine distance)
# 2. Tính ratio = max(value) / min(value) trong cặp
# 3. Nếu ratio > 5 → flag cả 2 trạm là suspicious

SPATIAL_THRESHOLD_KM  = 5.0
VALUE_RATIO_THRESHOLD = 5.0
```

**Lý do soft flag thay vì drop:**
- Dataset ít (~8,000 rows) — drop thêm ảnh hưởng training
- Cho phép phân tích phụ trong paper: accuracy có thấp hơn trên suspicious rows không?
- Address trực tiếp đề xuất của thầy hướng dẫn về cross-station comparison

---

### Nguồn 2: Open-Meteo Weather Data

#### 2.1 Missing Values

```python
# Forward fill tối đa 3 ngày liên tiếp per station
df[weather_cols] = (
    df.groupby("location_name")[weather_cols]
    .transform(lambda x: x.fillna(method="ffill", limit=3))
)
# Gap > 3 ngày: giữ NaN → drop row đó trong feature engineering
```

#### 2.2 Outlier Bounds

Giá trị hợp lệ cho Delhi NCR:

| Variable | Min | Max | Cơ sở |
|---|---|---|---|
| temperature | -5°C | 50°C | Delhi record: -2.2°C đến 48°C |
| wind_speed | 0 | 150 km/h | Bão mạnh nhất Ấn Độ ~140 km/h |
| wind_direction | 0° | 360° | Không filter |
| precipitation | 0 | 300 mm/day | Monsoon extreme Delhi |
| humidity | 0% | 100% | Tự nhiên |
| boundary_layer_height | 0 | 4,000 m | Điển hình 0–3,000m |

```python
WEATHER_BOUNDS = {
    "temperature":            (-5,   50),
    "wind_speed":             ( 0,  150),
    "precipitation":          ( 0,  300),
    "humidity":               ( 0,  100),
    "boundary_layer_height":  ( 0, 4000),
}
for col, (lo, hi) in WEATHER_BOUNDS.items():
    df.loc[df[col] < lo, col] = np.nan
    df.loc[df[col] > hi, col] = np.nan
```

`boundary_layer_height = 0` là hợp lệ (stable atmosphere ban đêm/sáng sớm) — không drop.

---

### Nguồn 3: WRI Global Power Plant Database

#### 3.1 Filter Rules

```python
# Drop thiếu tọa độ — không thể tính distance
df = df.dropna(subset=["latitude", "longitude"])

# Drop nhà máy không hoạt động
df = df[df["capacity_mw"] > 0]

# Drop renewable — không phát thải PM
FOSSIL_FUELS = ["Coal", "Oil", "Gas", "Petcoke", "Coke", "Waste"]
df = df[df["primary_fuel"].isin(FOSSIL_FUELS)]

# Drop duplicate (cùng tên + tọa độ gần nhau ≤ 1km)
# Giữ row có capacity_mw cao hơn
```

#### 3.2 Missing capacity_mw

```python
# Fill bằng median của cùng primary_fuel
df["capacity_mw"] = df.groupby("primary_fuel")["capacity_mw"].transform(
    lambda x: x.fillna(x.median())
)
```

---

## Thứ Tự Pipeline Hoàn Chỉnh

```
┌─────────────────────────────────────────────────────┐
│  OPENAQ RAW DATA                                    │
│  1. Convert O3 ppm → µg/m³          (trước filter) │
│  2. Drop value < 0                                  │
│  3. Apply outlier caps                              │
│  4. Aggregate per (location, date)  → daily mean   │
│  5. Add WHO exceedance label                        │
│  6. Cross-station suspicious flag                   │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│  OPEN-METEO WEATHER DATA                            │
│  1. Validate bounds per variable                    │
│  2. Forward fill missing ≤ 3 ngày                  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│  WRI GPPD INDUSTRIAL DATA                           │
│  1. Drop missing coordinates                        │
│  2. Drop capacity_mw ≤ 0                           │
│  3. Drop renewable fuels                            │
│  4. Fill missing capacity bằng median               │
│  5. Deduplicate                                     │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
              Cleaned Data → Feature Engineering (ADR-003)
```

---

## Output Schema

### `data/cleaned/air_quality.parquet` — long format

| Cột | Kiểu | Mô tả |
|---|---|---|
| `date` | date | Ngày (IST) |
| `location_id` | int | ID trạm OpenAQ |
| `location_name` | str | Tên trạm |
| `latitude` | float | Vĩ độ |
| `longitude` | float | Kinh độ |
| `parameter` | str | pm25/pm10/no2/o3/so2/co |
| `unit` | str | µg/m³ (đã chuẩn hóa) |
| `value` | float | Giá trị đã clean |
| `exceeds_who` | bool | True nếu vượt WHO AQG 2021 |
| `who_threshold` | float | Ngưỡng WHO tương ứng |
| `is_suspicious` | bool | True nếu flagged bởi cross-station check |

### `data/external/weather.parquet`

| Cột | Kiểu | Mô tả |
|---|---|---|
| `date` | date | Ngày |
| `location_name` | str | Tên trạm |
| `temperature` | float | °C |
| `wind_speed` | float | km/h |
| `wind_direction` | float | degrees |
| `precipitation` | float | mm |
| `humidity` | float | % |
| `boundary_layer_height` | float | m |

### `data/external/industrial.parquet`

| Cột | Kiểu | Mô tả |
|---|---|---|
| `name` | str | Tên nhà máy |
| `latitude` | float | Vĩ độ |
| `longitude` | float | Kinh độ |
| `capacity_mw` | float | Công suất MW |
| `primary_fuel` | str | Loại nhiên liệu |

---

## Consequences

### Tích cực
- Convert O3 trước filter — không mất dữ liệu hợp lệ
- Cap CO giảm xuống 10,000 — sát thực tế hơn
- Soft flag giữ toàn bộ data, mở ra phân tích phụ trong paper
- Weather bounds dựa trên climate record của Delhi — không tùy tiện
- GPPD filter loại bỏ renewable — chỉ giữ nguồn phát thải thật

### Rủi ro & Mitigation

| Rủi ro | Mitigation |
|---|---|
| Hệ số 2000 cho O3 chỉ đúng ở 25°C | Ghi nhận assumption trong paper |
| Forward fill weather tạo bias nếu gap dài | Giới hạn limit=3 ngày |
| Suspicious flag chưa có ground truth validate | Report % rows bị flag trong paper |
| WRI GPPD có thể thiếu nhà máy nhỏ | Ghi nhận là limitation |
| Cap CO 10,000 có thể drop giá trị hợp lệ cực cao | Log số rows bị drop để kiểm tra |

---

## Alternatives Considered

| Option | Lý do không chọn |
|---|---|
| Convert O3 sau filter | Mất dữ liệu ppm hợp lệ |
| CO cap giữ 50,000 | Quá rộng so với thực tế max ~8,800 |
| Drop suspicious rows | Dataset ít, mất thêm data ảnh hưởng training |
| Không clean weather data | Boundary layer height = 0 hợp lệ nhưng temperature < -5°C thì không |
| Giữ renewable trong GPPD | Hydro/Solar/Wind không phát thải PM — noise thuần túy |
