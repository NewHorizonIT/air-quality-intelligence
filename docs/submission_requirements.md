# Yêu Cầu Nộp Báo Cáo Môn Học

## Hạng mục nộp

### 1. Quyển báo cáo
- In 2 mặt, trình bày theo quy định của Khoa
- Định dạng file: `.docx`

### 2. Thư mục nộp
Đặt tên theo format: `<MSSV>NGUYENVANA+<MSSV>LETHIC`

Cấu trúc thư mục:
```
<MSSV>NGUYENVANA+<MSSV>LETHIC/
├── a_report/
│   └── BaoCao_AirQualityIntelligence.docx     ← Nội dung quyển báo cáo
├── b_slides/
│   └── Slides_AirQualityIntelligence.pptx     ← Trình bày báo cáo
├── c_data/
│   ├── raw/                                    ← Dữ liệu thô từ OpenAQ
│   ├── cleaned/                                ← Dữ liệu đã xử lý
│   └── external/                               ← Weather, Industrial data
└── d_source/
    ├── src/ingestion/                          ← Thu thập dữ liệu
    ├── src/processing/                         ← Xử lý dữ liệu
    ├── src/features/                           ← Feature engineering
    ├── src/models/                             ← Train & evaluate models
    └── notebooks/eda.ipynb                     ← Phân tích khám phá
```

## Checklist trước khi nộp

- [ ] Báo cáo đầy đủ các chương theo cấu trúc quy định
- [ ] Slides có đủ nội dung trình bày
- [ ] Data đã được làm sạch và sẵn sàng
- [ ] Source code chạy được, có hướng dẫn trong README
- [ ] Tên thư mục đúng format MSSV
