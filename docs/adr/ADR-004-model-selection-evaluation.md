# ADR-004: Model Selection & Evaluation Framework

**Status:** Accepted  
**Date:** 2026-10-10  
**Author:** [Tên nhóm]  
**Liên quan:** [[ADR-001-research-scope]] [[ADR-003-feature-engineering]]

---

## Context

ADR-001 xác định ablation study 4 tầng là contribution chính của paper.  
ADR-003 xác định 24 features chia thành 3 nhóm: temporal, meteorological, industrial.

ADR này quyết định model nào được train, cách tune hyperparameter, metrics đánh giá, và cách report kết quả trong paper.

---

## Decisions

### 1. Model Stack

Có 2 mục đích thực nghiệm tách biệt nhau:

#### Mục đích A — So sánh Model (cùng feature set đầy đủ)

Trả lời: *"Model nào phù hợp nhất với bài toán này?"*

| Model | Thư viện | Vai trò |
|---|---|---|
| **Persistence** | Không cần | Benchmark tối thiểu — "ngày mai = hôm nay" |
| **Ridge Regression** | `sklearn.linear_model.Ridge` | Baseline ML — linear, interpretable |
| **LightGBM** | `lightgbm.LGBMRegressor` | Main model |

Ridge cần `StandardScaler` + `SimpleImputer` trong pipeline (vì không handle NaN).  
LightGBM không cần scale, handle NaN natively.

Random Forest bỏ qua — Ridge vs LightGBM đủ để làm rõ "linear vs gradient boosting".

#### Mục đích B — Ablation Study (cùng model LightGBM, khác feature group)

Trả lời: *"Mỗi nhóm feature đóng góp bao nhiêu vào accuracy?"*

| Experiment | Features | Mục đích |
|---|---|---|
| **Persistence** | — | Benchmark không dùng ML |
| **Exp 1** | Temporal only | Baseline ML không có external data |
| **Exp 2** | Temporal + Meteorological | Đo impact của weather features |
| **Exp 3** | Temporal + Meteorological + Industrial | Đo impact của industrial features |

Delta giữa các experiment = **contribution được report trong paper**.

```
ΔWeather   = MAE(Exp1) - MAE(Exp2)   → weather giảm error bao nhiêu µg/m³
ΔIndustrial = MAE(Exp2) - MAE(Exp3)  → industrial giảm error thêm bao nhiêu
```

---

### 2. Hyperparameter Tuning

**Chọn: Optuna + Early Stopping + Time-Series CV (từ ADR-003)**

```python
import optuna
from lightgbm import early_stopping, log_evaluation

def objective(trial):
    params = {
        "n_estimators":      trial.suggest_int("n_estimators", 100, 1000),
        "learning_rate":     trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
        "max_depth":         trial.suggest_int("max_depth", 3, 7),
        "num_leaves":        trial.suggest_int("num_leaves", 15, 63),
        "min_child_samples": trial.suggest_int("min_child_samples", 10, 50),
        "subsample":         trial.suggest_float("subsample", 0.7, 1.0),
        "colsample_bytree":  trial.suggest_float("colsample_bytree", 0.7, 1.0),
        "reg_alpha":         trial.suggest_float("reg_alpha", 1e-4, 1.0, log=True),
        "reg_lambda":        trial.suggest_float("reg_lambda", 1e-4, 1.0, log=True),
    }
    # Đánh giá bằng time-series CV (ADR-003, 3 folds)
    # Return mean MAE across folds
    ...

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=100)
```

**Early stopping:** Dừng nếu validation MAE không cải thiện sau 50 rounds — tránh overfit.

**Tuning chỉ thực hiện 1 lần** trên Exp 3 (full features). Params tìm được dùng lại cho Exp 1 và Exp 2 — đảm bảo so sánh fair (không phải mỗi experiment có params riêng).

**Ridge tuning:** chỉ cần tune `alpha` bằng `RidgeCV` với cross-validation — đơn giản, không cần Optuna.

---

### 3. Evaluation Metrics

**Primary metric: MAE**

```python
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np

mae  = mean_absolute_error(y_true, y_pred)
rmse = np.sqrt(mean_squared_error(y_true, y_pred))
r2   = r2_score(y_true, y_pred)
mape = np.mean(np.abs((y_true - y_pred) / y_true.clip(lower=1))) * 100
```

| Metric | Đơn vị | Ý nghĩa | Vai trò |
|---|---|---|---|
| **MAE** | µg/m³ | Sai số trung bình — dễ hiểu nhất | **Primary** |
| **RMSE** | µg/m³ | Phạt nặng outlier hơn MAE | Secondary |
| **R²** | — | % variance được giải thích | Secondary |
| **MAPE** | % | Sai số tương đối | Communicate với non-technical |

