# Air Quality Intelligence Platform

Next-day PM2.5 forecasting for Delhi, India using multi-source environmental data and LightGBM.

> Research project for FJCAI 2026 — submission deadline November 2026.

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

*Results will be updated after Phase 4 (model training, week of Nov 3).*

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
├── src/
│   ├── ingestion/          # Phase 1: data fetching
│   │   ├── openaq_client.py
│   │   ├── fetch_air_quality.py
│   │   ├── fetch_weather.py
│   │   ├── fetch_industrial.py
│   │   └── verify_data.py
│   ├── processing/         # Phase 2: cleaning
│   │   ├── clean_air_quality.py
│   │   ├── clean_weather.py
│   │   ├── clean_industrial.py
│   │   └── verify_cleaned.py
│   ├── features/           # Phase 3: feature engineering
│   │   └── build_features.py
│   └── models/             # Phase 4–5: training & evaluation
│       ├── baseline.py
│       ├── train_lgbm.py
│       ├── evaluate.py
│       └── interpret.py
├── app/                    # Streamlit dashboard
│   ├── main.py
│   └── pages/
├── data/
│   ├── raw/                # Per-sensor parquets + merged
│   ├── cleaned/            # Post-cleaning parquets
│   ├── features/           # train / val / test splits
│   └── external/           # WRI GPPD industrial
├── models/                 # Saved model files (.pkl)
├── notebooks/
│   └── eda.ipynb
├── reports/
│   └── figures/            # All paper figures (300 DPI)
├── docs/
│   ├── adr/                # Architecture Decision Records
│   └── weekly_plans/       # Week-by-week project plan
└── requirements.txt
```

---

## Setup

**Requirements:** Python 3.11+

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

**API key** — create a `.env` file in the project root:

```
OPENAQ_API_KEY=your_key_here
```

Get a free key at [openaq.org](https://openaq.org/).

---

## Running the Pipeline

Run each phase in order. Each phase reads from the previous phase's output.

**Phase 1 — Fetch raw data**
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
python src/models/evaluate.py
python src/models/interpret.py
```

**Streamlit app**
```bash
streamlit run app/main.py
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

Ablation study:
- **Exp1** — temporal features only
- **Exp2** — Exp1 + weather
- **Exp3** — Exp2 + industrial ← main model

---

## Tech Stack

Python · Pandas · LightGBM · Optuna · SHAP · Scikit-learn · Streamlit · Matplotlib · Seaborn · Folium

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
