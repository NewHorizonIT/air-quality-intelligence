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
├── api/                        ← FastAPI backend (phục vụ web app)
│   └── main.py                 #   4 endpoints: /stations /daily /history /predict
├── web/                        ← Frontend React + Vite
│   ├── src/
│   │   ├── components/         #   AlertBanner, KPICard, MapView, ShapChart, …
│   │   ├── pages/              #   Dashboard.jsx, Prediction.jsx
│   │   ├── hooks/useApi.js
│   │   └── utils/              #   api.js, levels.js
│   └── package.json
├── src/                        ← ML pipeline
│   ├── ingestion/
│   ├── processing/
│   ├── features/
│   └── models/
├── data/
│   ├── raw/
│   ├── cleaned/
│   ├── features/               #   train / val / test .parquet
│   └── external/               #   weather.parquet, industrial.parquet
├── models/                     #   lgbm_exp3_best.pkl (pre-trained)
├── notebooks/
├── reports/figures/
├── docs/adr/
└── requirements.txt
```

---

## Cài đặt & Cấu hình

### Yêu cầu hệ thống

| Công cụ | Phiên bản | Ghi chú |
|---------|-----------|---------|
| Python | 3.11+ | Pipeline ML + API server |
| Node.js | 18+ | Web app React |
| Git | bất kỳ | Clone repo |

### 1 — Clone repo & tạo môi trường Python

```bash
git clone <repo-url>
cd air-quality-intelligence

python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Cài toàn bộ thư viện Python (ML + API)
python -m pip install -r requirements.txt
python -m pip install fastapi          # web framework cho demo API
```

### 2 — Cài thư viện frontend

```bash
cd web
npm install
cd ..
```

### 3 — Cấu hình API key

Tạo file `.env` ở thư mục gốc (chỉ cần cho bước thu thập dữ liệu — không cần để chạy demo):

```dotenv
OPENAQ_API_KEY=your_key_here
```

Lấy key miễn phí tại [openaq.org](https://openaq.org/).

> **Lưu ý:** Dữ liệu đã xử lý (`data/features/*.parquet`) và model đã train (`models/*.pkl`) đã có sẵn trong repo. Có thể bỏ qua toàn bộ pipeline và chạy demo ngay.

---

## Chạy Demo Web

Demo cần chạy song song 2 process — API server và web dev server.

### Terminal 1 — Khởi động API server

```bash
# Chạy từ thư mục gốc dự án
uvicorn api.main:app --reload --port 8000
```

Output khi khởi động thành công:
```
[api] Loading lgbm_exp3_best.pkl …
[api] Reading data/features/test.parquet …
[api] Initialising shap.TreeExplainer …
[api] API ready on http://localhost:8000
INFO:     Application startup complete.
```

Kiểm tra API:
- `GET http://localhost:8000/api/stations` — danh sách 53 trạm quan trắc
- `GET http://localhost:8000/api/daily`    — xu hướng PM2.5 theo ngày
- Swagger UI: `http://localhost:8000/docs`

### Terminal 2 — Khởi động web app

```bash
cd web
npm run dev
```

Output:
```
  VITE v8.x.x  ready in xxx ms
  ➜  Local:   http://localhost:5173/
```

Mở **http://localhost:5173** trên trình duyệt.

> Vite tự động proxy tất cả request `/api/*` về `http://localhost:8000`, nên cả 2 process phải chạy đồng thời.

---

## Chạy ML Pipeline (tùy chọn)

> Bỏ qua phần này nếu chỉ muốn chạy demo — model đã train sẵn trong repo.

Chạy từng phase theo thứ tự. Mỗi phase đọc output của phase trước.

**Phase 1 — Thu thập dữ liệu thô** *(cần OPENAQ_API_KEY trong .env)*
```bash
python src/ingestion/fetch_air_quality.py   # ~30 phút, có thể tiếp tục nếu bị gián đoạn
python src/ingestion/fetch_weather.py
python src/ingestion/fetch_industrial.py
python src/ingestion/verify_data.py
```

**Phase 2 — Làm sạch dữ liệu**
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

**Phase 4 — Huấn luyện mô hình**
```bash
python src/models/baseline.py
python src/models/train_lgbm.py      # ~50 phút cho Optuna 100 trials
```

**Phase 5 — Đánh giá + giải thích**
```bash
python src/models/evaluate.py        # xuất reports/evaluation_report.csv
python src/models/interpret.py       # xuất reports/figures/shap_*.png
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

| Tầng | Công nghệ |
|------|----------|
| ML pipeline | Python · Pandas · LightGBM · Optuna · SHAP · Scikit-learn |
| API server | FastAPI · Uvicorn · PyArrow |
| Web frontend | React 19 · Vite · Tailwind CSS · Recharts · Leaflet |
| Trực quan hoá | Matplotlib · Seaborn |

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
