# Tuần 5 — Phase 5: Evaluation + Interpretation
**2026-11-10 → 2026-11-14**

---

## Mục tiêu cuối tuần

- Bảng kết quả hoàn chỉnh trên **test set** (5 models × 4 metrics × 4 mùa)
- SHAP bar chart + beeswarm plot
- Tất cả figures đã save vào `reports/figures/` — sẵn sàng chèn vào paper

---

## Thứ 2 — 2026-11-10: Evaluation script

### Viết `src/models/evaluate.py`

**4 metrics:**
```python
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def evaluate(y_true, y_pred, label=""):
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    r2   = r2_score(y_true, y_pred)
    mape = (np.abs((y_true - y_pred) / y_true.replace(0, np.nan)).mean()) * 100
    return {"model": label, "MAE": mae, "RMSE": rmse, "R2": r2, "MAPE": mape}
```

**Seasonal breakdown:**
```python
SEASONS = {
    "winter":  [12, 1, 2],
    "spring":  [3, 4, 5],
    "monsoon": [6, 7, 8, 9],
    "autumn":  [10, 11],
}
# Tính MAE per season per model → bảng 5×4
```

**Checklist:**
- [ ] Kết quả overall trên test set (không phải val)
- [ ] Seasonal MAE breakdown đã tính
- [ ] Save kết quả: `data/exports/results_summary.csv`

---

## Thứ 3 — 2026-11-11: SHAP Analysis

### Viết `src/models/interpret.py`

```python
import shap

explainer = shap.TreeExplainer(lgbm_exp3)
shap_values = explainer.shap_values(X_test)

# Plot 1: Bar chart — mean absolute SHAP per feature (top 15)
shap.summary_plot(shap_values, X_test, plot_type="bar", max_display=15)

# Plot 2: Beeswarm — distribution of SHAP values
shap.summary_plot(shap_values, X_test, max_display=15)

# Plot 3: Seasonal SHAP — SHAP values per season
for season, months in SEASONS.items():
    mask = X_test.index.month.isin(months)
    shap.summary_plot(shap_values[mask], X_test[mask], plot_type="bar")
```

**Checklist:**
- [ ] SHAP bar chart: `reports/figures/shap_bar.png`
- [ ] SHAP beeswarm: `reports/figures/shap_beeswarm.png`
- [ ] Seasonal SHAP: `reports/figures/shap_seasonal.png`

---

## Thứ 4 — 2026-11-12: Figures cho paper

### Generate tất cả figures cần thiết

```
Fig A: Ablation bar chart — MAE của 5 models (grouped bar)
Fig B: Actual vs Predicted scatter (Exp3, test set)
Fig C: Residual distribution histogram
Fig D: Seasonal MAE comparison (5 models × 4 mùa)
Fig E: SHAP bar chart (top 15 features)
Fig F: SHAP beeswarm
```

Tất cả figure: **300 DPI**, font size ≥ 10pt, có title + axis labels, save `.png` và `.pdf`.

**Checklist:**
- [ ] 6 figures đã save vào `reports/figures/`
- [ ] Figures đẹp, đủ rõ để đọc trong paper in đen trắng

---

## Thứ 5 — 2026-11-13: Per-station analysis

```python
# MAE per station → tìm station nào model dự đoán tệ nhất
station_mae = (
    results_df.groupby("location_name")
    .apply(lambda g: mean_absolute_error(g["actual"], g["predicted"]))
    .sort_values(ascending=False)
)
# Top 5 worst → investigate: sparse data? near industrial?
```

**Checklist:**
- [ ] Per-station MAE đã tính
- [ ] 2–3 insight về station tệ nhất ghi vào notes (dùng cho Discussion section)

---

## Thứ 6 — 2026-11-14: Buffer + Wrap up

- Fix figure quality nếu cần
- Ghi notes cho paper: key findings, surprising results
- Update tracking: Phase 5 → 🟢 Hoàn thành
- **Milestone M4: Results Ready** ✓

---

## Files tạo tuần này

```
src/models/
  evaluate.py
  interpret.py

data/
  exports/results_summary.csv
  predictions/predictions.parquet

reports/figures/
  fig_ablation_bar.png
  fig_actual_vs_pred.png
  fig_residual.png
  fig_seasonal_mae.png
  shap_bar.png
  shap_beeswarm.png
  shap_seasonal.png
```

---

## Definition of Done

- [ ] Bảng kết quả 5 models × 4 metrics trên test set
- [ ] Seasonal MAE breakdown hoàn chỉnh
- [ ] SHAP bar + beeswarm đã save
- [ ] Tất cả figures 300 DPI, sẵn sàng chèn paper
