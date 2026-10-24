# Tuần 2 — Phase 2: Data Cleaning
**2026-10-20 → 2026-10-24**

---

## Mục tiêu cuối tuần

Toàn bộ data đã clean, đúng schema ADR-005, sẵn sàng vào feature engineering:
- `data/cleaned/air_quality.parquet` — O3 converted, capped, daily mean, WHO labels, cross-station flag
- `data/external/weather.parquet` — bounds validated, forward filled (overwrite in-place)
- `data/external/industrial.parquet` — deduplicated (overwrite in-place)

---

## Thứ 2 — 2026-10-20: clean_air_quality.py (phần 1)

### Viết `src/processing/clean_air_quality.py`

**Bước 1–4 của pipeline ADR-005:**

```
1. Convert O3 ppm → µg/m³  (× 2000)  ← TRƯỚC MỌI FILTER
2. Drop value < 0
3. Apply outlier caps:
     pm25=1000, pm10=2000, no2=600, o3=600, so2=500, co=10000
4. Aggregate daily mean per (location, date, parameter)
```

**Checklist hôm nay:**
- [ ] O3 convert đúng: rows có `unit == "ppm"` được nhân 2000
- [ ] Không còn giá trị âm
- [ ] Không còn giá trị vượt cap
- [ ] Sau aggregate: 1 row = 1 (date × station × parameter)

---

## Thứ 3 — 2026-10-21: clean_air_quality.py (phần 2)

**Bước 5–6 của pipeline ADR-005:**

```
5. WHO exceedance label:
     pm25=15, pm10=45, no2=25, o3=100, so2=40, co=4000  (µg/m³/day)
6. Cross-station suspicious flag:
     - Tìm cặp trạm cách nhau ≤ 5km (Haversine)
     - Với mỗi (date, parameter): ratio = max/min trong cặp
     - ratio > 5 → is_suspicious = True cho cả 2 trạm
```

**Checklist hôm nay:**
- [ ] Cột `exceeds_who` và `who_threshold` có giá trị đúng
- [ ] PM2.5 exceedance rate ở Delhi ~95% (high là bình thường)
- [ ] `is_suspicious` có giá trị, log % rows bị flag
- [ ] Output schema đúng ADR-005 (11 cột)

---

## Thứ 4 — 2026-10-22: clean_weather.py

### Viết `src/processing/clean_weather.py`

```python
WEATHER_BOUNDS = {
    "temperature":           (-5.0,   50.0),
    "wind_speed":            ( 0.0,  150.0),
    "precipitation":         ( 0.0,  300.0),
    "humidity":              ( 0.0,  100.0),
    "boundary_layer_height": ( 0.0, 4000.0),
}

# 1. Replace out-of-bounds → NaN
# 2. Forward fill per station, limit=3 ngày
```

> Note: `wind_direction` (0–360°) không filter bounds, không fill

**Checklist hôm nay:**
- [ ] Không còn nhiệt độ < -5°C hoặc > 50°C
- [ ] wind_speed >= 0
- [ ] Null % sau forward fill < 5% trên tất cả cột
- [ ] File overwrite in-place tại `data/external/weather.parquet`

---

## Thứ 5 — 2026-10-23: clean_industrial.py + Verify

### Viết `src/processing/clean_industrial.py`

```python
# 1. Confirm fossil fuels only (safety check)
# 2. Drop missing coords / zero capacity
# 3. Fill missing capacity_mw với median per fuel type
# 4. Dedup: cùng tọa độ ≤ 1km → giữ capacity cao hơn
```

### Verify toàn bộ cleaned data

```python
# Chạy:
python -m src.processing.verify_cleaned

# Check:
□ air_quality.parquet: shape, date range, null counts, value ranges
□ weather.parquet: null % < 5%, bounds hợp lệ
□ industrial.parquet: số nhà máy, không có duplicate
```

**Checklist hôm nay:**
- [ ] 3 scripts đã chạy thành công không có lỗi
- [ ] Tất cả file output tồn tại
- [ ] Verify script in ra ✓ cho tất cả checks

---

## Thứ 6 — 2026-10-24: Buffer + Update Tracking

- Fix mọi vấn đề phát hiện từ verify
- Update `project_plan.md`: Phase 2 → 🟢 Hoàn thành
- Ghi note về % suspicious rows, % WHO exceedance vào `docs/data_notes.md`

**Definition of Done:**
- [ ] `data/cleaned/air_quality.parquet` — đủ 11 cột, không null ở `value`
- [ ] `data/external/weather.parquet` — null < 5%
- [ ] `data/external/industrial.parquet` — không có duplicate
- [ ] Verify script chạy không có ✗

---

## Files Sẽ Tạo Tuần Này

```
src/
  processing/
    clean_air_quality.py   ← Thứ 2–3
    clean_weather.py       ← Thứ 4
    clean_industrial.py    ← Thứ 5
    verify_cleaned.py      ← Thứ 5

data/
  cleaned/
    air_quality.parquet    ← output của clean_air_quality.py
  external/
    weather.parquet        ← overwrite bởi clean_weather.py
    industrial.parquet     ← overwrite bởi clean_industrial.py
```

---

## Chạy Toàn Bộ Phase 2

```bash
python -m src.processing.clean_air_quality
python -m src.processing.clean_weather
python -m src.processing.clean_industrial
python -m src.processing.verify_cleaned
```

---

## Rủi Ro Tuần Này

| Rủi ro | Xử lý |
|---|---|
| Cross-station flag chậm (N² pairs) | 43 stations = ~900 pairs — acceptable |
| Forward fill weather tạo bias | Giới hạn limit=3 ngày theo ADR-005 |
| PM2.5 exceedance rate quá cao (~95%) | Đây là thực tế Delhi — ghi chú trong paper |
| Industrial dedup xóa nhầm nhà máy hợp lệ | Log trước/sau để verify thủ công |
