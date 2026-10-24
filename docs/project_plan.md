# Project Plan — Air Quality Intelligence Platform

## Thông tin dự án

| | |
|---|---|
| **Đề tài** | Dự đoán PM2.5 tại Delhi tích hợp khí tượng và công nghiệp |
| **Hội thảo** | FJCAI 2026 |
| **Deadline nộp paper** | Tháng 11/2026 (chờ thông báo chính xác từ BTC) |
| **Ngày bắt đầu** | 2026-10-13 |
| **Team** | 1 người |
| **Thời gian còn lại** | ~7 tuần |

---

## Timeline Tổng Quan

```
Tuần 1   Oct 13–17   Phase 1: Data Ingestion
Tuần 2   Oct 20–24   Phase 2: Data Cleaning
Tuần 3   Oct 27–31   Phase 3: Feature Engineering + EDA
Tuần 4   Nov 03–07   Phase 4: Model Training
Tuần 5   Nov 10–14   Phase 5: Evaluation + Interpretation
Tuần 6   Nov 17–21   Phase 6: Paper Writing (draft)
Tuần 7   Nov 24–28   Phase 7: Paper Final + App + Submit
                              ↑
                         DEADLINE
```

---

## Critical Path

```
Ingestion → Cleaning → Feature Engineering → Model Training → Evaluation → Paper
```

Mọi task nằm ngoài critical path đều có thể trễ mà không ảnh hưởng deadline.

---

## Phase 1: Data Ingestion
**Deadline: 2026-10-17**

| Task | Mô tả | Độ ưu tiên | Est. |
|---|---|---|---|
| 1.1 | Viết `src/ingestion/openaq_client.py` — OpenAQ API wrapper | Critical | 0.5 ngày |
| 1.2 | Viết `src/ingestion/fetch_air_quality.py` — fetch + save raw parquet | Critical | 1 ngày |
| 1.3 | Viết `src/ingestion/fetch_weather.py` — Open-Meteo per 46 stations | Critical | 1 ngày |
| 1.4 | Download WRI GPPD CSV + viết `src/ingestion/fetch_industrial.py` | Critical | 0.5 ngày |
| 1.5 | Verify data: kiểm tra shape, date range, null counts | Critical | 0.5 ngày |

**Definition of Done:**
- [ ] `data/raw/delhi_raw.parquet` tồn tại, có đủ data 2022–2024
- [ ] `data/external/weather.parquet` có 6 weather variables × 46 stations × 3 năm
- [ ] `data/external/industrial.parquet` có nhà máy trong buffer 50km Delhi

---

## Phase 2: Data Cleaning
**Deadline: 2026-10-24**

| Task | Mô tả | Độ ưu tiên | Est. |
|---|---|---|---|
| 2.1 | Viết `src/processing/clean_air_quality.py` theo ADR-005 | Critical | 1.5 ngày |
| 2.2 | Viết `src/processing/clean_weather.py` theo ADR-005 | Critical | 0.5 ngày |
| 2.3 | Viết `src/processing/clean_industrial.py` theo ADR-005 | Critical | 0.5 ngày |
| 2.4 | Verify: kiểm tra null, distribution, outlier sau clean | Critical | 0.5 ngày |
| 2.5 | Cross-station suspicious flag implementation | High | 1 ngày |

**Definition of Done:**
- [ ] `data/cleaned/air_quality.parquet` có cột `is_suspicious`
- [ ] O3 đã convert ppm → µg/m³
- [ ] Không còn giá trị âm, không còn CO = 1.5e25
- [ ] Weather bounds đã validate

---

## Phase 3: Feature Engineering + EDA
**Deadline: 2026-10-31**

| Task | Mô tả | Độ ưu tiên | Est. |
|---|---|---|---|
| 3.1 | Viết `src/features/build_features.py` — merge 3 nguồn | Critical | 1.5 ngày |
| 3.2 | Implement lag features (lag 1,2,3,7) + rolling stats | Critical | 0.5 ngày |
| 3.3 | Cyclical encoding month/dow + one-hot season | Critical | 0.5 ngày |
| 3.4 | Industrial distance + capacity features (Haversine) | Critical | 0.5 ngày |
| 3.5 | Train/Val/Test split + save parquet | Critical | 0.5 ngày |
| 3.6 | EDA notebook — plots cho paper (seasonal, spatial, correlation) | High | 1.5 ngày |

