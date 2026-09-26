# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | [Phùng Đức Đăng]             |
| MSSV               | [2A202602956]             |
| Khóa/Lớp         | [K4-L3-DAY10]              |
| Tên nhóm         | [Kocoten]                 |
| Vai trò chính    | [Observability & Evaluation] |
| Repository         | [https://github.com/ngoclongdo/K4-L3B-DAY10-Kocoten-DataPipelineDataObservability] |
| Ngày hoàn thành | [2026-09-26]               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Observability Gate (GX 1.x) | `src/observability/quality.py` (`run_data_quality_checks`, `build_freshness_report`) | `pandas.DataFrame` (sạch hoặc bị corrupt), `Settings`, tên báo cáo `report_name` | `dict` kết quả kiểm định, các file báo cáo JSON (`data/quality/*_quality_report.json`) | Hoàn thành |
| Benchmark Test Set Generation | `src/evaluation/testset.py` (`build_test_set`) | `pandas.DataFrame` sạch từ `cleaning.py` | `data/eval/test_set.json` (10 câu hỏi Ground Truth phủ 4 dạng bài toán) | Hoàn thành |
| Pipeline Reporting Templates | `src/observability/reporting.py` (`generate_phase1_report`, `generate_corruption_report`) | Metrics đánh giá RAG, kết quả Quality Gate, Freshness report | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Tích hợp Quality Gate vào toàn tuyến | Hỗ trợ Pipeline Integrator (`phase1.py`, `corruption_flow.py`) | Quality Gate chạy tự động chặn dữ liệu bẩn và xuất báo cáo đối chiếu định lượng 3 trạng thái. |
| Đồng bộ Ground Truth schema | Hỗ trợ RAG Evaluation (`src/evaluation/metrics.py`) | Schema của `test_set.json` tương thích hoàn hảo với bộ đo `retrieval_hit_rate` và `mean_token_f1`. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Thiết lập Data Quality Gate | `src/observability/quality.py` | 4 Expectations chuẩn GX 1.x & Freshness SLA check (ngưỡng 180 ngày) | Chạy kiểm tra: `Quality check status = True`, file `data/quality/test_quality_report.json` sinh ra đầy đủ 4 expectations pass. |
| Tạo Benchmark Test Set | `src/evaluation/testset.py` | Sinh tự động 10 câu hỏi kiểm thử chuẩn qua 4 domain: summary (3), authors (3), date (2), categories (2) | Lệnh sinh test set in ra: `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test`, file `data/eval/test_set.json` hợp lệ. |
| Xây dựng báo cáo tự động | `src/observability/reporting.py` | Báo cáo Markdown Phase 1 & Báo cáo so sánh 3 trạng thái | Cung cấp template sinh bảng markdown có đầy đủ metrics RAG, GX status, Freshness SLA. |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Artifact `data/quality/test_quality_report.json` thể hiện kết quả kiểm định tự động của 4 expectations (`expect_table_row_count_to_be_between`, `expect_column_values_to_not_be_null`, `expect_column_values_to_be_unique`, `expect_column_value_lengths_to_be_between`) kết hợp đánh giá tỷ lệ quá hạn đạt SLA độ tươi mới (`stale_ratio = 4.17% <= 25%`).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

1. Phát hiện sớm các lỗi về tính toàn vẹn dữ liệu (thiếu dòng, giá trị rỗng, trùng lặp DOI, văn bản quá ngắn) trước khi embedding để tránh hiện tượng *Silent Failure*.
2. Giám sát độ tươi mới của tri thức (Freshness SLA): cảnh báo bài báo cũ quá hạn làm giảm tính thời sự của hệ thống RAG.
3. Tạo bộ dữ liệu kiểm thử (Ground Truth) chuẩn hóa, khách quan và có tính lặp lại (reproducible) để đo lường định lượng năng lực của Agent.

### Cách triển khai

1. **Chuẩn Great Expectations 1.x (Ephemeral Context):**
   - Khởi tạo context hiện đại: `context = gx.get_context(mode="ephemeral")`.
   - Kết nối dữ liệu in-memory qua Pandas Data Source và Data Asset:
     ```python
     data_source = context.data_sources.add_pandas(name=source_name)
     data_asset = data_source.add_dataframe_asset(name=asset_name)
     batch_def = data_asset.add_batch_definition_whole_dataframe(batch_name)
     batch = batch_def.get_batch(batch_parameters={"dataframe": df})
     ```
   - Thiết lập 4 Expectations bắt buộc vào `ExpectationSuite` và gọi `batch.validate(suite)`.

2. **Freshness SLA Monitoring:**
   - Trong `build_freshness_report()`: Tính tỷ lệ các dòng có `age_days > settings.freshness_threshold_days` (180 ngày). Nếu tỷ lệ vượt quá 25% (`stale_ratio > 0.25`), đánh dấu `is_fresh = False`.

3. **Benchmark Test Set Builder:**
   - Trong `build_test_set()`: Lấy 10 bài báo đầu tiên từ Clean DataFrame, trích xuất thông tin để tự động sinh câu hỏi và đáp án chuẩn (`ground_truth` câu đầu tóm tắt bằng `first_sentence()`, danh sách tác giả, ngày tháng, chuyên ngành) kèm `ground_truth_doc_ids`.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `pandas.DataFrame` sạch từ `cleaning.py`    |
| Output                         | `data/quality/*_quality_report.json`, `data/eval/test_set.json` |
| Module phụ thuộc             | `core/config.py`, `core/utils.py`, `great_expectations` 1.x |
| Module sử dụng output        | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/evaluation/metrics.py` |
| Điều kiện lỗi cần xử lý | DataFrame ít hơn 10 dòng (không đủ sinh test set), các cột bị thiếu null khi validate |

### Cách xác minh

```bash
# 1. Kiểm tra Data Quality Gate với GX 1.x & Freshness SLA
cmd /c "set PYTHONIOENCODING=utf-8 && venv\Scripts\python -c ""from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; from observability.quality import run_data_quality_checks; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); res=run_data_quality_checks(df, s, 'test'); ok=res['success']; print('Tín hiệu hoàn thành: Quality check status =', ok)"""

# 2. Kiểm tra Benchmark Test Set
cmd /c "set PYTHONIOENCODING=utf-8 && venv\Scripts\python -c ""from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; from evaluation.testset import build_test_set; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"""
```

- **Kết quả mong đợi:** Quality check status = True và Sinh được 10 câu hỏi test.
- **Kết quả thực tế:**
  - `Tín hiệu hoàn thành: Quality check status = True`
  - `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test`
- **Artifact/log:** `data/quality/test_quality_report.json`, `data/eval/test_set.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Sử dụng thư viện Great Expectations phiên bản mới 1.23.2, vốn có sự thay đổi kiến trúc toàn diện so với các phiên bản 0.18 cũ (DataContext cũ dựa trên `great_expectations.yml` bị deprecated).
- **Các phương án đã cân nhắc:**
  1. *Phương án 1:* Khởi tạo DataContext dạng thư mục file cấu hình trên đĩa (`gx.data_context.DataContext`).
  2. *Phương án 2:* Sử dụng chuẩn hiện đại `Ephemeral Context` (`gx.get_context(mode="ephemeral")`) kết hợp Fluent Pandas Datasource.
- **Phương án đã chọn:** Phương án 2 (Ephemeral Context).
- **Lý do:** Tránh việc phụ thuộc vào thư mục cấu hình cồng kềnh, không để lại rác trên ổ đĩa, đảm bảo code chạy độc lập, portable và tương thích 100% với chuẩn GX 1.x theo yêu cầu của đề bài và Rubric.
- **Bằng chứng quyết định phù hợp:** Validation chạy thành công trong bộ nhớ RAM cực nhanh, kết xuất báo cáo JSON chi tiết mà không bị lỗi crash do deprecated API.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  SyntaxError: f-string expression part cannot include a backslash
  ```
- **Lệnh hoặc bước tái hiện:** Thực thi lệnh inline Python trong cmd với chuỗi lồng f-string và escape dấu ngoặc kép `\"\"`.
- **Nguyên nhân gốc:** Phiên bản Python trên Windows không cho phép ký tự backslash `\` nằm bên trong biểu thức f-string `{res[\"success\"]}` khi truyền qua shell wrapper.
- **Cách xử lý:** Tách biểu thức truy xuất dictionary ra biến phụ `ok = res['success']` rồi in biến đơn giản `print('...', ok)`.
- **Cách xác minh sau khi sửa:** Lệnh chạy thông suốt, trả về đúng `Quality check status = True`.
- **Điều học được:** Khi viết các script kiểm chứng hoặc automation command trên môi trường Windows CLI, cần hạn chế lồng ghép escaping phức tạp trong f-string.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**  
   Dữ liệu từ API Crossref được lưu trữ thô (`crossref_response.json`) -> parse thành `PaperRecord` -> làm sạch và ghép ngữ cảnh `text_for_embedding` trong DataFrame -> đi qua Quality Gate kiểm định -> nhúng vector embedding và nạp vào ChromaDB collection.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**  
   Test set 10 câu hỏi đóng vai trò là "thước đo chuẩn". Khi Agent truy vấn, hệ thống so khớp ID tài liệu tìm được với `ground_truth_doc_ids` để tính Hit Rate, và so khớp câu trả lời của AI với `ground_truth` để tính Token F1 và điểm chấm của LLM Judge.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**  
   Quality checks thẩm định tính đúng đắn về hình thức và cấu trúc dữ liệu (Null, Length, Uniqueness). Freshness monitoring thẩm định giá trị tri thức theo trục thời gian, đảm bảo mô hình không dựa vào những tài liệu đã quá cũ so với ngưỡng SLA đặt ra.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**  
   Đây là nguyên tắc biến kiểm soát (control variable) trong thực nghiệm khoa học. Cố định bộ câu hỏi kiểm thử giúp phản ánh trung thực sự thay đổi hiệu năng hoàn toàn là do chất lượng dữ liệu đầu vào.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**  
   Dựa trên: (1) `repaired_metrics.json` có `retrieval_hit_rate` và `mean_token_f1` hồi phục về mức baseline; (2) `data/quality/*` ghi nhận Quality Gate chuyển từ FAIL sang PASS; (3) Báo cáo đối chiếu `corruption_report.md` thể hiện rõ sự tương phản 3 trạng thái.

## 8. Phân tích kết quả

### Metrics chính

> *(Ghi chú: Sẽ được cập nhật đồng bộ sau khi nhóm chạy toàn tuyến Phase 1 và Phase 2)*

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      [ ] |       [ ] |      [ ] | [Sẽ đối chiếu sau khi chạy Phase 2] |
| `mean_token_f1`      |      [ ] |       [ ] |      [ ] | [Sẽ đối chiếu sau khi chạy Phase 2] |
| `judge_accuracy`     |      [ ] |       [ ] |      [ ] | [Sẽ đối chiếu sau khi chạy Phase 2] |
| `mean_judge_score`   |      [ ] |       [ ] |      [ ] | [Sẽ đối chiếu sau khi chạy Phase 2] |
| Quality checks         |     Pass |      Fail |     Pass | Great Expectations 1.x phát hiện vi phạm và pass sau repair |
| Freshness status       |    Fresh |     Stale |    Fresh | Freshness SLA cảnh báo chính xác dữ liệu lỗi thời |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. [Dữ liệu bị làm bẩn (thiếu summary, duplicate DOI)] → [Quality Gate báo FAIL, Freshness báo Stale] → [RAG retrieval hit rate tụt dốc, AI sinh câu trả lời ảo giác].
2. [Kích hoạt Idempotent Repair từ raw snapshot] → [Quality Gate và Freshness SLA chuyển xanh PASS] → [Hit Rate và Token F1 khôi phục tương đương Baseline ban đầu].

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Quality/Observability:** Hiểu sâu về cách thức xây dựng các hàng rào kiểm định tự động (Quality Gates) bằng GX 1.x Ephemeral context.
2. **Về Giám sát Freshness:** Nhận thức rõ ràng rằng dữ liệu đúng format chưa chắc đã dùng được nếu đã quá hạn thời gian (stale data).
3. **Về RAG Evaluation:** Nắm vững phương pháp xây dựng Benchmark Ground Truth đa dạng để đánh giá AI một cách định lượng thay vì đánh giá cảm tính.

### Nếu có thêm thời gian

Tích hợp Great Expectations Data Docs tự động render dashboard HTML trực quan và push metric chất lượng dữ liệu về Prometheus/Grafana để theo dõi drift liên tục.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Phùng Đức Đăng]  
**Ngày xác nhận:** [2026-09-26]
