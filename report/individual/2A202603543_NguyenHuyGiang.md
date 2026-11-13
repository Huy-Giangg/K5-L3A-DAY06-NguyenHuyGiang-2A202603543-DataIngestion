# Báo cáo cá nhân — Day 6: Data Ingestion Engineering

## Dữ liệu và pipeline
- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**
  - *Chủ đề:* Báo cáo nợ công và tài chính phát triển quốc tế — *International Debt Report 2026* do The World Bank Group phát hành.
  - *Nguồn và giấy phép:* World Bank Open Knowledge Repository (DOI: `10.1596/978-1-4648-2355-8`, handle: `10986/45762`). Giấy phép chính thức **Creative Commons Attribution 3.0 IGO (CC BY 3.0 IGO)**, được phép trích xuất, nghiên cứu và tái phân phối tự do có ghi nguồn.
  - *Số trang và phạm vi:* Chọn dải trang từ **Trang PDF 21 đến Trang PDF 55** (tổng cộng 35 trang vật lý, tương ứng phần *Key Takeaways* và *Chapter 1: Analysis of External Debt Stocks and Debt Flows*).
  - *Quy tắc tính trang hợp lệ:* Chỉ tính các trang chứa văn bản phân tích thực thụ ($\ge 50$ ký tự); loại bỏ các trang bìa lót, trang mục lục (trang 1–20) và các trang biểu đồ rỗng (trang 22, 25, 26). Tổng số trang nội dung hợp lệ là **32 trang** (đạt 74.933 ký tự), thỏa mãn điều kiện $\ge 30$ trang của đề bài.
- **Chuẩn hóa, lỗi và giới hạn:**
  - Văn bản PDF là vector native text chất lượng cao (Adobe InDesign), trích xuất trực tiếp bằng `pypdf`, không cần xử lý OCR.
  - Chuẩn hóa Unicode bằng `unicodedata.normalize("NFKC")`, thay thế khoảng trắng không ngắt `\u00a0`, chuẩn hóa dấu ngắt dòng `\r\n` thành `\n`, thu gọn khoảng trắng thừa nhưng bảo toàn cấu trúc xuống dòng kép `\n\n` giữa các đoạn văn.
  - *Ghi nhận:* Phát hiện 3 trang có nội dung chữ tối thiểu hoặc chỉ chứa hình vẽ/tiêu đề phân tách (trang 22, 25, 26) đã được hệ thống ghi log và bỏ qua hợp lệ.
- **Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí:**
  - *Embedding model:* `sentence-transformers/all-MiniLM-L6-v2` chạy local trên CPU, kích thước vector **384 chiều**, chuẩn hóa vector $L_2$ (`normalize_embeddings=True`).
  - *Vector store:* `Qdrant` (thư viện `qdrant-client` chạy chế độ local storage bền vững tại `./qdrant_db`).
  - *Distance Metric:* Cosine Similarity (`Distance.COSINE`).
  - *Lệnh chạy pipeline:* `python -m starter.src.run`
  - *Chi phí:* $0.00 (hoàn toàn mã nguồn mở và chạy offline trên máy cá nhân).
- **Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn:**
  - *Metadata bắt buộc:* `document_id` (`"worldbank-idr-2026"`), `source` (`"data/international_debt_report_2026.pdf"`), `page` (số trang vật lý PDF, 1-based index).
  - *Trường lọc bổ sung:* `chapter` (nhận giá trị `"Key Takeaways"` cho trang 21–24 và `"Chapter 1"` cho trang 25–55) và `section` (tiêu đề phân mục).
  - *Lý do chọn:* Tài liệu báo cáo có cấu trúc phân tầng tự nhiên rất rõ giữa phần tóm tắt vĩ mô (*Key Takeaways*) và phần phân tích chi tiết từng nhóm nước (*Chapter 1*). Trường `chapter` giúp khoanh vùng ngữ cảnh, loại trừ các đoạn văn bàn về cùng chủ đề nhưng khác cấp độ phân tích.

