# Group Report — Day 10: Data Pipeline & Data Observability

> Báo cáo chung của nhóm Kocoten (K4-L3B-DAY10). Thể hiện toàn bộ kết quả thực thi end-to-end từ Ingestion, Cleaning, Quality Gate GX 1.x, ChromaDB Vector Index, Đo lường suy giảm (Data Corruption) và Năng lực tự phục hồi (Idempotent Repair).

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4-L3-DAY10               |
| Tên nhóm         | Kocoten                   |
| Repository         | https://github.com/ngoclongdo/K4-L3B-DAY10-Kocoten-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Đỗ Nguyễn Ngọc Long | 2A202602390 | Trưởng nhóm / Pipeline Integrator | `core/`, `corruption.py`, `phase1.py`, `corruption_flow.py`, `script/` |
| 2 | Cao Đức Anh | 2A202602754 | Data Foundation & Recovery | `src/ingestion/crossref.py`, `cleaning.py`, raw & clean artifacts |
| 3 | Nguyễn Tuấn Anh | 2A202602535 | RAG & Vector Index | `src/retrieval/index.py`, `embeddings.py`, ChromaDB collections |
| 4 | Phùng Đức Đăng | 2A202602956 | Observability & Evaluation | `src/observability/quality.py` (GX 1.x), `testset.py`, reporting |

## 2. Tóm tắt kết quả

Nhóm Kocoten đã xây dựng và kiểm chứng thành công toàn diện hệ thống Data Pipeline tích hợp Data Observability cho RAG Agent theo chuẩn mực sản xuất:

1. **Baseline Phase 1:** Thu thập metadata bài báo học thuật qua Crossref REST API (có cơ chế Offline Fallback tự động khi gặp HTTP 429), chuẩn hóa và làm sạch 24 bài báo, thiết lập chốt kiểm định **Great Expectations 1.x** (Ephemeral Context với 4 Expectations cốt lõi) kết hợp giám sát **Freshness SLA** (`age_days > 180`). Hệ thống tự động sinh bộ Benchmark Test Set 10 câu hỏi Ground Truth phủ 4 dạng bài toán và đánh chỉ mục bền vững vào ChromaDB (`papers-baseline`), đạt **Retrieval Hit Rate tuyệt đối 1.0000** và Mean Token F1 0.5154.
2. **Corruption & Silent Failure:** Nhóm đã thiết kế bộ tiêm lỗi thực nghiệm gồm 6 sự cố dữ liệu thực tế (bỏ rơi 20% bài báo mới, xóa tóm tắt, chèn chuỗi rác, cắt tiêu đề, lùi ngày xuất bản 365 ngày và nhân đôi bản ghi). Kết quả kiểm chứng chứng minh: Data Quality Gate lập tức báo động **FAIL**, Freshness SLA chuyển cờ **STALE**, và RAG Agent bị suy giảm hiệu năng nghiêm trọng (**Retrieval Hit Rate rơi xuống 0.7000**, Token F1 rơi xuống 0.1860, Judge Score giảm còn 1.80/5.0).
3. **Idempotent Repair:** Nhờ bảo tồn bản sao nguyên gốc ban đầu (`data/raw/crossref_records.json` làm Lineage Anchor), hệ thống kích hoạt hàm tự phục hồi `repair_from_raw_snapshot()`, tái tạo lại dữ liệu sạch và re-index ChromaDB (`papers-repaired`). Kết quả phục hồi **đạt 100%** so với baseline ban đầu.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API (hoặc Local Snapshot Fallback)
    -> data/raw/crossref_response.json & crossref_records.json (Lineage Anchor)
    -> src/ingestion/cleaning.py (Chuẩn hóa, age_days, text_for_embedding, deduplicate)
    -> data/clean/papers_clean.csv & papers_clean.json
    -> src/observability/quality.py (Great Expectations 1.x Ephemeral & Freshness SLA)
    -> src/evaluation/testset.py (Sinh 10 câu hỏi Ground Truth qua 4 domains)
    -> src/retrieval/index.py (Dense Embedding MiniLM -> ChromaDB collection: papers-baseline)
    -> script/run_phase1.py (Đánh giá Baseline RAG: Hit Rate, Token F1, LLM Judge)
    -> data/reports/phase1_report.md
    -> src/ingestion/corruption.py (Tiêm 6 kịch bản lỗi thực nghiệm -> corruption_log.json)
    -> ChromaDB collection: papers-corrupted (Đo lường Silent Failure)
    -> Idempotent Repair từ raw records snapshot -> ChromaDB collection: papers-repaired
    -> data/reports/corruption_report.md (Bảng đối chiếu 3 trạng thái rõ ràng)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | Crossref REST API / Snapshot local | Bóc tách JSON, lọc tag rác HTML, fallback offline | `crossref_response.json`, `crossref_records.json` | Cao Đức Anh |
