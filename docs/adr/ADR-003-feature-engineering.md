# ADR-003: Feature Engineering Strategy

**Status:** Accepted  
**Date:** 2026-10-10  
**Author:** [Tên nhóm]  
**Liên quan:** [[ADR-001-research-scope]] [[ADR-002-external-data-integration]]

---

## Context

ADR-001 xác định task là regression per-station dự đoán PM2.5 t+1.  
ADR-002 xác định 3 nguồn data: OpenAQ + Open-Meteo + WRI GPPD.

ADR này quyết định cách biến raw data thành feature matrix đưa vào model, bao gồm: lag selection, rolling statistics, temporal encoding, missing data handling, và train/val/test split strategy.

### Ràng buộc quan trọng từ data exploration
- 43/44 trạm chỉ có data năm 2022 → không thể dùng temporal split thông thường
- PM10 không có data năm 2023 → 1,105 nulls trong pm10_lag1
- PM2.5 thiếu 44 ngày rải rác trong 3 năm
- Mỗi lag thêm sẽ mất N rows đầu mỗi trạm → cần cân bằng

---

## Decisions

### 1. Lag Features

**Chọn: lag_1, lag_2, lag_3, lag_7**

```python
df["pm25_lag1"] = df["pm25"].shift(1)
df["pm25_lag2"] = df["pm25"].shift(2)
df["pm25_lag3"] = df["pm25"].shift(3)
df["pm25_lag7"] = df["pm25"].shift(7)
df["pm10_lag1"] = df["pm10"].shift(1)
```

**Lý do:**
- lag_1: predictive power cao nhất — PM2.5 có autocorrelation mạnh
- lag_2, lag_3: capture trend ngắn hạn 3 ngày (điển hình của pollution episode Delhi)
- lag_7: capture weekly pattern (traffic, industrial cycle)
- lag_14 không dùng: thêm ít giá trị, mất thêm 7 rows đầu mỗi trạm

Áp dụng per-station — shift() thực hiện trong group_by(location_name) để tránh data leakage giữa các trạm.

---

### 2. Rolling Statistics

**Chọn: roll7_mean, roll7_std, roll14_mean, roll30_mean**

```python
# shift(1) trước khi rolling để chỉ dùng past data
base = df["pm25"].shift(1)
df["pm25_roll7_mean"]  = base.rolling(7,  min_periods=3).mean()
df["pm25_roll7_std"]   = base.rolling(7,  min_periods=3).std()
df["pm25_roll14_mean"] = base.rolling(14, min_periods=7).mean()
df["pm25_roll30_mean"] = base.rolling(30, min_periods=14).mean()
```

**Lý do từng feature:**

| Feature | Ý nghĩa |
|---|---|
| `roll7_mean` | Mức ô nhiễm trung bình tuần qua — trend ngắn hạn |
| `roll7_std` | Độ biến động 7 ngày — pollution episode đang ổn định hay leo thang? |
| `roll14_mean` | Trend trung hạn |
| `roll30_mean` | Seasonal baseline — model biết đang ở giai đoạn nào trong năm |

**Quan trọng:** `.shift(1)` trước `rolling()` đảm bảo không có data leakage — rolling window chỉ nhìn vào quá khứ, không nhìn vào ngày hiện tại.

---

### 3. Temporal Encoding

**Chọn: Cyclical encoding (sin/cos) cho month và day_of_week**

```python
# Month
df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

# Day of week
df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

# Season: one-hot (4 categories rõ ràng, không tuần hoàn)
df = pd.get_dummies(df, columns=["season"], prefix="season")
# → season_winter, season_spring, season_monsoon, season_autumn
```

**Lý do chọn cyclical:**
- Ordinal encoding: model không biết tháng 12 và tháng 1 gần nhau → sai về mặt vật lý
- Cyclical: tháng 12 (sin≈-0.5, cos≈0.87) và tháng 1 (sin≈0.5, cos≈0.87) gần nhau trong không gian feature
- Phù hợp cả LightGBM lẫn Ridge baseline

**Season dùng one-hot** vì 4 mùa Delhi có ranh giới rõ ràng (winter/spring/monsoon/autumn), không cần encode tuần hoàn.

---

### 4. Missing Data Strategy

#### 4a. PM2.5 — 44 ngày thiếu rải rác

**Chọn: Linear interpolation per-station**

```python
df["pm25"] = (
    df.groupby("location_name")["pm25"]
    .transform(lambda x: x.interpolate(method="linear", limit=3))
)
```

