# Tuần 3 — Phase 3: Feature Engineering + EDA
**2026-10-27 → 2026-10-31**

---

## Mục tiêu cuối tuần

- `data/features/train.parquet`, `val.parquet`, `test.parquet` — 24 features, sẵn sàng train
- `notebooks/eda.ipynb` — plots đủ dùng cho paper
- Không có data leakage

---

## Thứ 2 — 2026-10-27: Merge 3 nguồn

### Viết `src/features/build_features.py` — phần merge

```
1. Load air_quality.parquet → pivot wide: mỗi row = (date, station, pm25, pm10, no2, o3, so2, co)
2. Merge weather.parquet theo (date, location_name)
3. Tính industrial features (Haversine per station):
     - dist_nearest_plant_km  = khoảng cách đến nhà máy gần nhất
     - capacity_weighted_dist = Σ capacity_mw / distance²  (proximity-weighted load)
     - n_plants_50km          = số nhà máy trong 50km
```

> Note: industrial là data tĩnh (không có cột date) → join theo location_name, không theo date

**Checklist:**
- [ ] Mỗi row = 1 (date × station), không trùng
- [ ] Không có giá trị weather từ station khác bị merge nhầm
- [ ] 3 industrial features đã có

---

## Thứ 3 — 2026-10-28: Lag + Rolling features

### Tiếp tục `build_features.py` — phần lag/rolling

```python
# Target: pm25 ngày hôm sau (shift -1)
df["pm25_target"] = df.groupby("location_name")["pm25"].shift(-1)

# Lag features (per station)
for lag in [1, 2, 3, 7]:
    df[f"pm25_lag{lag}"] = df.groupby("location_name")["pm25"].shift(lag)

# Rolling stats (tính TRƯỚC khi shift để tránh leakage)
for window in [7, 14, 30]:
    df[f"pm25_roll{window}_mean"] = (
        df.groupby("location_name")["pm25"]
        .transform(lambda x: x.shift(1).rolling(window).mean())
    )
    df[f"pm25_roll{window}_std"] = (
        df.groupby("location_name")["pm25"]
        .transform(lambda x: x.shift(1).rolling(window).std())
    )
```

> ⚠️ `shift(1)` trước `rolling` là bắt buộc — tránh leakage (rolling không được nhìn thấy giá trị ngày hiện tại)

**Checklist:**
- [ ] `pm25_lag1` của ngày T = `pm25` của ngày T-1 ✓
- [ ] `pm25_roll7_mean` của ngày T không chứa giá trị ngày T ✓
- [ ] Không có future data leak

---

## Thứ 4 — 2026-10-29: Temporal + Cyclical features + Split

### Temporal features

```python
# Cyclical encoding (tránh 12→1, 7→1 bị coi là gần nhau)
df["month_sin"] = np.sin(2 * np.pi * df["date"].dt.month / 12)
df["month_cos"] = np.cos(2 * np.pi * df["date"].dt.month / 12)
df["dow_sin"]   = np.sin(2 * np.pi * df["date"].dt.dayofweek / 7)
df["dow_cos"]   = np.cos(2 * np.pi * df["date"].dt.dayofweek / 7)

# One-hot season
def get_season(month):
    if month in [12, 1, 2]:    return "winter"
    if month in [3, 4, 5]:     return "spring"
    if month in [6, 7, 8, 9]:  return "monsoon"
    return "autumn"

df = pd.get_dummies(df, columns=["season"], drop_first=True)
```

### Train/Val/Test split

```
Train : 2022-01-01 → 2024-03-31
Val   : 2024-04-01 → 2024-09-30
Test  : 2024-10-01 → 2025-12-31
```

```python
# Drop rows where target is NaN (last row per station)
df = df.dropna(subset=["pm25_target"])
```

**Checklist:**
- [ ] 24 features đúng theo ADR-003
- [ ] `train.parquet`, `val.parquet`, `test.parquet` đã lưu
- [ ] `df.shape[1]` == 24 features + target + metadata cols

---

## Thứ 5–6 — 2026-10-30–31: EDA Notebook

### `notebooks/eda.ipynb` — plots cho paper

```
Figure 1: Map 58 trạm Delhi (màu theo mean PM2.5)
Figure 2: Time series PM2.5 trung bình tất cả trạm (2022–2025)
Figure 3: Seasonal boxplot PM2.5 (winter/spring/monsoon/autumn)
Figure 4: Correlation heatmap (PM2.5 vs weather features)
Figure 5: PM2.5 distribution per station (violin plot, top 10 ô nhiễm nhất)
Figure 6: Missing data heatmap (station × parameter)
```

Lưu tất cả plots vào `reports/figures/` với tên rõ ràng: `fig1_station_map.png`...

---

## Files tạo tuần này

```
src/features/
  build_features.py

data/features/
  train.parquet
  val.parquet
  test.parquet

notebooks/
  eda.ipynb

reports/figures/
  fig1_station_map.png
  fig2_timeseries.png
  fig3_seasonal_boxplot.png
  fig4_correlation.png
  fig5_violin.png
  fig6_missing_heatmap.png
```

---

## Definition of Done

- [ ] `train.parquet` có ít nhất 50,000 rows
- [ ] Không có NaN trong 24 features (ngoại trừ pm10 — LightGBM handle native)
- [ ] 6 figures đã lưu vào `reports/figures/`
- [ ] Update tracking: Phase 3 → 🟢 Hoàn thành