**Definition of Done:**
- [ ] `data/features/train.parquet`, `val.parquet`, `test.parquet` tồn tại
- [ ] 24 features đúng như ADR-003
- [ ] Không có data leakage (shift trước rolling)
- [ ] EDA notebook có đủ plots dùng được cho paper

---

## Phase 4: Model Training
**Deadline: 2026-11-07**

| Task | Mô tả | Độ ưu tiên | Est. |
|---|---|---|---|
| 4.1 | Viết `src/models/baseline.py` — Persistence + Ridge | Critical | 0.5 ngày |
| 4.2 | Viết `src/models/train_lgbm.py` — LightGBM + Optuna | Critical | 1.5 ngày |
| 4.3 | Chạy Exp 1: LightGBM + Temporal features only | Critical | 0.5 ngày |
| 4.4 | Chạy Exp 2: LightGBM + Temporal + Weather | Critical | 0.5 ngày |
| 4.5 | Chạy Exp 3: LightGBM + Temporal + Weather + Industrial | Critical | 0.5 ngày |
| 4.6 | Save models: `models/lgbm_exp1.pkl`, `exp2.pkl`, `exp3.pkl`, `ridge.pkl` | Critical | 0.5 ngày |

**Definition of Done:**
- [ ] 5 models đã train và save
- [ ] Optuna log available (best params)
- [ ] Không có data leakage trong training

---

## Phase 5: Evaluation + Interpretation
**Deadline: 2026-11-14**

| Task | Mô tả | Độ ưu tiên | Est. |
|---|---|---|---|
| 5.1 | Viết `src/models/evaluate.py` — MAE/RMSE/R²/MAPE | Critical | 1 ngày |
| 5.2 | Seasonal breakdown (winter/spring/monsoon/autumn) | Critical | 0.5 ngày |
| 5.3 | Viết `src/models/interpret.py` — SHAP analysis | Critical | 1 ngày |
| 5.4 | Generate tất cả figures cho paper (ablation chart, SHAP bar, beeswarm) | Critical | 1 ngày |
| 5.5 | Per-station error analysis | High | 0.5 ngày |

**Definition of Done:**
- [ ] Bảng kết quả hoàn chỉnh (5 models × 4 metrics)
- [ ] SHAP bar chart + beeswarm plot
- [ ] Seasonal MAE chart
- [ ] Tất cả figures save vào `reports/figures/`

---

## Phase 6: Paper Writing
**Deadline: 2026-11-21**

| Task | Mô tả | Độ ưu tiên | Est. |
|---|---|---|---|
| 6.1 | Tải template FJCAI 2026 từ website BTC | Critical | 0.5 ngày |
| 6.2 | Viết Section 1: Introduction | Critical | 0.5 ngày |
| 6.3 | Viết Section 2: Related Work (tìm 8–10 papers) | Critical | 1 ngày |
| 6.4 | Viết Section 3: Data & Study Area | Critical | 0.5 ngày |
| 6.5 | Viết Section 4: Methodology | Critical | 1 ngày |
| 6.6 | Viết Section 5: Results & Discussion | Critical | 1.5 ngày |
| 6.7 | Viết Section 6: Conclusion + References | Critical | 0.5 ngày |
| 6.8 | Gửi thầy review lần 1 | Critical | — |

**Definition of Done:**
- [ ] Draft hoàn chỉnh 6–8 trang đúng template
- [ ] Tất cả figures đã chèn vào paper
- [ ] References đầy đủ IEEE format
- [ ] Thầy đã nhận bản draft

---

## Phase 7: Paper Final + App + Submit
**Deadline: 2026-11-28**

| Task | Mô tả | Độ ưu tiên | Est. |
|---|---|---|---|
| 7.1 | Chỉnh sửa paper theo feedback thầy | Critical | 1 ngày |
| 7.2 | Proofread lần cuối + check format | Critical | 0.5 ngày |
| 7.3 | Submit paper qua hệ thống BTC | Critical | 0.5 ngày |
| 7.4 | Build Streamlit Trang 2 (Prediction Demo) | High | 2 ngày |
| 7.5 | Chuẩn bị slides trình bày (14 slides) | High | 1 ngày |

