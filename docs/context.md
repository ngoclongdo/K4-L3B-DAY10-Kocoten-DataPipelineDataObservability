# Hướng Dẫn Thực Hành Pipeline & Data Observability

---

## Bước 2: Thu Thập Metadata & Bảo Tồn Dữ Liệu Thô (Raw Preservation)

Trong bước này, chúng ta thu thập metadata bài báo học thuật từ Crossref REST API và cất giữ bản sao nguyên gốc (*Raw Preservation*).

### Mục tiêu

- Thu thập metadata từ Crossref REST API công khai.
- Chuẩn hóa các trường thông tin: `paper_id` (DOI), `title`, `summary` (loại bỏ các thẻ HTML/XML rác như `<jats:p>`), `authors`, `categories`, `published`.
- Lưu lại 2 file dữ liệu thô (*Raw Artifacts*) phục vụ Data Lineage:
  - `data/raw/crossref_response.json`: Toàn bộ JSON gốc từ API (nguyên bản, không chỉnh sửa).
  - `data/raw/crossref_records.json`: Danh sách đối tượng `PaperRecord` sau khi bóc tách.

> [!NOTE]
> **Tại sao phải cất giữ bản thô (Raw Preservation)?**  
> Dữ liệu gốc cào về cần được giữ nguyên vẹn để làm điểm tựa phục hồi (*Lineage Anchor*). Khi các bước biến đổi dữ liệu phía sau xảy ra lỗi, hệ thống có thể chạy lại từ bản thô mà không cần gọi lại API ngoài, tránh nguy cơ bị giới hạn truy cập (*Rate Limit*).

> [!TIP]
> **Cơ chế Cứu hộ Offline (Fallback):**  
> Nếu mạng chập chờn hoặc API Crossref trả về lỗi `429 Too Many Requests`, pipeline sẽ tự động chuyển sang đọc file snapshot mẫu có sẵn tại `data/raw/crossref_response.json` mà không làm gián đoạn bài lab.

### 🎯 Nhiệm vụ của bạn

