# Tuần 6 — Phase 6: Paper Writing (Draft)
**2026-11-17 → 2026-11-21**

---

## Mục tiêu cuối tuần

- Draft hoàn chỉnh 6–8 trang đúng template FJCAI 2026
- Tất cả figures đã chèn vào paper
- Gửi thầy review trước thứ 6

---

## Thứ 2 — 2026-11-17: Setup + Introduction

**Bước 1: Tải template FJCAI 2026**
- Vào website BTC FJCAI 2026, tải LaTeX template (hoặc Word)
- Tạo file: `paper/main.tex` (hoặc `paper/main.docx`)

**Bước 2: Viết Section 1 — Introduction (~0.5 trang)**

Cấu trúc:
```
1. Hook: Delhi là một trong những thành phố ô nhiễm nhất thế giới
2. Problem: PM2.5 gây hại sức khỏe, cần dự đoán trước để cảnh báo
3. Gap: Các nghiên cứu trước chưa kết hợp đầy đủ weather + industrial
4. Contribution: 3 điểm (dataset 2022–2025, ablation study, SHAP)
5. Paper structure: Section 2... Section 3...
```

**Checklist:**
- [ ] Template đã tải và compile được
- [ ] Introduction draft (~300 words)

---

## Thứ 3 — 2026-11-18: Related Work + Data

**Section 2 — Related Work (~1 trang)**

Tìm và cite 8–10 bài về:
- PM2.5 prediction với ML (LightGBM, XGBoost, LSTM)
- Air quality forecasting Delhi/India
- Weather impact trên air quality
- Industrial emission và air quality

Gợi ý search: Google Scholar, Semantic Scholar với keywords:
`"PM2.5 prediction" "LightGBM"`, `"air quality forecasting" "Delhi"`, `"feature importance" "SHAP" "air quality"`

**Section 3 — Data & Study Area (~0.5 trang)**

```
3.1 Study Area: Delhi NCR, bounding box, tại sao chọn Delhi
3.2 Data Sources:
    - OpenAQ v3: 58 stations, 2022–2025, 6 parameters
    - Open-Meteo ERA5: 6 weather variables, free
    - WRI GPPD: N fossil fuel plants trong 50km buffer
3.3 Data Quality: unit conversion, outlier caps, cross-station flag
    → chèn Figure: missing data heatmap
```

**Checklist:**
- [ ] 8+ papers đã tìm và ghi vào references
- [ ] Section 2 draft
- [ ] Section 3 draft + Figure 6 chèn vào

---

## Thứ 4 — 2026-11-19: Methodology

**Section 4 — Methodology (~1.5 trang)**

```
4.1 Feature Engineering (24 features)
    - Table: danh sách feature groups
    → chèn Figure: correlation heatmap

4.2 Model Architecture
    - Persistence baseline
    - Ridge regression
    - LightGBM: hyperparams, Optuna 100 trials

4.3 Ablation Study Design
    - Table: Exp1/2/3 feature sets
    - Train/Val/Test split dates

4.4 Evaluation Metrics
    - MAE (primary), RMSE, R², MAPE
    - Seasonal breakdown rationale
```

**Checklist:**
- [ ] Section 4 draft (~600 words)
- [ ] Feature table đã chèn
- [ ] Ablation table đã chèn

---

## Thứ 5 — 2026-11-20: Results + Discussion

**Section 5 — Results & Discussion (~2 trang) ← phần quan trọng nhất**

```
5.1 Overall Performance
    → Table: 5 models × 4 metrics (MAE/RMSE/R²/MAPE)
    → chèn Figure: ablation bar chart

5.2 Ablation Study
    - Exp1→2: weather giảm MAE bao nhiêu %?
    - Exp2→3: industrial giảm thêm bao nhiêu %?
    → chèn Figure: actual vs predicted scatter

5.3 Seasonal Analysis
    → Table: MAE per season per model
    → chèn Figure: seasonal MAE chart
    - Insight: winter worst? monsoon better?

5.4 Feature Importance (SHAP)
    → chèn Figure: SHAP bar + beeswarm
    - Top 3 features, interpretation
    - Seasonal SHAP differences

5.5 Cross-station Analysis
    - Suspicious stations: bao nhiêu %, ảnh hưởng accuracy?
    - Per-station MAE: worst stations là đâu, tại sao?
```

**Checklist:**
- [ ] Section 5 draft
- [ ] Tất cả figures đã chèn đúng chỗ
- [ ] Numbers trong text khớp với bảng kết quả

---

## Thứ 6 — 2026-11-21: Conclusion + Gửi thầy

**Section 6 — Conclusion (~0.5 trang)**
```
- Summary: câu trả lời cho research question
- Key findings: 3 bullet points
- Limitations: 3 điểm (ppb assumption, GPPD thiếu nhà máy nhỏ, 1 năm train)
- Future Work: real-time, multi-horizon, other cities
```

**References** — IEEE format, dùng BibTeX nếu LaTeX.

**Gửi thầy review** trước 17:00 hôm nay.

**Checklist:**
- [ ] Draft đủ 6–8 trang
- [ ] Tất cả references đúng format IEEE
- [ ] Spell-check đã chạy
- [ ] Thầy đã nhận file (email/zalo)
- [ ] **Milestone M5: Draft Submitted to Supervisor** ✓

---

## Files tạo tuần này

```
paper/
  main.tex (hoặc main.docx)
  references.bib
  figures/   ← copy từ reports/figures/
```
