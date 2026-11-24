[![EN](https://img.shields.io/badge/lang-en-blue.svg)](README.md)
[![VI](https://img.shields.io/badge/lang-vi-yellow.svg)](README.vi.md)

# Air Quality Intelligence Platform

Next-day PM2.5 forecasting for Delhi, India using multi-source environmental data and LightGBM.

---

## Overview

Delhi is consistently ranked among the world's most polluted cities. This project builds a machine learning pipeline that predicts next-day PM2.5 concentration by combining three data sources: real-time air quality measurements, historical weather reanalysis, and industrial power plant proximity.

**Key contributions:**
- 4-year dataset (2022–2025) across 59 monitoring stations
- Ablation study isolating the marginal contribution of weather and industrial features
- SHAP-based interpretation of seasonal pollution drivers
- Interactive Streamlit demo for station-level prediction

---

## Results (preliminary — val set)

| Model | MAE (µg/m³) | RMSE | R² |
|---|---|---|---|
| Persistence baseline | — | — | — |
| Ridge regression | — | — | — |
| LightGBM Exp1 (temporal only) | — | — | — |
| LightGBM Exp2 (+ weather) | — | — | — |
| LightGBM Exp3 (+ industrial) | — | — | — |

*Results will be updated .*

---

## Data Sources

| Source | Coverage | Variables |
|---|---|---|
| [OpenAQ v3](https://api.openaq.org/) | 59 stations · 2022–2025 | PM2.5, PM10, NO₂, O₃, SO₂, CO |
| [Open-Meteo ERA5](https://open-meteo.com/) | Per station · daily | Temp, precip, wind speed/dir, humidity, ET₀ |
| [WRI Global Power Plant Database](https://datasets.wri.org/dataset/globalpowerplantdatabase) | Delhi bbox · static | Plant capacity, fuel type, coordinates |

---

## Project Structure

```
air-quality-intelligence/
├── api/                        ← FastAPI backend (serves the web app)
│   └── main.py                 #   4 endpoints: /stations /daily /history /predict
├── web/                        ← React + Vite frontend
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
├── models/                     #   lgbm_exp3_best.pkl (pre-trained, tracked by Git LFS)
├── notebooks/
├── reports/figures/
├── docs/adr/
└── requirements.txt
```

---

## Installation & Setup

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Required for ML pipeline + API server |
| Node.js | 18+ | Required for the React web app |
| Git | any | Clone the repo |

### 1 — Clone & create Python environment

```bash
git clone <repo-url>
cd air-quality-intelligence

python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install all Python dependencies (ML + API)
python -m pip install -r requirements.txt
python -m pip install fastapi          # web framework for the demo API
```

### 2 — Install frontend dependencies

```bash
cd web
npm install
cd ..
```

### 3 — Configure API key

Create a `.env` file in the project root (needed only for data ingestion — not required to run the demo):

```dotenv
OPENAQ_API_KEY=your_key_here
```

Get a free key at [openaq.org](https://openaq.org/).

> **Note:** Pre-processed data (`data/features/*.parquet`) and trained models (`models/*.pkl`) are already committed to the repo. You can skip directly to **Running the Demo** without re-running the full pipeline.

---

## Running the Demo

The demo requires two processes running simultaneously — the API server and the web dev server.

### Terminal 1 — Start the API server

```bash
# From the project root
uvicorn api.main:app --reload --port 8000
```

Expected output:
```
[api] Loading lgbm_exp3_best.pkl …
[api] Reading data/features/test.parquet …
[api] Initialising shap.TreeExplainer …
[api] API ready on http://localhost:8000
INFO:     Application startup complete.
```

You can verify the API is up:
- `GET http://localhost:8000/api/stations` — list of 53 monitoring stations
- `GET http://localhost:8000/api/daily`    — city-wide daily PM2.5 trend
- Interactive docs: `http://localhost:8000/docs`

### Terminal 2 — Start the web app

```bash
cd web
npm run dev
```

Expected output:
```
  VITE v8.x.x  ready in xxx ms
  ➜  Local:   http://localhost:5173/
```

Open **http://localhost:5173** in your browser.

> The Vite dev server proxies all `/api/*` requests to `http://localhost:8000`, so both processes must be running.

---

## Running the ML Pipeline

> Skip this section if you only want to run the demo — trained models are already included.

Run each phase in order. Each phase reads from the previous phase's output.

**Phase 1 — Fetch raw data** *(requires OPENAQ_API_KEY in .env)*
```bash
python src/ingestion/fetch_air_quality.py   # ~30 min, resumable
python src/ingestion/fetch_weather.py
python src/ingestion/fetch_industrial.py
python src/ingestion/verify_data.py
```

**Phase 2 — Clean**
```bash
python src/processing/clean_air_quality.py
python src/processing/clean_weather.py
python src/processing/clean_industrial.py
python src/processing/verify_cleaned.py
```

**Phase 3 — Feature engineering**
```bash
python src/features/build_features.py
```

**Phase 4 — Train**
```bash
python src/models/baseline.py
python src/models/train_lgbm.py      # ~50 min for Optuna 100 trials
```

**Phase 5 — Evaluate + interpret**
```bash
python src/models/evaluate.py        # writes reports/evaluation_report.csv
python src/models/interpret.py       # writes reports/figures/shap_*.png
```

---

## Feature Engineering

24 features across 3 groups:

| Group | Features |
|---|---|
| Temporal (13) | PM2.5 lag 1/2/3/7d · rolling mean 7/14/30d · rolling std 7/14d · month sin/cos · DOW sin/cos · season dummies |
| Weather (6) | Temperature · precipitation · wind speed · wind direction · humidity · ET₀ |
| Industrial (3) | Distance to nearest plant (km) · capacity-weighted proximity · plant count within 50km |

**Target:** PM2.5 at station s on day t+1.

**Train/Val/Test split (temporal):**
```
Train : 2022-01-01 → 2024-03-31
Val   : 2024-04-01 → 2024-09-30
Test  : 2024-10-01 → 2025-12-31
```

---

## Model

LightGBM regressor tuned with Optuna (100 trials, objective = MAE on val set).

| Experiment | Feature set |
|---|---|
| Exp1 | Temporal only |
| Exp2 | Exp1 + Weather |
| Exp3 ← main | Exp2 + Industrial |

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| ML pipeline | Python · Pandas · LightGBM · Optuna · SHAP · Scikit-learn |
| API server | FastAPI · Uvicorn · PyArrow |
| Web frontend | React 19 · Vite · Tailwind CSS · Recharts · Leaflet |
| Visualization | Matplotlib · Seaborn |

---

## Project Timeline

| Week | Phase | Dates |
|---|---|---|
| 1 | Data Ingestion | Oct 13–17 |
| 2 | Data Cleaning | Oct 20–24 |
| 3 | Feature Engineering + EDA | Oct 27–31 |
| 4 | Model Training | Nov 3–7 |
| 5 | Evaluation + SHAP | Nov 10–14 |
| 6 | Paper Writing | Nov 17–21 |
| 7 | Paper Final + Submit | Nov 24–28 |

---

## License

For academic research purposes only.