Mở file [`src/ingestion/crossref.py`](file:///d:/VinUni/day10/K4-L3B-DAY10-Kocoten-DataPipelineDataObservability/src/ingestion/crossref.py), đọc docstring và hoàn thiện logic 2 hàm:
1. `parse_crossref_payload(payload)`: Bóc tách cấu trúc payload JSON từ API Crossref thành danh sách các đối tượng `PaperRecord`.
2. `fetch_source_records(settings)`: Gọi API Crossref (hoặc kích hoạt fallback đọc snapshot mẫu), lưu JSON gốc vào `data/raw/crossref_response.json` và lưu danh sách records vào `data/raw/crossref_records.json`.

### Kiểm tra bước 2

Chạy lệnh kiểm tra sau trong terminal:

```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
```

**Tín hiệu hoàn thành:** Console in ra:
```text
Tín hiệu hoàn thành: Đã tải 24 bài báo
```

---

## Bước 3: Làm Sạch Dữ Liệu & Chuẩn Bị Văn Bản Tạo Vector (`src/ingestion/cleaning.py`)

Dữ liệu thô tải về cần được chuẩn hóa khoảng trắng, định dạng ngày tháng và định dạng văn bản phục vụ Embedding.

### Mục tiêu

- Loại bỏ khoảng trắng thừa, chuẩn hóa định dạng văn bản.
- Tính toán tuổi đời dữ liệu: `age_days = (run_date - published).days`.
- Khử trùng lặp bản ghi theo khóa duy nhất `paper_id`.
- Ghép nối các trường thành một đoạn ngữ cảnh hoàn chỉnh `text_for_embedding`:

```text
Title: <Tiêu đề bài báo>
Authors: <Danh sách tác giả>
Published: <Ngày xuất bản>
Categories: <Lĩnh vực chuyên môn>
Summary: <Tóm tắt nội dung>
```

### 🎯 Nhiệm vụ của bạn

Mở file [`src/ingestion/cleaning.py`](file:///d:/VinUni/day10/K4-L3B-DAY10-Kocoten-DataPipelineDataObservability/src/ingestion/cleaning.py), hoàn thiện hàm `build_clean_dataframe(raw_records, run_date)` để:
- Biến đổi danh sách `PaperRecord` thành một `pandas.DataFrame` sạch.
- Tính toán cột `age_days`.
- Tạo cột tổng hợp `text_for_embedding`.
- Loại bỏ hoàn toàn các dòng trùng lặp `paper_id`.

### Kiểm tra bước 3

Chạy lệnh kiểm tra sau trong terminal:

```bash
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
```

**Tín hiệu hoàn thành:** Console in ra:
```text
Tín hiệu hoàn thành: Clean thành công 24 dòng
```

---

## Bước 4: Thiết Lập Chốt Kiểm Soát Dữ Liệu (Observability Gate) với Great Expectations 1.x (`src/observability/quality.py`)

Trước khi đưa dữ liệu vào Vector Database, dữ liệu phải vượt qua chốt kiểm định chất lượng nghiêm ngặt.

### Chuẩn Great Expectations 1.x

Sử dụng chuẩn Ephemeral Context hiện đại trên GX 1.x:

```python
context = gx.get_context(mode="ephemeral")
data_source = context.data_sources.add_pandas(name="papers_source")
data_asset = data_source.add_dataframe_asset(name="papers_asset")
batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
batch = batch_def.get_batch(batch_parameters={"dataframe": df})
```

### 4 Hàng Rào Kiểm Định (Expectations) Bắt Buộc

1. **`ExpectTableRowCountToBeBetween`**: Số lượng bản ghi nằm trong ngưỡng 5 đến 5000 dòng.
2. **`ExpectColumnValuesToNotBeNull`**: Các cột quan trọng `paper_id`, `title`, `text_for_embedding` không được rỗng (null).
3. **`ExpectColumnValuesToBeUnique`**: Mỗi bài báo `paper_id` là duy nhất, không trùng lặp.
4. **`ExpectColumnValueLengthsToBeBetween`**: Trường `summary` có độ dài tối thiểu 30 ký tự.

### Giám Sát Độ Tươi Mới (Freshness Monitoring)

Đo lường tỉ lệ bài báo cũ (`age_days > 180` ngày). Nếu tỉ lệ bài báo cũ vượt quá 25%, hệ thống lập tức gắn cờ cảnh báo `is_fresh = False`.

### 🎯 Nhiệm vụ của bạn

Mở file [`src/observability/quality.py`](file:///d:/VinUni/day10/K4-L3B-DAY10-Kocoten-DataPipelineDataObservability/src/observability/quality.py), hoàn thiện hàm `run_data_quality_checks(df, settings, stage)` sử dụng Great Expectations 1.x Ephemeral Context để:
- Thiết lập và kiểm định 4 Expectations bắt buộc trên.
- Kết hợp gọi hàm `evaluate_freshness_sla()` để kiểm tra độ tươi mới của dữ liệu.
- Trả về dict kết quả chứa `{"success": bool, ...}`.

### Kiểm tra bước 4

Chạy lệnh kiểm tra sau trong terminal:

```bash
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print('Tín hiệu hoàn thành: Quality check status =', res['success'])"
```

**Tín hiệu hoàn thành:** Console in ra:
```text
Tín hiệu hoàn thành: Quality check status = True
```

---

## Bước 5: Tạo Bộ Đề Đánh Giá Chuẩn (Benchmark Test Set) (`src/evaluation/testset.py`)

Để đánh giá chất lượng câu trả lời của AI, chúng ta xây dựng bộ dữ liệu kiểm thử (Ground Truth) gồm 10 câu hỏi thuộc 4 dạng bài toán:

1. `summary`: Hỏi tóm tắt nội dung chính của bài báo.
2. `authors`: Hỏi về tác giả công trình nghiên cứu.
3. `date`: Hỏi thời điểm xuất bản.
4. `categories`: Hỏi về lĩnh vực chuyên môn.

Mỗi câu hỏi trong `test_set.json` có định dạng:

```json
{
  "id": "eval_001",
  "question_type": "summary",
  "question": "What is the summary of the paper '<Title>'?",
  "ground_truth": "<Nội dung câu đầu tóm tắt chuẩn>",
  "ground_truth_doc_ids": ["<DOI bài báo>"]
}
```

### 🎯 Nhiệm vụ của bạn

Mở file [`src/evaluation/testset.py`](file:///d:/VinUni/day10/K4-L3B-DAY10-Kocoten-DataPipelineDataObservability/src/evaluation/testset.py), hoàn thiện hàm `build_test_set(df, output_path)` để:
- Tự động trích xuất từ DataFrame dữ liệu sạch 10 câu hỏi Ground Truth phân bổ đều qua 4 dạng bài toán trên.
- Lưu thành file `data/eval/test_set.json`.

### Kiểm tra bước 5

Chạy lệnh kiểm tra sau trong terminal:

```bash
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
```

**Tín hiệu hoàn thành:** Console in ra:
```text
Tín hiệu hoàn thành: Sinh được 10 câu hỏi test
```

---

## Bước 6: Chạy Toàn Tuyến Dữ Liệu Sạch (Baseline Pipeline) (`script/run_phase1.py`)

### 🎯 Nhiệm vụ của bạn

Mở file [`src/pipelines/phase1.py`](file:///d:/VinUni/day10/K4-L3B-DAY10-Kocoten-DataPipelineDataObservability/src/pipelines/phase1.py), hoàn thiện hàm `run_phase1_pipeline(settings)` để xâu chuỗi 6 bước pipeline hoàn chỉnh:
$$\text{Ingest} \longrightarrow \text{Clean} \longrightarrow \text{Index ChromaDB} \longrightarrow \text{Sinh Testset} \longrightarrow \text{Đánh giá Baseline RAG Hit Rate \& Token F1} \longrightarrow \text{Great Expectations Quality Gate}$$
và xuất báo cáo `data/reports/phase1_report.md`.

Sau đó, thực thi script chạy toàn tuyến Phase 1:

```bash
python script/run_phase1.py
```

**Tín hiệu hoàn thành:**
- File `data/clean/papers_clean.csv` xuất hiện đầy đủ các dòng sạch.
- File `data/results/baseline_metrics.json` ghi nhận các chỉ số ban đầu (Hit Rate và Token F1).
- File `data/reports/phase1_report.md` được sinh ra với bảng số liệu chi tiết.

---

## Bước 7: Tiêm Lỗi Dữ Liệu Thực Nghiệm (Data Corruption Suite)

Tại [`src/ingestion/corruption.py`](file:///d:/VinUni/day10/K4-L3B-DAY10-Kocoten-DataPipelineDataObservability/src/ingestion/corruption.py), chúng ta giả lập 6 dạng sự cố dữ liệu thực tế:

1. **Drop latest records**: Bỏ rơi 20% các bài báo mới nhất.
2. **Blank summary**: Xóa trắng phần tóm tắt ở một số dòng.
3. **Inject noise**: Chèn các chuỗi ký tự rác vào tóm tắt.
4. **Truncate title**: Cắt ngắn tiêu đề xuống dưới 8 ký tự.
5. **Stale date**: Lùi ngày xuất bản về 365 ngày trước.
6. **Duplicate rows**: Nhân đôi các dòng để tạo trùng lặp.

### 🎯 Nhiệm vụ của bạn

Mở file [`src/ingestion/corruption.py`](file:///d:/VinUni/day10/K4-L3B-DAY10-Kocoten-DataPipelineDataObservability/src/ingestion/corruption.py), hoàn thiện hàm `corrupt_clean_dataframe(clean_df, log_path)` để tiêm 6 dạng lỗi trên vào dữ liệu sạch và ghi lại nhật ký toàn bộ các dòng bị biến đổi vào `data/results/corruption_log.json`.

### Kiểm tra bước 7

Chạy lệnh kiểm tra sau trong terminal:

```bash
python -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); c=corrupt_clean_dataframe(df, s.paths.corruption_log); print(f'Tín hiệu hoàn thành: Corrupted {len(c)} dòng')"
```

**Tín hiệu hoàn thành:**
- Nhật ký lỗi `data/results/corruption_log.json` được ghi lại chi tiết.

---

## Bước 8: Đo Lường Suy Giảm, Phục Hồi Dữ Liệu & Đối Chiếu 3 Trạng Thái

### 🎯 Nhiệm vụ của bạn

Mở file [`src/pipelines/corruption_flow.py`](file:///d:/VinUni/day10/K4-L3B-DAY10-Kocoten-DataPipelineDataObservability/src/pipelines/corruption_flow.py), hoàn thiện hàm `run_corruption_flow_pipeline(settings)` để:
1. Nạp dữ liệu bẩn vào ChromaDB và đo lường sự suy giảm hiệu năng của AI (quan sát hiện tượng *Silent Failure*).
2. Kích hoạt hàm phục hồi an toàn `repair_from_raw_snapshot()` từ snapshot thô ban đầu để ghi đè dữ liệu hỏng.
3. Tái đánh giá hệ thống và kết xuất bảng so sánh 3 trạng thái tại `data/reports/corruption_report.md`.

Sau đó, thực thi script chạy toàn tuyến Phase 2:

```bash
python script/run_corruption_flow.py
```

**Tín hiệu hoàn thành:**
- Console in ra bảng so sánh hiệu năng 3 cột rõ ràng (*Baseline* vs *Corrupted* vs *Repaired*).
- Báo cáo `data/reports/corruption_report.md` được tạo thành công, thể hiện rõ mức độ phục hồi hiệu năng của hệ thống.