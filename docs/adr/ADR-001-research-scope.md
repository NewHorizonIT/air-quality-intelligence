# ADR-001: Research Scope & Prediction Target

**Status:** Accepted (Updated 2026-10-13)
**Date:** 2026-10-10  
**Author:** [Tên nhóm]

---

## Context

Project Air Quality Intelligence Platform thu thập dữ liệu chất lượng không khí tại Delhi từ OpenAQ v3 API. Nhóm cần xác định rõ phạm vi nghiên cứu và target dự đoán trước khi bắt đầu feature engineering và training.

### Phát hiện từ data exploration (sau khi fetch 2022–2025)

**Update 2026-10-13 — sau khi extend fetch đến 2025:**

| Chỉ số | Giả định ban đầu | Thực tế sau fetch |
|---|---|---|
| Tổng stations | 44 | **59** |
| Stations chỉ có 2022 | 43 | **3** (ITO, Anand Vihar cũ, Sector-16A Faridabad) |
| Stations có 2022–2025 | 1 | **43** trạm chính |
| Stations mới từ 2025 | 0 | **13** (xuất hiện từ Feb 2025) |
| New Delhi coverage | 2022–2024 | 2022–2025 (1,378 ngày) |
| Total rows | ~8,000 | **124,161** |

Phát hiện thêm về data quality:
- CO, NO2, SO2 có unit "ppb" từ các sensors mới (cần convert — xem ADR-005)
- Extreme negative values tại một số trạm (sensor glitch)
- 1 trạm "East Arjun Nagar" chỉ có 2 ngày → sẽ drop ở cleaning

---

## Decision

### 1. Task Type
**Chọn: Regression + derive Classification**

- Train regression để dự đoán giá trị PM2.5 cụ thể (µg/m³)
- Derive binary label từ kết quả: nếu predicted > 15 µg/m³ → exceeds WHO
- Lý do: regression cho nhiều thông tin hơn classification; imbalanced label (~95% exceed) gây khó khăn nếu train classification trực tiếp

### 2. Prediction Horizon
**Chọn: t+1 (ngày mai)**

- Dự đoán PM2.5 ngày hôm sau
- t+3 và t+7 để làm Future Work
- Lý do: accuracy cao nhất, usefulness cao nhất cho hành động ngay

### 3. Granularity
**Chọn: Per-station**

- Dự đoán riêng cho từng trạm, không aggregate về city-level
- Lý do: capture được spatial variation, address ý kiến thầy về so sánh trạm

### 4. Data Strategy — Updated
**Chọn: Unified dataset 59 trạm × 2022–2025**

Không còn cần phân chia Dataset A/B vì hầu hết stations giờ có data đa năm.

**Dataset chính:**
- **59 trạm**, date range **2022-01-01 → 2025-12-31**
- 124,161 rows raw (trước cleaning)
- Drop stations < 30 ngày (East Arjun Nagar — 2 ngày)

**Temporal split (trên toàn dataset):**
```
Train : 2022-01-01 → 2024-03-31
Val   : 2024-04-01 → 2024-09-30
Test  : 2024-10-01 → 2025-12-31
```

**Spatial cross-validation:** Time-series CV cho toàn bộ 58 trạm (sau khi drop 1).

### 5. Research Question
**Chính thức:**
> "Dữ liệu khí tượng và nguồn phát thải công nghiệp cải thiện độ chính xác dự đoán PM2.5 tại Delhi như thế nào?"

---

## Scope

### Trong scope
- Dự đoán PM2.5 t+1 per-station
- 58 trạm Delhi NCR (2022–2025)
- Ablation study: 4 tầng feature groups
- Feature importance (SHAP)
- Cross-station comparison (đặc biệt ý nghĩa hơn với 59 trạm)

### Ngoài scope
- Real-time prediction
- Dự đoán NO2/O3/SO2/CO làm target chính
- Horizon > t+1
- Causal inference
- Production deployment

---

## Consequences

### Tích cực
- Dataset phong phú hơn nhiều so với giả định ban đầu (124k rows vs ~8k)
- 4 năm data (2022–2025) cho temporal generalization tốt hơn
- 13 stations mới tăng spatial coverage đặc biệt cho năm 2025
- Không cần dual-dataset strategy phức tạp

### Rủi ro & Mitigation

| Rủi ro | Mitigation |
|---|---|
| Stations mới 2025 chỉ có ~300 ngày | Vẫn đủ cho test set; ghi nhận trong paper |
| ppb unit conversion CO/NO2/SO2 có thể sai factor | Validate sau convert: median phải khớp kỳ vọng Delhi |
| 3 stations còn lại chỉ có 2022 | Giữ lại cho train set, không ảnh hưởng test |

---

## Alternatives Considered

| Option | Lý do không chọn |
|---|---|
| Giữ dual dataset A/B | Không cần thiết — hầu hết stations giờ có 2022–2025 |
| City-level aggregate | Mất spatial dimension |
| Classification only | Imbalanced ~95%, mất thông tin định lượng |
| Focus chỉ "New Delhi" 3 năm | Chỉ 1 trạm, không có spatial analysis |
| Multi-horizon (t+1, t+3, t+7) | Tăng complexity không cần thiết cho scope hội thảo |