| **Cleaning** | `list[PaperRecord]` | Khử trùng lặp DOI, tính `age_days`, tạo `text_for_embedding` | `papers_clean.csv`, `papers_clean.json` | Cao Đức Anh |
| **Observability** | Clean / Corrupted DataFrame | Great Expectations 1.x (4 Expectations), Freshness SLA | `*_quality_report.json`, `freshness_report.json` | Phùng Đức Đăng |
| **Evaluation Set** | Clean DataFrame | Tự động sinh 10 câu hỏi Ground Truth phủ 4 bài toán | `data/eval/test_set.json` | Phùng Đức Đăng |
| **Vector Index** | DataFrame sạch & bẩn | Vectorize bằng `all-MiniLM-L6-v2`, nạp 3 ChromaDB collections | `data/chroma/`, `papers_embeddings*.json` | Nguyễn Tuấn Anh |
| **Pipelines & Flow** | Toàn bộ các module trên | Xâu chuỗi Phase 1, Phase 2, Tiêm lỗi & Idempotent Repair | `baseline_metrics.json`, `phase1_report.md`, `corruption_report.md` | Đỗ Nguyễn Ngọc Long |

## 4. Kết quả thực nghiệm đối chiếu 3 trạng thái

### Bảng tổng hợp định lượng (Ground Truth Benchmark)

| Chỉ số / Trạng thái | Baseline (Dữ liệu sạch) | Corrupted (Dữ liệu bẩn) | Repaired (Sau phục hồi) | Nhận xét & Đánh giá |
|:---|:---:|:---:|:---:|:---|
| **Retrieval Hit Rate** | **1.0000** | **0.7000** | **1.0000** | Sụt giảm mạnh khi mất tài liệu mới; phục hồi 100% sau repair |
| **Mean Token F1** | **0.5154** | **0.1860** | **0.5154** | Chất lượng văn bản câu trả lời thoái hóa nặng, hồi phục nguyên vẹn |
| **Judge Accuracy** | **0.5000** | **0.2000** | **0.5000** | Độ chính xác câu trả lời được LLM Judge chấm phục hồi |
| **Mean Judge Score** | **3.00 / 5.0** | **1.80 / 5.0** | **3.00 / 5.0** | Điểm số chất lượng câu trả lời hồi phục hoàn toàn |
| **GX 1.x Quality Gate** | **PASS** | **FAIL (Đã chặn)** | **PASS** | Chốt kiểm soát phát hiện chính xác vi phạm Null, Unique, Length |
| **Freshness SLA Status** | **FRESH** | **STALE (Cảnh báo)** | **FRESH** | SLA phát hiện kịp thời tỷ lệ bài báo quá hạn (> 180 ngày) |

### Phân tích hiện tượng Silent Failure
- Khi dữ liệu bị tiêm lỗi, hệ thống Retrieval và LLM vẫn hoạt động bình thường, không có bất kỳ Exception nào được ném ra. Tuy nhiên, do tóm tắt bị rỗng hoặc tiêu đề bị cắt, ngữ cảnh đưa vào LLM là rác hoặc sai lệch, khiến Agent trả lời sai hoặc gặp ảo giác.
- Nếu không có **Data Quality Gate (Great Expectations 1.x)** và **Freshness SLA**, hiện tượng Silent Failure này sẽ âm thầm lọt vào môi trường Production và phá hủy trải nghiệm người dùng.

### Tính Idempotent của cơ chế Phục hồi
- Cơ chế `repair_from_raw_snapshot()` chứng minh rằng khi xảy ra sự cố, hệ thống không cần chắp vá thủ công mà có thể tái tạo (reproduce) toàn bộ dữ liệu sạch và vector index từ snapshot thô ban đầu chỉ trong chưa đầy 2 giây.

## 5. Danh sách Artifacts nộp bài

- **Mã nguồn:** `src/core/`, `src/ingestion/`, `src/observability/`, `src/evaluation/`, `src/retrieval/`, `src/pipelines/`
- **Kịch bản chạy:** `script/run_phase1.py`, `script/run_corruption_flow.py`
- **Báo cáo chung:** `report/group_report.md`
- **Báo cáo cá nhân:**
  - `report/2A202602390_DoNguyenNgocLong.md`
  - `report/2A202602754_CaoDucAnh.md`
  - `report/2A202602535_NguyenTuanAnh.md`
  - `report/2A202602956_PhungDucDang.md`
- **Dữ liệu & Kết quả:**
  - `data/raw/`: `crossref_response.json`, `crossref_records.json`
  - `data/clean/`: `papers_clean.csv`, `papers_clean.json`, `papers_clean_corrupted.csv`, `papers_clean_repaired.csv`
  - `data/quality/`: `baseline_quality_report.json`, `corrupted_quality_report.json`, `freshness_report.json`
  - `data/results/`: `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_log.json`
  - `data/reports/`: `phase1_report.md`, `corruption_report.md`
  - `data/chroma/`: Lưu trữ 3 collection ChromaDB thực thi.

---
*Báo cáo được hoàn thiện và xác nhận đồng thuận bởi toàn bộ 4 thành viên nhóm Kocoten.*