---

## Cấu hình và benchmark
- **A / B / C (tham số cụ thể, khác biệt duy nhất B–C):**
  - *Cấu hình A (Fixed-size):* Kích thước chunk cố định 500 ký tự, overlap 50 ký tự (`fixed_size`). Metadata cơ bản, truy xuất Top-3 không áp dụng filter.
  - *Cấu hình B (Paragraph-aware):* Cắt theo cấu trúc đoạn văn tự nhiên (`\n\n`), gộp các đoạn nhỏ và giới hạn kích thước tối đa 800 ký tự (`by_paragraph`). Cùng metadata như A, truy xuất Top-3 không áp dụng filter.
  - *Cấu hình C (B + Metadata Filter):* Dùng chung 100% cách chunking và collection của Cấu hình B. Khác biệt duy nhất: khi câu hỏi có trường `filter` (ví dụ `{"chapter": "Key Takeaways"}`), hệ thống kích hoạt bộ lọc metadata trong Qdrant.
- **≥20 câu: phân chia ≥15 dev / ≥5 test, câu metadata filter và cách kiểm chứng evidence:**
  - Bộ câu hỏi gồm đúng **20 câu** được lưu tại `benchmark/questions.json`:
    - **15 câu Dev** (`q01` $\rightarrow$ `q15`): Dùng để khảo sát, tinh chỉnh và theo dõi hành vi pipeline.
    - **5 câu Test** (`q16` $\rightarrow$ `q20`): Tập holdout độc lập, giữ nguyên để đánh giá cuối cùng.
    - Có **3 câu hỏi có Filter** (`q03`, `q07` thuộc Dev và `q17` thuộc Test) kiểm tra khả năng lọc metadata `chapter`.
  - Toàn bộ 20 câu đều được kiểm chứng đối soát chuỗi ký tự (`evidence_quote`) trùng khớp 100% với nội dung trang gốc `gold_page` trước khi chạy thử nghiệm.
- **Tiêu chí chọn chiến lược đã chốt trước khi xem test:**
  - *Ưu tiên 1:* Độ chính xác truy xuất bằng chứng (Evidence Hit@3) trên tập Dev.
  - *Ưu tiên 2:* Tính toàn vẹn ngữ cảnh (Chunk Coherence) và chất lượng bằng chứng (Grounding Quality).
  - *Ưu tiên 3:* Hiệu quả tài nguyên (thời gian embedding và số lượng chunk sinh ra).

---

## Kết quả

### Bảng 1: Chỉ số Retrieval & Tài nguyên
| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Config A (Fixed 500/50)** | Dev | 8/15 (53.3%) | 10/15 (66.7%) | 176 | 3.90s | $0.00 |
| | Test | 2/5 (40.0%) | 4/5 (80.0%) | 176 | — | $0.00 |
| | **Overall** | **10/20 (50.0%)** | **14/20 (70.0%)** | **176** | **3.90s** | **$0.00** |
| **Config B (Paragraph-aware)** | Dev | 10/15 (66.7%) | 11/15 (73.3%) | 121 | 2.89s | $0.00 |
| | Test | 5/5 (100.0%) | 5/5 (100.0%) | 121 | — | $0.00 |
| | **Overall** | **15/20 (75.0%)** | **16/20 (80.0%)** | **121** | **2.89s** | **$0.00** |
| **Config C (B + Metadata Filter)** | Dev | 11/15 (73.3%) | 12/15 (80.0%) | 121 | 0.00s | $0.00 |
| | Test | 5/5 (100.0%) | 5/5 (100.0%) | 121 | — | $0.00 |
| | **Overall** | **16/20 (80.0%)** | **17/20 (85.0%)** | **121** | **0.00s** | **$0.00** |

