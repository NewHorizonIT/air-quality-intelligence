# ADR-007: Application Layer

**Status:** Accepted  
**Date:** 2026-10-10  
**Author:** [Tên nhóm]  
**Liên quan:** [[ADR-001-research-scope]] [[ADR-004-model-selection-evaluation]] [[ADR-006-storage-layer]]

---

## Context

Sau khi có model hoàn chỉnh, project cần một lớp ứng dụng để:
1. **Demo kết quả** tại hội thảo khoa học — interactive, trực quan
2. **Analytics dashboard** — visualize data và model performance cho paper

README đã đề cập Power BI. Cần quyết định rõ dùng gì, build gì, và scope đến đâu.

---

## Decisions

### 1. Loại Ứng Dụng

**Chọn: Streamlit (web app) + Power BI (dashboard)**

Hai công cụ phục vụ 2 mục đích khác nhau — không thay thế nhau:

| | Streamlit | Power BI |
|---|---|---|
| **Mục đích** | Demo model prediction | Analytics & visualization |
| **Người dùng** | Reviewer, hội thảo | Tác giả, báo cáo |
| **Input** | User chọn trạm + ngày | Data có sẵn |
| **Output** | PM2.5 dự đoán + SHAP | Charts, trends, heatmap |
| **Khi build** | Sau khi có model | Sau khi có cleaned data |

---

### 2. Streamlit Web App

**Framework:** Streamlit — Python thuần, không cần frontend knowledge, deploy trong 1 ngày.

**Cấu trúc 3 trang:**

#### Trang 1: Dashboard Overview
```
- Bản đồ 46 trạm Delhi (màu theo PM2.5 level hôm nay)
- Time series PM2.5 trung bình Delhi theo thời gian
- WHO exceedance rate theo mùa (bar chart)
- Top 5 trạm ô nhiễm nhất
```

#### Trang 2: Prediction Demo ← Trang quan trọng nhất
```
- Dropdown: chọn trạm quan trắc
- Date picker: chọn ngày muốn dự đoán
- Button: "Dự đoán PM2.5 ngày mai"
- Output:
    + Giá trị PM2.5 dự đoán (µg/m³)
    + Nhãn WHO: AN TOÀN / NGUY HIỂM
    + Confidence range (±MAE)
    + SHAP waterfall chart: giải thích tại sao model ra kết quả đó
```

#### Trang 3: Model Comparison
```
- Bảng ablation study: Persistence / Ridge / Exp1 / Exp2 / Exp3
- Bar chart MAE theo experiment
- SHAP feature importance (top 10)
- Seasonal MAE breakdown
```

**Stack kỹ thuật:**
```python
streamlit          # web framework
plotly             # interactive charts
folium / pydeck    # bản đồ
shap               # SHAP plots
pandas             # data manipulation
joblib             # load model
```

**Cách chạy:**
```bash
streamlit run app/main.py
```

---

### 3. Power BI Dashboard

**Kết nối:** Import trực tiếp từ `data/features/` và `data/predictions/` (parquet).

**Cấu trúc 2 trang:**

#### Trang 1: Air Quality Analytics
```
- Trend PM2.5 theo năm / tháng / mùa (line chart)
- Heatmap PM2.5 theo trạm × tháng
- WHO exceedance rate theo parameter
- So sánh các trạm (box plot)
```

#### Trang 2: Model Performance
```
- Actual vs Predicted scatter plot
- Residual distribution (histogram)
- MAE theo mùa (bar chart)
- Per-station error map
```

---

## Source Code Structure

```
app/                               ← Streamlit app
├── main.py                        ← Entry point, navigation
├── pages/
│   ├── 01_overview.py             ← Dashboard Overview
│   ├── 02_prediction.py           ← Prediction Demo
│   └── 03_model_comparison.py     ← Model Comparison
├── components/
│   ├── map.py                     ← Folium map component
│   ├── charts.py                  ← Plotly chart helpers
│   └── shap_plot.py               ← SHAP visualization
└── utils/
    ├── load_model.py              ← Load trained model
    └── predict.py                 ← Prediction pipeline

dashboard/                         ← Power BI files
└── air_quality_dashboard.pbix
```

---

## Data Flow cho App

```
data/features/test.parquet  ─┐
                              ├──► app/utils/predict.py ──► Prediction Demo
models/lgbm_best.pkl        ─┘

data/cleaned/air_quality.parquet ──► Overview Dashboard
data/predictions/predictions.parquet ──► Model Comparison

data/features/ + data/predictions/ ──► Power BI (direct import)
```

---

## Timeline Build App

```
Sau khi hoàn thành model (ADR-004):

  Week 1: Streamlit Trang 2 (Prediction Demo) ← ưu tiên nhất
  Week 2: Streamlit Trang 1 (Overview) + Trang 3 (Model Comparison)
  Week 3: Power BI dashboard
  Week 4: Polish UI, test, chuẩn bị demo hội thảo
```

Trang 2 (Prediction Demo) ưu tiên trước vì đây là phần trình bày tại hội thảo.

---

## Consequences

### Tích cực
- Streamlit viết Python thuần — không cần học thêm tech stack mới
- SHAP waterfall trong Prediction Demo trực quan, ấn tượng khi demo
- Power BI đã có trong tech stack (README) — không cần học tool mới
- Tách biệt 2 tool → mỗi cái làm đúng việc của mình

### Rủi ro & Mitigation

| Rủi ro | Mitigation |
|---|---|
| Streamlit chậm nếu load model mỗi request | Cache model với `@st.cache_resource` |
| Power BI không refresh tự động | Import manual trước khi demo/báo cáo |
| Demo tại hội thảo cần internet | Export static screenshots làm backup |
| Scope app phình to | Giữ đúng 3 trang Streamlit, không thêm feature |

---

## Alternatives Considered

| Option | Lý do không chọn |
|---|---|
| Flask + React | Cần biết JavaScript, quá phức tạp cho scope này |
| Dash (Plotly) | Phức tạp hơn Streamlit, lợi ích không đáng kể |
| Grafana | Tốt cho time-series ops, không phù hợp demo ML prediction |
| Chỉ dùng Power BI | Không thể làm interactive prediction demo |
| Mobile app | Overkill, không phù hợp research scope |