**Definition of Done:**
- [ ] Paper đã submit, có confirmation từ hệ thống
- [ ] Streamlit prediction demo chạy được
- [ ] Slides draft hoàn chỉnh

---

## Milestones

| Milestone | Ngày | Ý nghĩa |
|---|---|---|
| 🟡 **M1: Data Ready** | 2026-10-24 | Toàn bộ data đã fetch và clean xong |
| 🟡 **M2: Features Ready** | 2026-10-31 | Train/val/test parquet đã build |
| 🟡 **M3: Models Trained** | 2026-11-07 | 5 models đã train, kết quả có |
| 🟡 **M4: Results Ready** | 2026-11-14 | Tất cả figures và metrics hoàn chỉnh |
| 🟡 **M5: Draft Submitted to Supervisor** | 2026-11-21 | Thầy nhận bản draft |
| 🔴 **M6: Paper Submitted** | 2026-11-28 | Nộp cho BTC FJCAI 2026 |

---

## Risk Register

| Rủi ro | Khả năng | Impact | Mitigation |
|---|---|---|---|
| OpenAQ API thay đổi / rate limit | Trung bình | Cao | Cache ngay sau fetch, không re-fetch |
| Open-Meteo thiếu data một số ngày | Thấp | Trung bình | Forward fill ≤3 ngày (ADR-005) |
| WRI GPPD thiếu nhà máy Delhi | Trung bình | Trung bình | Ghi nhận là limitation trong paper |
| Model accuracy thấp hơn kỳ vọng | Trung bình | Cao | Vẫn có kết quả để report; focus vào ablation |
| Trễ deadline 1 tuần | Cao | Cao | Buffer 3 ngày trước deadline thật |
| Template FJCAI không tương thích | Thấp | Trung bình | Tải template sớm ở Phase 6 |
| Thầy review chậm | Trung bình | Trung bình | Gửi draft sớm cuối tuần 6 |

---

## Scope Cuts nếu bị trễ

Nếu tiến độ bị trễ, cắt theo thứ tự này (ít ảnh hưởng paper nhất trước):

```
1. Power BI dashboard          → ghi là Future Work
2. Streamlit Trang 1 + 3      → chỉ giữ Trang 2 (Prediction Demo)
3. Per-station error analysis  → bỏ, chỉ report overall metrics
4. Cross-station suspicious flag → ghi là Future Work
5. Seasonal SHAP               → chỉ giữ global SHAP
```

Không được cắt: Ingestion, Cleaning, Features, Model Training, Evaluation, Paper.

---

## Tracking Template (cập nhật hàng tuần)

| Phase | Status | % Done | Ghi chú |
|---|---|---|---|
| Phase 1: Ingestion | 🔴 Chưa bắt đầu | 0% | |
| Phase 2: Cleaning | 🔴 Chưa bắt đầu | 0% | |
| Phase 3: Features + EDA | 🔴 Chưa bắt đầu | 0% | |
| Phase 4: Model Training | 🔴 Chưa bắt đầu | 0% | |
| Phase 5: Evaluation | 🔴 Chưa bắt đầu | 0% | |
| Phase 6: Paper Writing | 🔴 Chưa bắt đầu | 0% | |
| Phase 7: Final + Submit | 🔴 Chưa bắt đầu | 0% | |

**Legend:** 🔴 Chưa bắt đầu · 🟡 Đang làm · 🟢 Hoàn thành · ⚠️ Bị block

---

## Ghi Chú Quan Trọng

1. **Deadline thật của BTC** chưa có — cập nhật ngay khi có thông báo chính thức
2. **Paper phải có người trình bày** tại hội thảo nếu được accept (ADR không nộp = bị gỡ)
3. **Không submit sau deadline** — BTC không nhận bài trễ
4. **Gửi thầy review trước Nov 21** — cần ít nhất 3–5 ngày để thầy đọc và feedback