### Bảng 2: Đánh giá Thủ công 5 Khía cạnh
| Strategy | Coherence trung bình /2 (n=10) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N) | Grounding 0/1/2 (số câu) và trung bình /2 (n=5) |
|---|:---:|:---:|:---:|:---:|
| **Config A** | 1.00 / 2.0 | 15/15 (100%) | N/A (không hỗ trợ filter) | 0: 0 câu, 1: 1 câu, 2: 4 câu (TB: 1.80 / 2.0) |
| **Config B** | 2.00 / 2.0 | 15/15 (100%) | N/A (không dùng filter) | 0: 0 câu, 1: 0 câu, 2: 5 câu (TB: 2.00 / 2.0) |
| **Config C** | 2.00 / 2.0 | 15/15 (100%) | 15/15 (100%) | 0: 0 câu, 1: 0 câu, 2: 5 câu (TB: 2.00 / 2.0) |

- **Đường dẫn trace, nhãn thủ công và cách chọn mẫu:**
  - *Trace truy xuất:* File `results/retrieval_trace.json` (chứa đầy đủ top-3 hits, cosine similarity, trang truy xuất và nhãn hit/miss).
  - *Summary chỉ số:* File `results/summary.json` và `artifacts/experiment_log.csv`.
  - *Mẫu chọn kiểm toán Coherence:* Chọn đoạn văn đầu tiên của 10 trang nguồn đã sắp xếp cố định trước: trang 21, 23, 27, 28, 29, 30, 31, 32, 33, 34.
  - *Mẫu chọn Grounding & Metadata:* Toàn bộ 5 câu tập Test (`q16` đến `q20`) nhân với Top-3 hits (tổng cộng 15 records).

---

## Phân tích và kết luận

### 1. So sánh đối chứng A–B và B–C:
- **So sánh A–B (Tác động của Chunking):**
  - Cấu hình B vượt trội toàn diện so với Cấu hình A: Hit@1 tổng thể tăng từ **50.0% lên 75.0%** (+25%), Hit@3 tăng từ **70.0% lên 80.0%** (+10%). Điểm Coherence tăng gấp đôi từ **1.00/2.0 lên 2.00/2.0**.
  - Việc cắt cố định (A) thường xuyên chém ngang câu, làm tách rời số liệu kinh tế và chủ ngữ. Trong khi đó, Cấu hình B gom trọn vẹn ngữ cảnh của đoạn văn, giúp vector embedding phản ánh chính xác ngữ nghĩa tổng thể.
  - Về tài nguyên, Cấu hình B chỉ sinh ra **121 chunks** (giảm 31.25% so với 176 chunks của A), giúp giảm thời gian embedding từ 3.90s xuống 2.89s và tiết kiệm đáng kể dung lượng bộ nhớ vector index.
- **So sánh B–C (Tác động của Metadata Filter):**
  - Cấu hình C nâng Hit@1 trên tập Dev từ **66.7% lên 73.3%** và Hit@3 từ **73.3% lên 80.0%**.
  - Tỷ lệ tuân thủ filter ở câu Test `q17` đạt **100%** (3/3 chunk ở Top-3 đều thuộc đúng phân vùng `Key Takeaways`, loại bỏ hoàn toàn các chunk nhiễu ở `Chapter 1`).
  - Do dùng chung collection với B, Cấu hình C không tốn thêm bất kỳ tài nguyên embedding hay dung lượng lưu trữ nào (0.00s).

