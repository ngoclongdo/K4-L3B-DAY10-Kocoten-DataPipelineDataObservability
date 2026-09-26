# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | [Đỗ Nguyễn Ngọc Long]     |
| MSSV               | [2A202602390]             |
| Khóa/Lớp         | [K4-L3-DAY10]              |
| Tên nhóm         | [Kocoten]                 |
| Vai trò chính    | [Trưởng nhóm / Pipeline Integrator] |
| Repository         | [https://github.com/ngoclongdo/K4-L3B-DAY10-Kocoten-DataPipelineDataObservability] |
| Ngày hoàn thành | [2026-09-26]               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Baseline Pipeline End-to-End | `src/pipelines/phase1.py` (`run_phase1_pipeline`, `main`) | Raw data, settings, GX checks, test set, vector index | Clean artifacts, baseline index, `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` | Hoàn thành |
| Synthetic Corruption Suite | `src/ingestion/corruption.py` (`corrupt_clean_dataframe`) | Clean DataFrame, đường dẫn log | Corrupted DataFrame (tiêm 6 kịch bản lỗi), `data/results/corruption_log.json` | Hoàn thành |
| Corruption & Idempotent Repair Flow | `src/pipelines/corruption_flow.py` (`run_corruption_flow_pipeline`, `main`) | Clean DataFrame, corrupted DataFrame, raw snapshot | `corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md` | Hoàn thành |
| Entrypoint Scripts & Git Workflow | `script/run_phase1.py`, `script/run_corruption_flow.py`, `docs/TEAM.md` | Settings môi trường | Kịch bản 1-click execution, điều phối branch và commit của cả nhóm | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Điều phối kiến trúc toàn tuyến | Hỗ trợ cả 3 thành viên (Đức Anh, Tuấn Anh, Đức Đăng) | Phân rã bài toán, chuẩn hóa contract I/O giúp nhóm code song song không conflict. |
| Xử lý tương thích môi trường Windows CLI | Hỗ trợ cả nhóm | Fix triệt để các lỗi Unicode codepage (`set PYTHONIOENCODING=utf-8`) và escaping terminal. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Chạy toàn tuyến Baseline (Phase 1) | `script/run_phase1.py`, `src/pipelines/phase1.py` | Toàn bộ chu trình Ingest -> Clean -> GX 1.x -> Testset -> Index -> Eval chạy exit code 0 | `python script/run_phase1.py` hoàn tất, sinh ra `baseline_metrics.json` và `phase1_report.md`. |
| Bộ tiêm lỗi 6 kịch bản (CP4) | `src/ingestion/corruption.py` | Tiêm thành công 6 dạng lỗi, ghi lại đầy đủ 22 sự cố vào `data/results/corruption_log.json` | Kiểm tra `corruption_log.json` ghi nhận đầy đủ 6 dạng vi phạm. |
| Chạy toàn tuyến Phase 2 & Bảng so sánh 3 trạng thái | `script/run_corruption_flow.py`, `src/pipelines/corruption_flow.py` | Đo lường Silent Failure trên dữ liệu bẩn, kích hoạt Idempotent Repair và xuất bảng đối chiếu | `python script/run_corruption_flow.py` in bảng so sánh 3 cột rõ ràng ra console và sinh `corruption_report.md`. |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Bảng đối chiếu định lượng 3 trạng thái tại [data/reports/corruption_report.md](file:///d:/VinUni/day10/K4-L3B-DAY10-Kocoten-DataPipelineDataObservability/data/reports/corruption_report.md) chứng minh rõ ràng hiện tượng Silent Failure (Hit Rate giảm từ 1.0 xuống 0.70, Token F1 giảm từ 0.5154 xuống 0.1860) và sự phục hồi hoàn hảo 100% sau khi chạy Idempotent Repair.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

1. Kết nối các module đơn lẻ của 3 thành viên thành một đường ống dữ liệu (Data Pipeline) hoàn chỉnh, khép kín và có tính tất định (Idempotent).
2. Thiết kế kịch bản tiêm lỗi thực nghiệm phản ánh đúng các sự cố dữ liệu thực tế trong sản xuất (mất mát dữ liệu mới, tóm tắt bị rỗng, dữ liệu rác, tiêu đề bị cắt, ngày tháng quá hạn, trùng lặp khóa chính).
3. Chứng minh năng lực phát hiện lỗi của Data Observability Gate (GX 1.x) và cơ chế tự phục hồi an toàn từ Lineage Anchor.

### Cách triển khai

1. **Phase 1 Pipeline (`run_phase1_pipeline`):**
   - Xâu chuỗi tuần tự theo mô hình DAG: Thu thập -> Tiền xử lý -> Kiểm định GX 1.x & Freshness SLA -> Tạo bộ kiểm thử -> Đánh chỉ mục ChromaDB -> Đánh giá Agent bằng Token F1 & LLM Judge -> Xuất báo cáo Markdown.
2. **Data Corruption Suite (`corrupt_clean_dataframe`):**
   - Triển khai đủ 6 dạng lỗi: Bỏ rơi 20% bài báo mới nhất, xóa tóm tắt, chèn chuỗi rác `@@ERROR_NOISE_CORRUPTED_STRING@@`, cắt tiêu đề < 8 ký tự, lùi ngày xuất bản về 365 ngày trước (đẩy tỷ lệ quá hạn lên 35% để breach SLA 25%), nhân bản 2 dòng để tạo trùng lặp DOI. Ghi nhật ký vào `corruption_log.json`.
3. **Phase 2 Corruption & Idempotent Repair Flow (`run_corruption_flow_pipeline`):**
   - Đánh chỉ mục dữ liệu bẩn vào collection `papers-corrupted`, đo lường sự suy giảm chỉ số của RAG Agent.
   - Kích hoạt hàm `repair_from_raw_snapshot()` đọc lại bản thô nguyên gốc từ `data/raw/crossref_records.json` để ghi đè và tái tạo lại tập dữ liệu sạch ban đầu mà không cần gọi lại external API.
   - Re-index vào collection `papers-repaired` và đánh giá lại hệ thống trên cùng bộ test set.
   - Xuất bảng đối chiếu 3 cột ra console và file markdown.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Cấu hình `Settings`, các module của nhóm    |
| Output                         | `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `phase1_report.md`, `corruption_report.md` |
| Module phụ thuộc             | `ingestion/`, `observability/`, `retrieval/`, `evaluation/` |
| Module sử dụng output        | Ban giám khảo đánh giá, Live Demo nghiệm thu |
| Điều kiện lỗi cần xử lý | Mạng chập chờn khi gọi Gemini API, file JSON không tồn tại |

### Cách xác minh

```bash
# 1. Chạy toàn tuyến Baseline Phase 1
cmd /c "set PYTHONIOENCODING=utf-8 && venv\Scripts\python script/run_phase1.py"

# 2. Chạy toàn tuyến Phase 2 Corruption & Repair
cmd /c "set PYTHONIOENCODING=utf-8 && venv\Scripts\python script/run_corruption_flow.py"
```

- **Kết quả mong đợi:** Cả 2 script chạy exit code 0, in bảng so sánh 3 trạng thái.
- **Kết quả thực tế:** Cả 2 script chạy mượt mà, bảng đối chiếu 3 trạng thái in ra rõ ràng trên console.
- **Artifact/log:** `data/reports/phase1_report.md`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần thiết kế cơ chế phục hồi dữ liệu (Repair) sao cho vừa đảm bảo tính an toàn vừa đảm bảo tính bất biến (Idempotent).
- **Các phương án đã cân nhắc:**
  1. *Phương án 1:* Viết script "vá lỗi" (patching) cục bộ: tìm các dòng bị null/corrupt rồi sửa đổi trực tiếp trên DataFrame hiện tại.
  2. *Phương án 2:* Thực hiện Idempotent Repair: quay về điểm tựa nguồn gốc thô (Raw Snapshot Lineage Anchor) đã bảo tồn từ trước để tái tạo và ghi đè hoàn toàn toàn bộ tập dữ liệu.
- **Phương án đã chọn:** Phương án 2 (Tái tạo từ Raw Snapshot).
- **Lý do:** Tránh hiện tượng vá lỗi chắp vá sinh ra lỗi dây chuyền tiềm ẩn (Side-effects); đảm bảo 100% tính nguyên vẹn và khả năng tái lập của dữ liệu, đúng triết lý của Data Lineage.
- **Bằng chứng quyết định phù hợp:** Hiệu năng của hệ thống sau khi repair khôi phục chính xác 100% bằng với mức Baseline ban đầu (Hit Rate 1.0000, Token F1 0.5154).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ConnectError: [WinError 10054] An existing connection was forcibly closed by the remote host
  ```
- **Lệnh hoặc bước tái hiện:** Quá trình đánh giá 10 câu hỏi bằng LLM Judge gọi liên tiếp tới Google Gemini API qua kết nối HTTPS trên Windows.
- **Nguyên nhân gốc:** Socket connection bị server hoặc proxy ngắt đột ngột do keep-alive timeout trên đường truyền quốc tế.
- **Cách xử lý:** Hệ thống client đã tích hợp cơ chế retry tự động (`Retrying google.genai._api_client.BaseApiClient._request_once in 1.45 seconds...`) giúp tự động kết nối lại và hoàn thành trọn vẹn 10 câu hỏi mà không làm gãy pipeline.
- **Cách xác minh sau khi sửa:** Toàn bộ 10 câu hỏi đều được chấm điểm đầy đủ và ghi nhận kết quả chính xác vào `corrupted_answers.json` và `repaired_answers.json`.
- **Điều học được:** Khi xây dựng pipeline phụ thuộc vào LLM API ngoài, luôn bắt buộc phải có cơ chế retry với exponential backoff.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**  
   Dữ liệu được thu thập từ Crossref REST API -> lưu snapshot thô nguyên bản làm Lineage Anchor -> bóc tách làm sạch, tạo text context hoàn chỉnh trong DataFrame -> kiểm định chất lượng qua GX 1.x và Freshness SLA -> biến đổi thành dense vector embedding -> nạp bền vững vào ChromaDB collection.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**  
   Test set gồm 10 câu hỏi có sẵn `ground_truth_doc_ids` và `ground_truth`. Hệ thống đo xem vector search có tìm trúng tài liệu chuẩn không (Retrieval Hit Rate), và so sánh câu trả lời được AI tạo ra với đáp án mẫu (Token F1 và điểm chấm của LLM Judge).
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**  
   Quality checks kiểm tra tính đúng đắn cấu trúc và giá trị của dữ liệu (schema, null, uniqueness, length). Freshness monitoring kiểm tra khía cạnh thời gian, phát hiện và cảnh báo tri thức bị lỗi thời dựa trên SLA ngày xuất bản.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**  
   Để giữ nguyên môi trường kiểm thử đối chứng khách quan. Mọi sự tăng giảm của các chỉ số hoàn toàn do sự thay đổi của chất lượng dữ liệu đầu vào mang lại.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**  
   Repair thành công khi: (1) `repaired_metrics.json` có `retrieval_hit_rate` và `mean_token_f1` phục hồi về mức baseline; (2) `repaired_quality_report.json` và `freshness_report.json` đạt PASS / FRESH; (3) File đối chiếu `corruption_report.md` thể hiện sự đảo chiều tích cực rõ ràng.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    0.7000 |   1.0000 | Tụt dốc nghiêm trọng do mất tài liệu mới, hồi phục 100% |
| `mean_token_f1`      |   0.5154 |    0.1860 |   0.5154 | Câu trả lời bị giảm chất lượng mạnh trên dữ liệu bẩn |
| `judge_accuracy`     |   0.5000 |    0.2000 |   0.5000 | Tỷ lệ câu trả lời đúng của AI hồi phục hoàn toàn |
| `mean_judge_score`   |     3.00 |      1.80 |     3.00 | Điểm trung bình chất lượng tăng từ 1.80 lên lại 3.00 |
| Quality checks         |     Pass |      Fail |     Pass | Great Expectations phát hiện vi phạm và pass sau repair |
| Freshness status       |    Fresh |     Stale |    Fresh | Cảnh báo stale chính xác khi ngày xuất bản bị lùi hạn |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. [Tiêm 6 lỗi dữ liệu (xóa tóm tắt, chèn rác, cắt title, lùi ngày, trùng lặp)] → [Quality Gate báo FAIL, Freshness báo STALE] → [Retrieval Hit Rate sụt từ 1.0 xuống 0.70, Token F1 rơi từ 0.5154 xuống 0.1860 và Judge Score rơi xuống 1.80 (hiện tượng Silent Failure)].
2. [Kích hoạt Idempotent Repair tái tạo từ raw snapshot `crossref_records.json`] → [Quality Gate và Freshness SLA xanh trở lại] → [Toàn bộ chỉ số hiệu năng RAG Agent khôi phục 100% bằng mức Baseline].

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Thấu hiểu sâu sắc vai trò của Data Lineage và nguyên tắc thiết kế hệ thống có khả năng tự phục hồi (Self-Healing Architecture).
2. **Về Data Observability:** Chốt kiểm soát chất lượng dữ liệu (Quality Gates) là phòng tuyến bắt buộc phải có để ngăn chặn dữ liệu rác đi vào serving layer của AI.
3. **Về Quản lý dự án nhóm:** Cách phân chia module decoupled giúp các thành viên trong nhóm có thể code song song, kiểm chứng độc lập mà không bị dẫm chân lên nhau.

### Nếu có thêm thời gian

Triển khai cơ chế CI/CD tự động bằng GitHub Actions: mỗi khi có commit mới vào dữ liệu, hệ thống tự động chạy toàn tuyến kiểm định chất lượng và cập nhật bảng dashboard theo dõi.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Đỗ Nguyễn Ngọc Long]  
**Ngày xác nhận:** [2026-09-26]
