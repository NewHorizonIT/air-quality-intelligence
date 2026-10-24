# Tuần 7 — Phase 7: Paper Final + App + Submit
**2026-11-24 → 2026-11-28**

---

## Mục tiêu cuối tuần

- Paper đã submit lên hệ thống BTC FJCAI 2026 ← **ưu tiên tuyệt đối**
- Streamlit Prediction Demo chạy được
- Slides 14 trang draft xong

---

## Thứ 2 — 2026-11-24: Nhận feedback thầy + Fix paper

Thầy đã nhận draft tuần 6. Hôm nay đọc feedback và sửa:

**Các lỗi thường gặp thầy sẽ comment:**
- Kết quả thiếu discussion (chỉ list số, không giải thích)
- Introduction chưa rõ contribution
- Related work chưa đủ (thiếu paper Việt Nam / Ấn Độ)
- Figures thiếu caption đầy đủ
- References format chưa chuẩn IEEE

**Checklist:**
- [ ] Đọc hết feedback thầy
- [ ] List tất cả sửa đổi cần làm
- [ ] Fix phần Introduction + Contribution

---

## Thứ 3 — 2026-11-25: Fix Results + Figures

- Sửa Section 5 theo feedback
- Nếu thầy yêu cầu thêm experiment → chạy lại evaluate.py
- Kiểm tra tất cả figures: caption, resolution, numbering
- Đảm bảo số liệu trong text khớp với tables/figures

**Checklist:**
- [ ] Section 5 đã sửa
- [ ] Tất cả figures có caption đầy đủ
- [ ] Cross-reference figures đúng (Figure 1, 2... không nhảy số)

---

## Thứ 4 — 2026-11-26: Proofread + Format check

**Proofread:**
- Đọc lại toàn bộ paper 1 lần — không sửa nội dung, chỉ sửa ngôn ngữ
- Dùng Grammarly hoặc ChatGPT để polish tiếng Anh
- Check tất cả công thức toán có đúng không

**Format check theo template FJCAI:**
- [ ] Đúng số trang (6–8 trang)
- [ ] Font, margin, column width đúng template
- [ ] Abstract ≤ 150 words
- [ ] Keywords 4–6 từ
- [ ] Không có author info trong bản nộp (double-blind)
- [ ] File PDF export sạch, không có comment

---

## Thứ 5 — 2026-11-27: Submit paper + Streamlit app

### Submit paper — làm sớm nhất có thể

```
1. Vào portal nộp bài BTC FJCAI 2026
2. Upload PDF
3. Điền metadata: title, abstract, keywords, track
4. Submit
5. Chụp màn hình confirmation
```

> ⚠️ Không đợi đến thứ 6 — hệ thống có thể nghẽn vào ngày cuối

### Viết Streamlit Trang 2 — Prediction Demo

```python
# app/pages/02_prediction.py
st.title("PM2.5 Prediction Demo")

station = st.selectbox("Chọn trạm quan trắc", station_list)
date    = st.date_input("Chọn ngày dự đoán")

if st.button("Dự đoán PM2.5 ngày mai"):
    features = build_feature_row(station, date)
    pred = model.predict(features)[0]

    st.metric("PM2.5 dự đoán", f"{pred:.1f} µg/m³")
    if pred > 15:
        st.error("⚠️ Vượt ngưỡng WHO (15 µg/m³)")
    else:
        st.success("✓ An toàn theo WHO AQG 2021")

    # SHAP waterfall
    shap_vals = explainer.shap_values(features)
    shap.waterfall_plot(shap.Explanation(shap_vals[0], base_values=explainer.expected_value))
    st.pyplot(plt.gcf())
```

**Checklist:**
- [ ] Paper đã submit ✓ (có confirmation email/screenshot)
- [ ] Streamlit app chạy được: `streamlit run app/main.py`
- [ ] Prediction demo hoạt động end-to-end

---

## Thứ 6 — 2026-11-28: Slides + Wrap up

### Chuẩn bị slides trình bày (14 slides)

```
Slide 1 : Title + Author
Slide 2 : Motivation — Delhi pollution stats
Slide 3 : Research Question + Contribution
Slide 4 : Data Sources (3 nguồn, map 58 stations)
Slide 5 : Methodology overview (pipeline diagram)
Slide 6 : Feature Engineering (24 features table)
Slide 7 : Model Architecture (LightGBM + Optuna)
Slide 8 : Ablation Study Design
Slide 9 : Results — Main table (5 models × metrics)
Slide 10: Results — Ablation bar chart
Slide 11: Seasonal Analysis
Slide 12: SHAP Feature Importance
Slide 13: Demo screenshot (Streamlit app)
Slide 14: Conclusion + Future Work + Q&A
```

**Tip:** Mỗi slide 1 message chính. Không nhồi text.

**Checklist:**
- [ ] 14 slides draft xong
- [ ] **Milestone M6: Paper Submitted** ✓
- [ ] Update tracking: tất cả phases → 🟢

---

## Definition of Done — Toàn dự án

- [ ] `paper/` — PDF đã submit lên BTC, có confirmation
- [ ] `models/lgbm_exp3_best.pkl` — model chính đã train
- [ ] `app/main.py` — Streamlit chạy được
- [ ] `reports/figures/` — đủ figures cho paper
- [ ] `data/exports/results_summary.csv` — kết quả đầy đủ
- [ ] Slides 14 trang draft

---

## Nếu bị trễ — Scope cuts theo thứ tự

```
1. Power BI dashboard          → ghi "Future Work"
2. Streamlit Trang 1 + 3      → chỉ giữ Trang 2 Prediction Demo
3. Slides                     → làm sau submit paper
4. Per-station error analysis → bỏ khỏi paper
5. Seasonal SHAP              → chỉ giữ global SHAP
```

**Không được cắt:** Paper submit.
