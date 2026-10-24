# Tuần 4 — Phase 4: Model Training
**2026-11-03 → 2026-11-07**

---

## Mục tiêu cuối tuần

- 5 models đã train và save: Persistence, Ridge, LightGBM Exp1/2/3
- Optuna best params đã log
- Không có data leakage trong training

---

## Thứ 2 — 2026-11-03: Baseline Models

### Viết `src/models/baseline.py`

**Persistence baseline** — predict ngày mai = hôm nay:
```python
def persistence_predict(df_test):
    return df_test["pm25_lag1"]   # lag1 chính là giá trị hôm nay
```
Không cần train. Đây là lower bound — nếu model không beat được cái này thì có vấn đề.

**Ridge regression:**
```python
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

ridge = Pipeline([
    ("scaler", StandardScaler()),
    ("model", Ridge(alpha=1.0)),
])
ridge.fit(X_train, y_train)
joblib.dump(ridge, "models/ridge.pkl")
```

**Checklist:**
- [ ] Persistence MAE tính được
- [ ] Ridge train xong, save tại `models/ridge.pkl`
- [ ] Cả 2 đã predict trên val set

---

## Thứ 3 — 2026-11-04: LightGBM Exp 1 + 2

### Viết `src/models/train_lgbm.py`

**Experiment design (ADR-004):**

| Exp | Features |
|---|---|
| Exp1 | Temporal only (lags, rolling, cyclical, season) |
| Exp2 | Exp1 + Weather (6 biến) |
| Exp3 | Exp2 + Industrial (3 biến) ← model chính |

**Chạy Exp1 và Exp2:**
```python
import lightgbm as lgb

FEATURE_SETS = {
    "exp1": TEMPORAL_FEATURES,
    "exp2": TEMPORAL_FEATURES + WEATHER_FEATURES,
    "exp3": TEMPORAL_FEATURES + WEATHER_FEATURES + INDUSTRIAL_FEATURES,
}

params_default = {
    "objective": "regression",
    "metric": "mae",
    "n_estimators": 500,
    "learning_rate": 0.05,
    "num_leaves": 63,
    "random_state": 42,
    "verbose": -1,
}
```

**Checklist:**
- [ ] Exp1 train xong, save `models/lgbm_exp1.pkl`
- [ ] Exp2 train xong, save `models/lgbm_exp2.pkl`
- [ ] Val MAE Exp2 < Exp1 (weather helps)

---

## Thứ 4 — 2026-11-05: Optuna tuning + Exp3

### Optuna hyperparameter search (chỉ tune 1 lần trên Exp3)

```python
import optuna

def objective(trial):
    params = {
        "num_leaves":        trial.suggest_int("num_leaves", 31, 255),
        "max_depth":         trial.suggest_int("max_depth", 3, 12),
        "learning_rate":     trial.suggest_float("lr", 0.01, 0.1, log=True),
        "n_estimators":      trial.suggest_int("n_estimators", 200, 1000),
        "min_child_samples": trial.suggest_int("min_child_samples", 10, 100),
        "subsample":         trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree":  trial.suggest_float("colsample", 0.6, 1.0),
        "reg_alpha":         trial.suggest_float("reg_alpha", 1e-8, 10, log=True),
        "reg_lambda":        trial.suggest_float("reg_lambda", 1e-8, 10, log=True),
    }
    model = lgb.LGBMRegressor(**params, objective="regression", metric="mae")
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)])
    preds = model.predict(X_val)
    return mean_absolute_error(y_val, preds)

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=100)
```

> ⚠️ 100 trials × ~30s/trial = ~50 phút. Chạy background trong khi làm việc khác.

**Checklist:**
- [ ] Optuna log best params đã in ra
- [ ] Exp3 (best params) train xong
- [ ] Save `models/lgbm_exp3_best.pkl`
- [ ] Val MAE Exp3 < Exp2 (industrial helps)

---

## Thứ 5 — 2026-11-06: Kết quả sơ bộ

Compile kết quả 5 models trên val set:

| Model | MAE | RMSE | R² |
|---|---|---|---|
| Persistence | ? | ? | ? |
| Ridge | ? | ? | ? |
| LightGBM Exp1 | ? | ? | ? |
| LightGBM Exp2 | ? | ? | ? |
| LightGBM Exp3 | ? | ? | ? |

**Checklist:**
- [ ] Bảng kết quả đã điền đủ
- [ ] Exp3 là model tốt nhất (MAE thấp nhất)
- [ ] Không có dấu hiệu leakage (R² không quá 0.99)

---

## Thứ 6 — 2026-11-07: Buffer + Fix

- Fix nếu có model không hội tụ
- Kiểm tra learning curves
- Update tracking: Phase 4 → 🟢 Hoàn thành

---

## Files tạo tuần này

```
src/models/
  baseline.py
  train_lgbm.py

models/
  ridge.pkl
  lgbm_exp1.pkl
  lgbm_exp2.pkl
  lgbm_exp3_best.pkl
```

---

## Definition of Done

- [ ] 4 model files tồn tại trong `models/`
- [ ] Persistence MAE đã tính (không cần save file)
- [ ] Exp3 MAE < Exp1 MAE (ablation meaningful)
- [ ] Best Optuna params đã log