### 2. Hai ví dụ ca lỗi tiêu biểu (Error Analysis):
- **Ca lỗi 1: Lỗi do Fixed-size cắt vụn câu (Cấu hình A — Câu `q20`, Gold Page 21):**
  - *Câu hỏi:* So sánh sự khác biệt về tình hình nợ giữa các nước IDA và các nền kinh tế đang phát triển khác.
  - *Nguyên nhân:* Đoạn văn gốc trên trang 21 có cấu trúc so sánh đối chiếu gồm 3 câu liên tiếp. Cửa sổ 500 ký tự của Cấu hình A đã cắt đứt đoạn văn ngay giữa câu so sánh. Hệ thống truy xuất được 2 chunk liền kề nhưng mỗi chunk chỉ chứa 1 nửa thông tin, dẫn đến `evidence_found = False` ở cả Top-3 hits (Hit@3 = 0, Grounding = 1).
  - *Khắc phục:* Ở Cấu hình B, toàn bộ đoạn văn được giữ trọn vẹn trong chunk `worldbank-idr-2026_p21_para_001`, đạt Hit@1 với điểm cosine 0.7445.
- **Ca lỗi 2: Lỗi nhiễu phân vùng do thiếu Filter (Cấu hình B — Câu `q17`, Gold Page 21):**
  - *Câu hỏi:* Đánh giá gánh nặng nợ của các nước IDA trong phần tổng quan *Key Takeaways*.
  - *Nguyên nhân:* Dù Cấu hình B lấy đúng chunk trang 21 ở Rank 1, nhưng Rank 2 và Rank 3 lại lấy nhầm các chunk ở trang 37 và 51 (thuộc Chapter 1) vì các trang này cũng chứa tần suất cao các từ khóa `"IDA-eligible"` và `"debt burdens"`.
  - *Khắc phục:* Ở Cấu hình C, nhờ bộ lọc `chapter: "Key Takeaways"`, các chunk gây nhiễu ở Chapter 1 bị triệt tiêu hoàn toàn, Top-3 hits chỉ gồm các đoạn thuộc đúng trang 21 và 23.

### 3. Chiến lược lựa chọn, đánh đổi và điều kiện áp dụng:
- **Chiến lược được chọn:** **Cấu hình C (Paragraph-aware Chunking kết hợp Metadata Filter)** là chiến lược tối ưu nhất, đạt điểm cân bằng tuyệt đối giữa độ chính xác truy xuất (Hit@3 = 85.0%), chất lượng grounding (2.00/2.0), tính mạch lạc (2.00/2.0) và tiết kiệm tài nguyên.
- **Đánh đổi (Trade-offs):** Chunking theo đoạn văn có thể tạo ra các chunk có độ dài không đồng đều (từ 200 đến 800 ký tự). Ngoài ra, Metadata Filter đòi hỏi hệ thống upstream hoặc người dùng phải cung cấp metadata phân vùng ngữ cảnh trước khi query.
- **Điều kiện áp dụng:** Rất phù hợp cho các tài liệu phân tích chính sách, báo cáo tài chính, tài liệu kỹ thuật có cấu trúc chương/mục rõ ràng.

### 4. Hạn chế của nghiên cứu:
- Kích thước tập Test còn nhỏ (5 câu) mang tính chất minh họa kiểm toán mẫu, chưa đủ lớn để đại diện cho toàn bộ các tình huống người dùng thực tế.
- Việc chấm Coherence và Grounding được thực hiện thủ công bởi tác giả nên có thể tồn tại rủi ro thiên lệch chủ quan.
- Thời gian đo lường embedding chạy trên môi trường CPU cá nhân, có thể dao động nhẹ tùy thuộc vào tải nền của hệ điều hành.

### 5. Hướng cải tiến mở rộng (Nếu làm lại):
- Triển khai **Hybrid Retrieval**: Kết hợp mô hình Dense Embedding hiện tại với mô hình từ khóa thưa như **BM25** (Reciprocal Rank Fusion) để xử lý tốt hơn các câu hỏi chứa mã định danh, từ viết tắt đặc thù hoặc tên riêng.
- Bổ sung kỹ thuật **Hierarchical / Parent-Document Retrieval**: Lưu các chunk nhỏ để vector search chính xác, nhưng trả về cho LLM toàn bộ đoạn văn cha (Parent Chunk) để tối ưu hóa ngữ cảnh đọc hiểu.
