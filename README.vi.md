[![EN](https://img.shields.io/badge/lang-en-blue.svg)](README.md)
[![VI](https://img.shields.io/badge/lang-vi-yellow.svg)](README.vi.md)

# Air Quality Intelligence Platform

Dự đoán nồng độ PM2.5 ngày hôm sau tại Delhi, Ấn Độ bằng LightGBM kết hợp dữ liệu đa nguồn.

---

## Tổng quan

Delhi là một trong những thành phố ô nhiễm nhất thế giới. Dự án xây dựng pipeline học máy dự đoán nồng độ PM2.5 ngày hôm sau bằng cách kết hợp ba nguồn dữ liệu: đo lường chất lượng không khí thực tế, tái phân tích thời tiết lịch sử, và khoảng cách đến nhà máy công nghiệp.

**Đóng góp chính:**
- Tập dữ liệu 4 năm (2022–2025) từ 59 trạm quan trắc
- Ablation study đo lường đóng góp riêng lẻ của dữ liệu thời tiết và công nghiệp
- Giải thích mô hình bằng SHAP theo từng mùa trong năm
- Demo Streamlit dự đoán PM2.5 theo trạm quan trắc

---

## Kết quả (sơ bộ — val set)

| Mô hình | MAE (µg/m³) | RMSE | R² |
|---|---|---|---|
| Persistence baseline | — | — | — |
| Ridge regression | — | — | — |
| LightGBM Exp1 (chỉ temporal) | — | — | — |
| LightGBM Exp2 (+ thời tiết) | — | — | — |
| LightGBM Exp3 (+ công nghiệp) | — | — | — |

*Kết quả sẽ cập nhật sau.*

---

## Nguồn dữ liệu

| Nguồn | Phạm vi | Biến số |
|---|---|---|
| [OpenAQ v3](https://api.openaq.org/) | 59 trạm · 2022–2025 | PM2.5, PM10, NO₂, O₃, SO₂, CO |
| [Open-Meteo ERA5](https://open-meteo.com/) | Theo trạm · hàng ngày | Nhiệt độ, mưa, tốc độ/hướng gió, độ ẩm, ET₀ |
| [WRI Global Power Plant Database](https://datasets.wri.org/dataset/globalpowerplantdatabase) | Bounding box Delhi · tĩnh | Công suất, loại nhiên liệu, tọa độ |

---

## Cấu trúc dự án

```
air-quality-intelligence/
├── src/
│   ├── ingestion/          
│   │   ├── openaq_client.py
│   │   ├── fetch_air_quality.py
│   │   ├── fetch_weather.py
│   │   ├── fetch_industrial.py
│   │   └── verify_data.py
│   ├── processing/         
│   │   ├── clean_air_quality.py
│   │   ├── clean_weather.py
│   │   ├── clean_industrial.py
│   │   └── verify_cleaned.py
│   ├── features/           
│   │   └── build_features.py
│   └── models/             
│       ├── baseline.py
│       ├── train_lgbm.py
│       ├── evaluate.py
│       └── interpret.py
├── app/                    
│   ├── main.py
│   └── pages/
├── data/
│   ├── raw/                
│   ├── cleaned/           
│   ├── features/           
│   └── external/           
├── models/                
├── notebooks/
│   └── eda.ipynb
├── reports/
│   └── figures/            
├── docs/
│   ├── adr/                
│   └── weekly_plans/       
└── requirements.txt
```

---

## Cài đặt

**Yêu cầu:** Python 3.11+

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

**API key** — tạo file `.env` ở thư mục gốc:

```
OPENAQ_API_KEY=your_key_here
```

Lấy key miễn phí tại [openaq.org](https://openaq.org/).

---

## Chạy pipeline

Chạy từng phase theo thứ tự. Mỗi phase đọc output của phase trước.

**Phase 1 — Thu thập dữ liệu thô**
```bash
python src/ingestion/fetch_air_quality.py   # ~30 phút, có thể tiếp tục
python src/ingestion/fetch_weather.py
python src/ingestion/fetch_industrial.py
python src/ingestion/verify_data.py
```

**Phase 2 — Làm sạch**
```bash
python src/processing/clean_air_quality.py
python src/processing/clean_weather.py
python src/processing/clean_industrial.py
python src/processing/verify_cleaned.py
```

**Phase 3 — Xây dựng đặc trưng**
```bash
python src/features/build_features.py
```

**Phase 4 — Huấn luyện**
```bash
python src/models/baseline.py
python src/models/train_lgbm.py      # ~50 phút cho Optuna 100 trials
```

**Phase 5 — Đánh giá + giải thích**
```bash
python src/models/evaluate.py
python src/models/interpret.py
```

**Streamlit app**
```bash
streamlit run app/main.py
```

---

## Xây dựng đặc trưng

24 đặc trưng thuộc 3 nhóm:

| Nhóm | Đặc trưng |
|---|---|
| Thời gian (13) | PM2.5 lag 1/2/3/7d · rolling mean 7/14/30d · rolling std 7/14d · month sin/cos · DOW sin/cos · season dummies |
| Thời tiết (6) | Nhiệt độ · lượng mưa · tốc độ gió · hướng gió · độ ẩm · ET₀ |
| Công nghiệp (3) | Khoảng cách nhà máy gần nhất (km) · proximity có trọng số công suất · số nhà máy trong 50km |

**Biến mục tiêu:** PM2.5 tại trạm s ngày t+1.

**Phân chia train/val/test (theo thời gian):**
```
Train : 2022-01-01 → 2024-03-31
Val   : 2024-04-01 → 2024-09-30
Test  : 2024-10-01 → 2025-12-31
```

---

## Mô hình

LightGBM tối ưu siêu tham số bằng Optuna (100 trials, mục tiêu tối thiểu MAE trên val set).

| Thí nghiệm | Tập đặc trưng |
|---|---|
| Exp1 | Chỉ đặc trưng thời gian |
| Exp2 | Exp1 + thời tiết |
| Exp3 ← chính | Exp2 + công nghiệp |

---

## Công nghệ sử dụng

Python · Pandas · LightGBM · Optuna · SHAP · Scikit-learn · Streamlit · Matplotlib · Seaborn · Folium

---

## Kế hoạch dự án

| Tuần | Phase | Ngày |
|---|---|---|
| 1 | Thu thập dữ liệu | 13–17/10 |
| 2 | Làm sạch dữ liệu | 20–24/10 |
| 3 | Feature Engineering + EDA | 27–31/10 |
| 4 | Huấn luyện mô hình | 03–07/11 |
| 5 | Đánh giá + SHAP | 10–14/11 |
| 6 | Viết báo | 17–21/11 |
| 7 | Hoàn thiện + nộp bài | 24–28/11 |

---

## Giấy phép

Chỉ dùng cho mục đích nghiên cứu học thuật.
