# ADR-006: Storage Layer

**Status:** Accepted  
**Date:** 2026-10-10  
**Author:** [Tên nhóm]  
**Liên quan:** [[ADR-002-external-data-integration]] [[ADR-003-feature-engineering]] [[ADR-005-data-quality-cleaning]]

---

## Context

README đề cập PostgreSQL nhưng toàn bộ pipeline hiện tại dùng file. Project có 3 nguồn data (OpenAQ, Open-Meteo, WRI GPPD) cần được lưu trữ, clean, merge và đưa vào model. Cần quyết định rõ: lưu ở đâu, dạng gì, merge ở bước nào.

---

## Decisions

### 1. File-based vs PostgreSQL

**Chọn:** Tách biệt rõ 2 phase:

| Phase | Storage | Lý do |
|---|---|---|
| **ML pipeline + paper** | File-based (Parquet) | Không cần setup, nhanh với pandas, đủ cho research |
| **Dashboard (future)** | PostgreSQL | Power BI native connector, hỗ trợ SQL analytics |

PostgreSQL **không dùng** trong phase nghiên cứu — tốn công setup mà không có lợi ích thêm cho paper. Sẽ implement khi build dashboard sau khi có model hoàn chỉnh.

---

### 2. File Format

| Format | Dùng khi nào | Lý do |
|---|---|---|
| **Parquet** | Tất cả data trong pipeline | Nhanh, nén tốt, giữ nguyên dtype |
| **CSV** | Export cho báo cáo / nộp bài | Mọi tool đọc được |
| **JSON** | Cache API responses | Flexible, human-readable |

---

### 3. Directory Structure & Merge Strategy

**Nguyên tắc cốt lõi:** 3 nguồn data được **clean độc lập**, chỉ **merge tại bước feature engineering**.

**Lý do không merge sớm:**
- Industrial data là tĩnh (không có cột `date`) — merge sớm tạo rows thừa
- Mỗi nguồn có thể re-clean độc lập mà không ảnh hưởng nguồn khác
- Merge logic tập trung 1 chỗ duy nhất: `src/features/build_features.py`

**Luồng merge:**
```
air_quality.parquet  (date × station × parameter)
        │
        │  merge theo (date, location_name)
        ▼
weather.parquet      (date × station × weather_vars)
        │
        │  tính distance/capacity features từ industrial
        │  join theo location_name  ← không phải date (data tĩnh)
        ▼
industrial.parquet   (station tĩnh: name, lat, lon, capacity_mw)
        │
        ▼
features/train.parquet  (date × station × 24 features × target)
```

**Cấu trúc thư mục:**

```
data/
├── raw/
│   └── delhi_raw.parquet              ← OpenAQ thô, fetch 1 lần, không xóa
│
├── external/
│   ├── weather.parquet                ← Open-Meteo đã clean (date × station)
│   └── industrial.parquet             ← WRI GPPD đã clean, tĩnh (station only)
│
├── cleaned/
│   └── air_quality.parquet            ← OpenAQ đã clean, long format
│
├── features/                          ← Merged + engineered, sẵn sàng train
│   ├── train.parquet                  (2022-01-01 → 2023-09-30)
│   ├── val.parquet                    (2023-10-01 → 2024-03-31)
│   └── test.parquet                   (2024-04-01 → 2024-12-31)
│
├── predictions/
│   └── predictions.parquet            ← Model output
│
├── .cache/
│   ├── delhi_locations.json           ← Cache OpenAQ locations
│   └── delhi_sensors.json             ← Cache OpenAQ sensors
│
└── exports/
    └── results_summary.csv            ← Export cho báo cáo / nộp bài
```

---

### 4. Data Flow Toàn Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  INGESTION                                                      │
│  src/ingestion/fetch_air_quality.py  → data/raw/               │
│  src/ingestion/fetch_weather.py      → data/external/weather   │
│  src/ingestion/fetch_industrial.py   → data/external/industrial│
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  CLEANING  (ADR-005)                                            │
│  src/processing/clean_air_quality.py → data/cleaned/           │
│  src/processing/clean_weather.py     → data/external/ (update) │
│  src/processing/clean_industrial.py  → data/external/ (update) │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  FEATURE ENGINEERING  (ADR-003)                                 │
│  src/features/build_features.py                                 │
│    - Merge 3 nguồn                                              │
│    - Tạo lag, rolling, cyclical, industrial features            │
│    - Split train/val/test                                       │
│  → data/features/train.parquet                                  │
│  → data/features/val.parquet                                    │
│  → data/features/test.parquet                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  MODELING  (ADR-004)                                            │
│  src/models/train_lgbm.py    → models/lgbm_best.pkl            │
│  src/models/baseline.py      → models/ridge.pkl                │
│  src/models/evaluate.py      → data/predictions/               │
│  src/models/interpret.py     → reports/shap_plots/             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  EXPORT                                                         │
│  data/exports/results_summary.csv   ← nộp báo cáo              │
│  reports/figures/                   ← plots cho paper          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Source Code Structure

```
src/
├── ingestion/
│   ├── __init__.py
│   ├── openaq_client.py          ← OpenAQ API wrapper
│   ├── fetch_air_quality.py      ← Fetch + save raw parquet
│   ├── fetch_weather.py          ← Open-Meteo per station
│   └── fetch_industrial.py       ← Download + filter WRI GPPD
│
├── processing/
│   ├── __init__.py
│   ├── clean_air_quality.py      ← ADR-005: O3 convert, caps, flags
│   ├── clean_weather.py          ← ADR-005: bounds, forward fill
│   └── clean_industrial.py       ← ADR-005: filter, dedup
│
├── features/
│   ├── __init__.py
│   └── build_features.py         ← ADR-003: merge + engineer + split
│
└── models/
    ├── __init__.py
    ├── baseline.py               ← Persistence + Ridge
    ├── train_lgbm.py             ← LightGBM + Optuna
    ├── evaluate.py               ← Metrics + seasonal breakdown
    └── interpret.py              ← SHAP analysis
```

---

## Consequences

### Tích cực
- Clean từng nguồn độc lập → dễ debug, dễ re-run từng bước
- Merge chỉ ở feature engineering → logic tập trung 1 chỗ
- Parquet giữ dtype → không mất thông tin khi đọc lại
- Structure rõ ràng → teammate dễ navigate

### Rủi ro & Mitigation

| Rủi ro | Mitigation |
|---|---|
| File parquet không versioned | Dùng git để track code; data tái tạo được từ script |
| features/ bị stale nếu clean lại raw | Xóa features/ và re-run build_features.py |
| Nhiều file parquet nhỏ | Chấp nhận được ở scale này (~10MB tổng) |
| Dashboard cần PostgreSQL sau này | Schema đã thiết kế tương thích, migrate dễ |

---

## Alternatives Considered

| Option | Lý do không chọn |
|---|---|
| PostgreSQL ngay từ đầu | Overkill cho ML pipeline, không cần thiết cho paper |
| Merge tất cả vào 1 file lớn | Industrial data tĩnh gây redundancy; khó re-clean từng nguồn |
| DVC (Data Version Control) | Phức tạp hơn cần thiết cho scope này |
| SQLite | Không có lợi ích so với parquet cho ML workflow |