**Lý do MAE là primary:** đơn vị µg/m³ trực quan — reviewer hiểu ngay "sai 12 µg/m³" nghĩa là gì so với WHO threshold 15 µg/m³.

#### Seasonal Breakdown

Report thêm MAE theo 4 mùa Delhi:

| Mùa | Tháng | Đặc điểm |
|---|---|---|
| Winter | Dec–Feb | PM2.5 cao nhất — temperature inversion |
| Spring | Mar–May | Trung bình |
| Monsoon | Jun–Sep | PM2.5 thấp nhất — mưa rửa ô nhiễm |
| Autumn | Oct–Nov | Diwali spike — PM2.5 tăng đột ngột |

Seasonal MAE cho thấy model mạnh/yếu ở giai đoạn nào — đây là phân tích có giá trị trong paper.

#### Bảng kết quả trong paper

| Model / Experiment | MAE ↓ | RMSE ↓ | R² ↑ | MAPE ↓ |
|---|---|---|---|---|
| Persistence | — | — | — | — |
| Ridge (full features) | — | — | — | — |
| LightGBM Exp 1 (Temporal) | — | — | — | — |
| LightGBM Exp 2 (+Weather) | — | — | — | — |
| LightGBM Exp 3 (+Industrial) | — | — | — | — |

*(Điền sau khi có kết quả thực nghiệm)*

---

### 4. Interpretability — SHAP

**Chọn: SHAP TreeExplainer cho LightGBM best model (Exp 3)**

```python
import shap

explainer   = shap.TreeExplainer(best_model)
shap_values = explainer.shap_values(X_test)

# Plot 1: Bar chart — top 10 features theo mean |SHAP|
shap.plots.bar(shap_values)

# Plot 2: Beeswarm — phân phối và direction của từng feature
shap.plots.beeswarm(shap_values)
```

**3 analyses cần thực hiện:**

| Analysis | Câu hỏi trả lời |
|---|---|
| Global importance (bar chart) | Feature nào đóng góp nhiều nhất tổng thể? |
| Beeswarm plot | Feature kéo prediction lên hay xuống trong điều kiện nào? |
| Seasonal SHAP | Feature importance thay đổi như thế nào giữa các mùa? |

Seasonal SHAP đặc biệt có giá trị: kỳ vọng `boundary_layer_height` quan trọng nhất vào winter, `precipitation` quan trọng nhất vào monsoon — nếu SHAP confirm điều này thì model đang học đúng physics.

---

## Implementation Plan

```
src/models/
├── baseline.py          ← Persistence model + Ridge pipeline
├── train_lgbm.py        ← LightGBM training + Optuna tuning
├── evaluate.py          ← Tính MAE/RMSE/R²/MAPE + seasonal breakdown
├── ablation.py          ← Chạy Exp 1, 2, 3 và so sánh
└── interpret.py         ← SHAP analysis + plots
```

**Thứ tự chạy:**
```
1. train_lgbm.py  →  tune params trên Exp 3 (full features)
2. ablation.py    →  chạy Exp 1, 2, 3 với params đã tune
3. baseline.py    →  Persistence + Ridge với full features
4. evaluate.py    →  tổng hợp tất cả metrics
5. interpret.py   →  SHAP analysis trên best model
```

---

## Consequences

### Tích cực
- Ablation study tách biệt rõ contribution của weather vs industrial
- Dùng cùng hyperparams cho Exp 1/2/3 đảm bảo so sánh fair
- MAE primary metric dễ hiểu, liên quan trực tiếp đến WHO threshold
- Seasonal SHAP validate xem model có học đúng physics không

### Rủi ro & Mitigation

| Rủi ro | Mitigation |
|---|---|
| Optuna 100 trials tốn thời gian | Chạy trên Exp 3 một lần, reuse params |
| MAPE không xác định khi y_true ≈ 0 | clip(lower=1) trước khi tính MAPE |
| Test set chỉ có 1 trạm (New Delhi) | Ghi nhận là limitation, report CV results thêm |
| LightGBM overfit do ít data | early_stopping + min_child_samples + reg_alpha/lambda |

---

## Alternatives Considered

| Option | Lý do không chọn |
|---|---|
| Random Forest | Ridge vs LightGBM đủ rõ, RF thêm vào chỉ tăng complexity report |
| Grid Search | Chậm hơn Optuna, không adaptive |
| RMSE làm primary metric | Khó interpret hơn MAE, bị ảnh hưởng bởi outlier |
| Tune params riêng cho mỗi experiment | Không fair — model mạnh hơn ở Exp 3 có thể do params tốt hơn, không phải do features |
| LIME thay SHAP | SHAP có global + local view, phù hợp tree model hơn |
