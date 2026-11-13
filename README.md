# Day 06 · Data Ingestion Engineering

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Bắt đầu nhanh

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và hoàn thiện các hàm TODO, hoặc tự chọn vector store tương đương. Starter chỉ là khung: **bạn tự hiện thực pipeline và benchmark**.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Phần xử lý và benchmark do bạn tự hiện thực; không bắt buộc xây chatbot.

---

## Hướng dẫn tái lập thực nghiệm (Reproduction Guide)

### 1. Cài đặt môi trường và thư viện
Yêu cầu Python 3.11+. Cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
```

### 2. Chạy toàn bộ Pipeline và Benchmark
Chạy lệnh sau tại thư mục gốc của repository:
```bash
python -m starter.src.run
```

Pipeline sẽ tự động:
1. Đọc 35 trang PDF từ `data/international_debt_report_2026.pdf` (Trang 21–55).
2. Chuẩn hóa text và sinh chunking cho Cấu hình A (Fixed 500/50) và Cấu hình B (Paragraph-aware).
3. Tạo embedding bằng `sentence-transformers/all-MiniLM-L6-v2` và lập chỉ mục vào Qdrant local tại `./qdrant_db`.
4. Đọc 20 câu hỏi benchmark từ `benchmark/questions.json` và chạy truy xuất Top-3 cho cả 3 cấu hình A, B, C.
5. Tính toán Hit@1, Hit@3 cho tập Dev (15 câu) và tập Test (5 câu).
6. Tự động lưu log vết truy xuất vào `results/retrieval_trace.json`, bảng tổng hợp tại `results/summary.json` và cập nhật `artifacts/experiment_log.csv`.

### 3. Vị trí các tài liệu nộp bài
- **Thông tin học viên:** [STUDENT.md](STUDENT.md)
- **Manifest dữ liệu:** [data/manifest.json](data/manifest.json)
- **Bộ Benchmark 20 câu:** [benchmark/questions.json](benchmark/questions.json)
- **Báo cáo phân tích cá nhân:** [report/individual/2A202603543_NguyenHuyGiang.md](report/individual/2A202603543_NguyenHuyGiang.md)
- **Log thực nghiệm:** [artifacts/experiment_log.csv](artifacts/experiment_log.csv)
- **Trace kết quả:** [results/retrieval_trace.json](results/retrieval_trace.json)

