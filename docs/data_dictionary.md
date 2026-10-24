# Data Dictionary

## 1. Raw Data — `data/raw/delhi_raw.parquet`

| Trường | Kiểu | Đơn vị | Mô tả |
|---|---|---|---|
| `datetime` | datetime64[us, UTC] | — | Timestamp UTC của đầu ngày theo IST. `2021-12-31 18:30 UTC` = `2022-01-01 00:00 IST`. Cần convert sang Asia/Kolkata trước khi dùng. |
| `value` | float64 | µg/m³ | Giá trị đo được (daily aggregate/mean). Có thể âm (sensor lỗi) hoặc cực lớn (sensor glitch). |
| `parameter` | str | — | Chất ô nhiễm: `pm25`, `pm10`, `no2`, `o3`, `so2`, `co` |
| `unit` | str | — | Đơn vị đo. Hầu hết là µg/m³. **Ngoại lệ: O3 có một số rows đơn vị `ppm`** — cần convert (1 ppm O3 ≈ 2000 µg/m³). |
| `sensor_id` | int64 | — | ID thiết bị đo (OpenAQ). Mỗi sensor chỉ đo 1 parameter. Không dùng làm feature. |
| `location_id` | int64 | — | ID trạm quan trắc (OpenAQ). Một location có nhiều sensors. |
| `location_name` | str | — | Tên trạm + agency vận hành. VD: `"Anand Vihar, Delhi - DPCC"` |
| `latitude` | float64 | degrees | Vĩ độ trạm. Dùng cho spatial features. |
| `longitude` | float64 | degrees | Kinh độ trạm. Dùng cho spatial features. |

### Agencies trong location_name
| Suffix | Tên đầy đủ | Ghi chú |
|---|---|---|
| DPCC | Delhi Pollution Control Committee | Chính quyền Delhi |
| CPCB | Central Pollution Control Board | Trung ương Ấn Độ |
| IMD | India Meteorological Department | Khí tượng quốc gia |
| IITM | Indian Institute of Tropical Meteorology | Nghiên cứu |
| HSPCB | Haryana State Pollution Control Board | Bang Haryana |
| UPPCB | Uttar Pradesh Pollution Control Board | Bang Uttar Pradesh |

### Data coverage issues
| Parameter | Thời gian có data | Ghi chú |
|---|---|---|
| pm25 | 2022–2024 | 43 trạm chỉ có 2022; "New Delhi" có đủ 3 năm |
| pm10 | 2022, 2024 | Không có 2023 |
| no2, o3, so2, co | 2022 only | Ngừng sync lên OpenAQ sau tháng 10/2022 |

---

## 2. Cleaned Data — `data/cleaned/delhi_cleaned.parquet`

Long format — mỗi row là (station, date, parameter).

| Trường | Kiểu | Mô tả |
|---|---|---|
| `date` | datetime64[ns] | Ngày theo IST (đã convert từ UTC) |
| `location_id` | int64 | ID trạm |
| `location_name` | str | Tên trạm |
| `latitude` | float64 | Vĩ độ |
| `longitude` | float64 | Kinh độ |
| `parameter` | str | Chất ô nhiễm |
| `unit` | str | Đơn vị |
| `value` | float64 | Giá trị đã clean (đã loại âm và outlier) |
| `exceeds_who` | bool | True nếu vượt WHO AQG 2021 threshold |
| `who_threshold` | float64 | Ngưỡng WHO tương ứng (µg/m³) |

### WHO AQG 2021 Thresholds
| Parameter | Threshold (µg/m³) | Ghi chú |
|---|---|---|
| PM2.5 | 15.0 | 24-hour mean |
| PM10 | 45.0 | 24-hour mean |
| NO2 | 25.0 | 24-hour mean |
| O3 | 100.0 | peak season |
| SO2 | 40.0 | 24-hour mean |
| CO | 4000.0 | 4 mg/m³ → µg/m³ |

---

## 3. Combined Data — `data/cleaned/delhi_combined.parquet`

Wide format — mỗi row là (station, date), mỗi parameter là 1 cột.

| Trường | Kiểu | Mô tả |
|---|---|---|
| `date` | datetime64[ns] | Ngày |
| `location_name` | str | Tên trạm |
| `pm25` | float64 | Giá trị PM2.5 (µg/m³) |
| `pm10` | float64 | Giá trị PM10 (µg/m³) |
| `no2` | float64 | Giá trị NO2 (µg/m³) |
| `o3` | float64 | Giá trị O3 (µg/m³) |
| `so2` | float64 | Giá trị SO2 (µg/m³) |
| `co` | float64 | Giá trị CO (µg/m³) |

---

## 4. Training Data (sẽ build) — `data/features/train_features.parquet`

Wide format — mỗi row là (station, date) với đầy đủ features và target.

### Features hiện tại (temporal)
| Trường | Mô tả |
|---|---|
| `pm25_lag1` | PM2.5 ngày hôm qua (t-1) |
| `pm25_lag3` | PM2.5 ngày t-3 |
| `pm25_lag7` | PM2.5 ngày t-7 |
| `pm10_lag1` | PM10 ngày hôm qua |
| `pm25_roll7_mean` | Trung bình 7 ngày qua |
| `pm25_roll14_mean` | Trung bình 14 ngày qua |
| `pm25_roll7_std` | Độ lệch chuẩn 7 ngày qua |
| `month` | Tháng (1–12) |
| `day_of_week` | Ngày trong tuần (0=Mon, 6=Sun) |
| `season` | Mùa: winter/spring/monsoon/autumn |

### Features cần bổ sung (meteorological)
| Trường | Nguồn | Mô tả |
|---|---|---|
| `temperature_mean` | Open-Meteo | Nhiệt độ trung bình ngày (°C) |
| `wind_speed` | Open-Meteo | Tốc độ gió trung bình (km/h) |
| `wind_direction` | Open-Meteo | Hướng gió (0–360°, 0=Bắc) |
| `precipitation` | Open-Meteo | Lượng mưa (mm) |
| `humidity` | Open-Meteo | Độ ẩm tương đối (%) |
| `boundary_layer_height` | Open-Meteo | Chiều cao lớp biên hành tinh (m) |

### Features cần bổ sung (industrial)
| Trường | Nguồn | Mô tả |
|---|---|---|
| `dist_nearest_plant_km` | WRI GPPD | Khoảng cách đến nhà máy điện gần nhất (km) |
| `upwind_impact_score` | Tính từ WRI + wind_direction | Mức độ ảnh hưởng từ nguồn upwind |

### Target
| Trường | Mô tả |
|---|---|
| `target_pm25_next_day` | PM2.5 ngày hôm sau (µg/m³) — giá trị cần predict |

---

## 5. External Data (cần fetch)

### Weather — Open-Meteo
- API: `https://archive-api.open-meteo.com/v1/archive`
- Parameters: temperature_2m_mean, windspeed_10m_mean, winddirection_10m_dominant, precipitation_sum, relativehumidity_2m_mean, boundary_layer_height
- Resolution: daily
- Cách dùng: gọi theo tọa độ từng trạm

### Industrial — WRI Global Power Plant Database
- File: `global_power_plant_database.csv`
- Download: resourcewatch.org / datasets.wri.org
- Filter: country_long == "India", trong bounding box 76.0°E–78.0°E, 27.5°N–29.5°N
- Columns cần: name, latitude, longitude, capacity_mw, primary_fuel
