from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "de_cuong_dang_ky.docx")


def set_cell_bg(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def add_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        if level == 1:
            run.font.color.rgb = RGBColor(0x1A, 0x56, 0x76)
        elif level == 2:
            run.font.color.rgb = RGBColor(0x2E, 0x75, 0x96)
    return h


def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Header row
    hdr = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        set_cell_bg(cell, "1A5676")
        p = cell.paragraphs[0]
        run = p.add_run(h)
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run.font.size = Pt(9)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Data rows
    for r_idx, row_data in enumerate(rows):
        row = table.rows[r_idx + 1]
        bg = "EBF5FB" if r_idx % 2 == 0 else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            set_cell_bg(cell, bg)
            p = cell.paragraphs[0]
            run = p.add_run(val)
            run.font.size = Pt(9)

    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)

    doc.add_paragraph()
    return table


def build():
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3)
        section.right_margin = Cm(2)

    # Default font
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    # Title block
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("BẢN ĐĂNG KÝ ĐỀ TÀI")
    run.bold = True
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0x1A, 0x56, 0x76)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = sub.add_run("Đồ Án Phân Tích Dữ Liệu")
    run2.font.size = Pt(13)
    run2.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    doc.add_paragraph()

    topic_label = doc.add_paragraph()
    run3 = topic_label.add_run("Tên đề tài: ")
    run3.bold = True
    run3.font.size = Pt(12)
    run4 = topic_label.add_run(
        "Dự đoán nồng độ PM2.5 ngày hôm sau tại các trạm quan trắc Delhi "
        "sử dụng LightGBM kết hợp dữ liệu khí tượng và nguồn phát thải công nghiệp"
    )
    run4.font.size = Pt(12)

    doc.add_paragraph()

    # ── Section 1 ──────────────────────────────────────────────────────────
    add_heading(doc, "1. Chủ Đề & Câu Hỏi Phân Tích", level=1)

    add_heading(doc, "Bối cảnh", level=2)
    doc.add_paragraph(
        "Delhi là một trong những thành phố ô nhiễm không khí nghiêm trọng nhất thế giới. "
        "PM2.5 vượt ngưỡng WHO AQG (15 µg/m³) trên 90% số ngày/năm, gây ảnh hưởng trực tiếp "
        "đến sức khỏe cộng đồng. Dự đoán chính xác PM2.5 một ngày trước giúp chính quyền, "
        "bệnh viện, trường học đưa ra cảnh báo sớm."
    )

    add_heading(doc, "Người dùng kết quả", level=2)
    doc.add_paragraph(
        "Cơ quan quản lý môi trường (DPCC, CPCB), nhà nghiên cứu khoa học sức khỏe cộng đồng, "
        "ứng dụng cảnh báo chất lượng không khí."
    )

    add_heading(doc, "5 Câu hỏi phân tích", level=2)
    questions = [
        "Chỉ dùng dữ liệu lịch sử PM2.5 (lag + rolling), LightGBM dự đoán PM2.5 ngày mai với độ chính xác bao nhiêu (MAE)?",
        "Bổ sung dữ liệu khí tượng (nhiệt độ, gió, mưa, boundary layer height) cải thiện MAE thêm bao nhiêu % so với baseline chỉ dùng temporal?",
        "Bổ sung thêm dữ liệu proximity nhà máy công nghiệp có cải thiện đáng kể nữa không?",
        "Yếu tố nào quan trọng nhất trong việc dự đoán PM2.5 theo từng mùa (winter smog vs. monsoon)?",
        "Trạm quan trắc nào khó dự đoán nhất và lý do có liên quan đến khoảng cách nhà máy không?",
    ]
    for i, q in enumerate(questions, 1):
        p = doc.add_paragraph(style="List Number")
        p.add_run(q)

    add_heading(doc, "Điểm khác biệt", level=2)
    doc.add_paragraph(
        "Các đề tài phổ biến chỉ dùng dữ liệu khí tượng hoặc lịch sử AQI. Đề tài này thiết kế "
        "ablation study 3 tầng feature (temporal → weather → industrial) để đo lường đóng góp "
        "cận biên của từng nhóm, kết hợp SHAP để giải thích theo mùa và theo không gian."
    )

    # ── Section 2 ──────────────────────────────────────────────────────────
    add_heading(doc, "2. Dữ Liệu", level=1)

    add_table(
        doc,
        headers=["Nguồn", "URL / Truy cập", "Quy mô", "Trạng thái"],
        rows=[
            ["OpenAQ v3 API", "api.openaq.org", "59 trạm × 2022–2025, ~124,161 rows", "Đã fetch"],
            ["Open-Meteo ERA5 Historical", "archive-api.open-meteo.com", "Daily per-station, cùng date range", "Đã fetch"],
            ["WRI Global Power Plant DB", "datasets.wri.org", "~30 nhà máy trong bbox Delhi", "File CSV tĩnh, đã có"],
        ],
        col_widths=[3.5, 4.5, 5, 2.5],
    )

    p = doc.add_paragraph()
    p.add_run("Đơn vị quan sát: ").bold = True
    p.add_run("(station_id, date) — 1 row = 1 ngày tại 1 trạm")

    p2 = doc.add_paragraph()
    p2.add_run("Target: ").bold = True
    p2.add_run("target_pm25_next_day — nồng độ PM2.5 (µg/m³) tại ngày t+1")

    add_heading(doc, "Features (24 features)", level=2)
    add_table(
        doc,
        headers=["Nhóm", "Features", "Số lượng"],
        rows=[
            ["Temporal", "PM2.5 lag 1/2/3/7d · rolling mean 7/14/30d · rolling std 7/14d · month sin/cos · DOW sin/cos · season dummies", "13"],
            ["Weather", "Nhiệt độ · lượng mưa · tốc độ gió · hướng gió · độ ẩm · ET₀", "6"],
            ["Industrial", "Khoảng cách nhà máy gần nhất · capacity-weighted proximity · số nhà máy trong 50km", "3"],
        ],
        col_widths=[3, 11.5, 2],
    )

    add_heading(doc, "Vấn đề chất lượng dữ liệu", level=2)
    add_table(
        doc,
        headers=["Vấn đề", "Xử lý"],
        rows=[
            ["O3 có đơn vị ppm tại một số rows", "Convert: 1 ppm O3 ≈ 2000 µg/m³"],
            ["CO/NO2 từ sensor mới có đơn vị ppb", "Convert theo hệ số tương ứng"],
            ["Giá trị âm (sensor lỗi)", "Loại bỏ"],
            ["Outlier cực lớn", "Loại nếu > 3 IQR"],
            ["Missing ~15–20% tại một số trạm", "Forward-fill + flag"],
            ["1 trạm chỉ có 2 ngày (East Arjun Nagar)", "Drop trạm"],
        ],
        col_widths=[8, 8.5],
    )

    p3 = doc.add_paragraph()
    p3.add_run("Rủi ro truy cập: ").bold = True
    p3.add_run("Thấp — tất cả nguồn đều public và đã có dữ liệu thực tế.")

    # ── Section 3 ──────────────────────────────────────────────────────────
    add_heading(doc, "3. Quy Trình Công Việc", level=1)

    flow = doc.add_paragraph()
    flow.add_run(
        "Thu thập raw → Data Dictionary → Cleaning → EDA → Feature Engineering "
        "→ Temporal Split → Baseline → LightGBM 3 Experiments → Đánh giá "
        "→ SHAP Interpretation → Insight & Báo cáo → Sản phẩm cuối"
    ).italic = True

    add_table(
        doc,
        headers=["Phase", "Mô tả", "Output"],
        rows=[
            ["1. Ingestion", "Fetch OpenAQ, Open-Meteo, WRI", "data/raw/"],
            ["2. Cleaning", "Loại outlier, convert units, fill missing", "data/cleaned/"],
            ["3. EDA", "Phân tích phân phối, seasonality, tương quan không gian", "Notebook + PNG"],
            ["4. Feature Eng", "Build 24 features, kiểm tra leakage", "data/features/"],
            ["5. Train", "Persistence baseline + Ridge + 3 LightGBM experiments", "models/"],
            ["6. Evaluate", "MAE/RMSE/R² theo experiment, mùa, trạm", "Bảng kết quả"],
            ["7. SHAP", "Feature importance, phân tích theo mùa", "PNG + insight"],
            ["8. Sản phẩm", "Report + Streamlit demo", "App + PDF"],
        ],
        col_widths=[3, 8, 5.5],
    )

    # ── Section 4 ──────────────────────────────────────────────────────────
    add_heading(doc, "4. Kỹ Thuật", level=1)

    add_heading(doc, "Preprocessing", level=2)
    items = [
        "Timezone convert: UTC → Asia/Kolkata (IST)",
        "Outlier removal: giá trị âm và > 3 IQR",
        "Unit standardization: ppb/ppm → µg/m³",
        "Cyclic encoding: month và DOW dạng sin/cos (tránh boundary artifact)",
        "Season: dummies (winter / spring / monsoon / autumn)",
    ]
    for item in items:
        doc.add_paragraph(item, style="List Bullet")

    add_heading(doc, "Chống data leakage", level=2)
    leakage = [
        "Lag features chỉ sử dụng t-1 trở về trước",
        "Rolling window tính trên closed past window (không nhìn tương lai)",
        "Split hoàn toàn theo thời gian, không shuffle",
        "Target là PM2.5 ngày t+1 — không dùng bất kỳ feature nào từ ngày t+1 trở đi",
    ]
    for item in leakage:
        doc.add_paragraph(item, style="List Bullet")

    add_heading(doc, "Lý do chọn LightGBM", level=2)
    lgbm = [
        "Xử lý tốt time-series tabular data với missing values",
        "Nhanh hơn XGBoost — phù hợp chạy ablation nhiều lần",
        "Hỗ trợ native feature importance và tích hợp tốt với SHAP",
        "Hyperparameter tuning: Optuna 100 trials, objective = MAE trên val set",
    ]
    for item in lgbm:
        doc.add_paragraph(item, style="List Bullet")

    # ── Section 5 ──────────────────────────────────────────────────────────
    add_heading(doc, "5. Thực Nghiệm", level=1)

    add_heading(doc, "Chia dữ liệu (temporal — không shuffle)", level=2)
    split_p = doc.add_paragraph()
    split_p.add_run(
        "Train  :  2022-01-01 → 2024-03-31\n"
        "Val    :  2024-04-01 → 2024-09-30   (tune hyperparams)\n"
        "Test   :  2024-10-01 → 2025-12-31   (báo cáo kết quả cuối)"
    ).font.name = "Courier New"

    add_heading(doc, "4 Experiments — Ablation Study", level=2)
    add_table(
        doc,
        headers=["ID", "Model", "Feature set", "Mục đích"],
        rows=[
            ["E1", "Persistence (PM2.5(t) = dự đoán t+1)", "—", "Naive baseline"],
            ["E2", "LightGBM", "Temporal only (13 features)", "ML baseline"],
            ["E3", "LightGBM", "Temporal + Weather (19 features)", "Đo contribution của weather"],
            ["E4", "LightGBM", "Temporal + Weather + Industrial (22 features)", "Đo contribution của industrial"],
        ],
        col_widths=[1.5, 4.5, 6, 4.5],
    )

    p_metric = doc.add_paragraph()
    p_metric.add_run("Metric chính: ").bold = True
    p_metric.add_run("MAE (µg/m³) — đơn vị trực quan, dễ giải thích với người dùng cuối")

    p_metric2 = doc.add_paragraph()
    p_metric2.add_run("Metric phụ: ").bold = True
    p_metric2.add_run("RMSE, R², MAPE")

    add_heading(doc, "Phân tích lỗi", level=2)
    errors = [
        "Residual plot theo mùa",
        "Per-station MAE heatmap trên bản đồ Delhi",
        "Scatter predicted vs. actual, tô màu theo season",
    ]
    for item in errors:
        doc.add_paragraph(item, style="List Bullet")

    # ── Section 6 ──────────────────────────────────────────────────────────
    add_heading(doc, "6. Sản Phẩm Cuối", level=1)

    add_table(
        doc,
        headers=["Sản phẩm", "Mô tả"],
        rows=[
            ["data/raw/, data/cleaned/, data/features/", "Dataset thô, cleaned, features (định dạng Parquet)"],
            ["notebooks/eda.ipynb", "EDA đầy đủ với visualization"],
            ["src/", "Pipeline có thể chạy lại hoàn toàn từ đầu"],
            ["models/", "File model đã train (.pkl) cho cả 4 experiments"],
            ["reports/figures/", "Biểu đồ PNG: ablation bar chart, SHAP summary, seasonal analysis, spatial error map"],
            ["app/main.py", "Streamlit demo: chọn trạm → xem dự đoán PM2.5 ngày mai"],
            ["Report PDF", "Báo cáo 6–8 trang định dạng IEEE"],
            ["README.md", "Hướng dẫn chạy pipeline, phân công nhóm"],
        ],
        col_widths=[5.5, 11],
    )

    # Footer note
    doc.add_paragraph()
    note = doc.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_note = note.add_run(
        "Điểm tự đánh giá sơ bộ: ~44–47/50 — dữ liệu đã có, baseline xác định, "
        "metric rõ ràng, sản phẩm cuối cụ thể và tái lập."
    )
    run_note.italic = True
    run_note.font.size = Pt(10)
    run_note.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    out = os.path.abspath(OUTPUT_PATH)
    doc.save(out)
    print(f"Saved: {out}")


if __name__ == "__main__":
    build()
