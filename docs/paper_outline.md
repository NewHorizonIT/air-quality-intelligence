# Paper Outline — Hội Thảo Khoa Học

## Thông tin đề tài

**Tên đề tài (VI):**
Dự đoán nồng độ PM2.5 tại các trạm quan trắc Delhi sử dụng học máy
với tích hợp dữ liệu khí tượng và nguồn phát thải công nghiệp

**Tên đề tài (EN):**
Improving PM2.5 Forecasting Accuracy in Delhi Using Multi-Source Machine Learning:
Integrating Meteorological Factors and Industrial Emission Proximity

**Format:** IEEE — 6 đến 8 trang

---

## Cấu trúc bài báo

### Abstract (~150 từ)
- Bối cảnh: ô nhiễm PM2.5 tại Delhi
- Vấn đề: dự đoán chính xác PM2.5 ngày hôm sau
- Phương pháp: LightGBM + ablation study 4 tầng feature
- Kết quả chính: MAE, RMSE, R² (điền sau khi có kết quả)
- Đóng góp: weather + industrial proximity cải thiện X%

---

### 1. Introduction (~0.5 trang)
- Tầm quan trọng của chất lượng không khí với sức khỏe
- Delhi là một trong những thành phố ô nhiễm nhất thế giới
- Hạn chế của các phương pháp dự đoán hiện tại
- Research gap: ít nghiên cứu kết hợp cả meteorological + industrial proximity
- Contribution của paper này
- Cấu trúc bài báo

### 2. Related Work (~0.5 trang)
- ML cho dự đoán PM2.5 (tổng quan)
- Các nghiên cứu tại Delhi / Ấn Độ
- Sử dụng yếu tố khí tượng trong dự đoán AQI
- Source attribution / industrial emission proximity
- Gap chưa được giải quyết

### 3. Data & Study Area (~1 trang)
#### 3.1 Study Area
- Delhi NCR: vị trí địa lý, đặc điểm khí hậu 4 mùa
- Seasonal pattern: winter smog, Diwali spike, monsoon

#### 3.2 Air Quality Data
- Nguồn: OpenAQ v3 API
- 44 monitoring stations, bounding box Delhi NCR
- Parameters: PM2.5 (primary), PM10
- Thời gian: 2022–2024
- Preprocessing: cleaning, outlier removal, aggregation

#### 3.3 Meteorological Data
- Nguồn: Open-Meteo Historical API
- Variables: temperature, wind speed/direction, precipitation, humidity, boundary layer height
- Resolution: daily, per station coordinates

#### 3.4 Industrial Emission Data
- Nguồn: Global Power Plant Database (WRI)
- Filter: Delhi NCR + 50km buffer
- Derived feature: upwind impact score

### 4. Methodology (~1.5 trang)
#### 4.1 Feature Engineering
- Temporal features: lag (1, 3, 7 ngày), rolling mean/std (7, 14 ngày)
- Meteorological features
- Spatial-industrial features: distance + upwind/downwind calculation
- Seasonal encoding

#### 4.2 Experimental Design (Ablation Study)
| Experiment | Features | Mục đích |
|---|---|---|
| E1 | Persistence model | Baseline ngây thơ |
| E2 | Temporal only | Baseline ML |
| E3 | Temporal + Meteorological | Đo impact của weather |
| E4 | Temporal + Meteorological + Industrial | Đo impact của industrial |

#### 4.3 Model
- LightGBM Regressor: lý do chọn
- Hyperparameter tuning: time-series cross-validation
- Train/Validation/Test split (temporal):
  - Train: 2022-01-01 → 2023-09-30
  - Validation: 2023-10-01 → 2024-03-31
  - Test: 2024-04-01 → 2024-12-31

#### 4.4 Evaluation Metrics
- MAE (Mean Absolute Error) — đơn vị µg/m³
- RMSE (Root Mean Square Error)
- R² (Coefficient of Determination)
- MAPE (Mean Absolute Percentage Error)

### 5. Results & Discussion (~2 trang)
#### 5.1 Ablation Study Results
- Bảng so sánh 4 experiments theo 4 metrics
- Bar chart: MAE theo từng experiment

#### 5.2 Feature Importance (SHAP)
- Top features đóng góp nhiều nhất
- Weather vs temporal vs industrial: ai quan trọng hơn?

#### 5.3 Seasonal Analysis
- Model accuracy theo mùa (winter/monsoon/spring/autumn)
- Mùa nào khó predict nhất?

#### 5.4 Spatial Analysis
- Per-station error: trạm nào khó predict nhất?
- Correlation với khoảng cách đến nhà máy

#### 5.5 Discussion
- Giải thích tại sao boundary layer height là feature quan trọng
- Hạn chế: data coverage 2023–2024, thiếu real-time
- So sánh với related work

### 6. Conclusion (~0.25 trang)
- Tóm tắt contribution
- Kết quả chính (số cụ thể)
- Future work: real-time, multi-horizon, thêm traffic/crop burning data

---

## References (IEEE format)
- Xem thêm: docs/reference.md
- Cần tìm thêm: 8–12 paper liên quan

---

## Timeline

| Giai đoạn | Nội dung | Deadline |
|---|---|---|
| Data | Fetch weather + industrial data | TBD |
| ADR | Hoàn thiện ADR-001 đến ADR-006 | TBD |
| Features | Feature engineering hoàn chỉnh | TBD |
| Model | Train 4 experiments, evaluate | TBD |
| Writing | Draft paper | TBD |
| Review | Thầy review, chỉnh sửa | TBD |
| Submit | Nộp hội thảo | TBD |