`limit=3`: chỉ interpolate nếu gap ≤ 3 ngày liên tiếp. Gap dài hơn → giữ NaN, drop row đó.

**Lý do:** PM2.5 là time series liên tục — interpolate tạo ít artifact nhất. Forward fill sẽ làm lag features bị lệch (ngày bị fill sẽ có lag_1 = chính nó).

#### 4b. PM10 — null toàn bộ 2023/2024

**Chọn: Giữ NaN, để LightGBM xử lý natively**

```python
# Không impute pm10_lag1
# LightGBM tự routing samples có NaN xuống nhánh riêng
```

**Lý do:**
- LightGBM handle NaN natively — không cần impute
- Impute bằng median 2022 sẽ tạo bias: các trạm 2023/2024 sẽ "giả vờ" có PM10 pattern của 2022
- Drop feature sẽ mất thông tin PM10 của toàn bộ 2022

**Lưu ý với Ridge baseline:** Ridge không handle NaN — cần `SimpleImputer(strategy="median")` trong pipeline của Ridge, không áp dụng cho LightGBM.

---

### 5. Train/Validation/Test Split

Phải dùng **2 strategy khác nhau** do data bị lệch:

#### 5a. 43 trạm (chỉ có 2022) — Time-Series Cross-Validation

```
Expanding window CV, 3 folds:

Fold 1: Train Jan–May 2022  | Val Jun–Jul 2022
Fold 2: Train Jan–Jul 2022  | Val Aug–Sep 2022
Fold 3: Train Jan–Sep 2022  | Val Oct–Dec 2022
```

Dùng để: tune hyperparameter LightGBM, chọn features tốt nhất.

#### 5b. Trạm "New Delhi" (2022–2024) — Temporal Split

```
Train:      2022-01-01 → 2023-09-30   (637 ngày)
Validation: 2023-10-01 → 2024-03-31   (183 ngày)  ← tune threshold
Test:       2024-04-01 → 2024-12-31   (275 ngày)  ← report final metrics
```

Test set bao gồm:
- Monsoon 2024 (Apr–Sep): PM2.5 thấp — test model có underfit không
- Winter onset 2024 (Oct–Dec): PM2.5 tăng mạnh — test model có catch được spike không

**Final metrics trong paper** lấy từ 5b — đây là số liệu report chính thức.

---

## Feature Matrix Hoàn Chỉnh

```
--- Lag Features (5) ---
pm25_lag1, pm25_lag2, pm25_lag3, pm25_lag7
pm10_lag1  (NaN cho 2023–2024)

--- Rolling Statistics (4) ---
pm25_roll7_mean, pm25_roll7_std
pm25_roll14_mean, pm25_roll30_mean

--- Temporal (6) ---
month_sin, month_cos
dow_sin, dow_cos
season_winter, season_spring, season_monsoon, season_autumn

--- Meteorological / ADR-002 (6) ---
temperature_mean, wind_speed, wind_direction
precipitation, humidity, boundary_layer_height

--- Industrial / ADR-002 (3) ---
dist_nearest_plant_km
n_plants_within_20km
total_capacity_within_20km

--- Target ---
target_pm25_next_day
```

**Tổng: 24 features + 1 target**

---

## Consequences

### Tích cực
- Cyclical encoding đúng về mặt vật lý — tháng 12 và tháng 1 gần nhau
- shift(1) trước rolling đảm bảo không data leakage
- LightGBM native NaN handling tránh imputation bias cho PM10
- 2 split strategy tận dụng được toàn bộ data hiện có

### Rủi ro & Mitigation

| Rủi ro | Mitigation |
|---|---|
| Data leakage qua lag nếu không group_by station | Luôn apply shift() trong groupby |
| roll30_mean thiếu data đầu mỗi trạm | min_periods=14, drop rows thiếu |
| Ridge không handle NaN của pm10_lag1 | Dùng SimpleImputer trong Ridge pipeline riêng |
| Test set chỉ có 1 trạm | Ghi nhận là limitation trong paper |

---

## Alternatives Considered

| Option | Lý do không chọn |
|---|---|
| lag_14 | Thêm ít giá trị, mất thêm data |
| Ordinal encoding month | Tháng 12 và tháng 1 bị coi là xa nhau |
| Forward fill PM2.5 | Gây lệch lag features |
| Impute PM10 bằng median | Tạo bias cho 2023–2024 |
| Random CV split | Data leakage — model nhìn thấy tương lai |
