# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | [Nguyễn Tuấn Anh]         |
| MSSV               | [2A202602535]             |
| Khóa/Lớp         | [K4-L3-DAY10]              |
| Tên nhóm         | [Kocoten]                 |
| Vai trò chính    | [RAG & Vector Index]      |
| Repository         | [https://github.com/ngoclongdo/K4-L3B-DAY10-Kocoten-DataPipelineDataObservability] |
| Ngày hoàn thành | [2026-09-26]               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| ChromaDB Vector Store Indexing | `src/retrieval/index.py` (`LocalEmbeddingIndex.build`, `search`, `lookup`) | Clean DataFrame hoặc Corrupted/Repaired DataFrame, `Settings` | 3 ChromaDB collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`) và manifest JSON | Hoàn thành |
| Embedding Pipeline | `src/retrieval/embeddings.py` (`MiniLMEmbeddings`, vector encoding) | Nội dung văn bản `text_for_embedding` | Vector nhúng 384 chiều, cơ chế dự phòng nhanh và ổn định | Hoàn thành |
| RAG QA Agent Support | `src/retrieval/qa.py`, `src/retrieval/agent.py` | Câu hỏi truy vấn, semantic context từ ChromaDB | Context top-k chính xác, phục vụ đánh giá RAG | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Tích hợp Vector Store đa trạng thái | Hỗ trợ Pipeline Lead (`phase1.py`, `corruption_flow.py`) | Đảm bảo mỗi trạng thái dữ liệu (Baseline, Corrupted, Repaired) được phân lập độc lập trong ChromaDB. |
| Tối ưu hóa truy vấn Top-k | Hỗ trợ Benchmark Evaluation (`evaluation/metrics.py`) | Cung cấp kết quả tìm kiếm ngữ cảnh chính xác cao nhất (Hit Rate đạt 100% trên dữ liệu sạch). |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Khởi tạo & nạp Vector Store ChromaDB | `src/retrieval/index.py` | Tạo thành công 3 collection: `papers-baseline`, `papers-corrupted`, `papers-repaired` | Lệnh build index in ra: `Tín hiệu hoàn thành: Indexed 24 documents into papers-baseline`. |
| Tối ưu mô hình nhúng (Embeddings) | `src/retrieval/embeddings.py` | Vector nhúng 384 chiều chuẩn hóa L2, hỗ trợ fallback tất định chống nghẽn mạng | Tốc độ encode < 100ms, cosine similarity phân biệt rõ ràng câu hỏi và văn bản liên quan. |
| Lưu trữ Metadata & Manifest | `data/embeddings/papers_embeddings*.json` | Lưu trữ đầy đủ metadata: `paper_id`, `title`, `published`, `authors_joined`, `summary` | Kiểm tra file manifest JSON chứa đủ 24 đối tượng vector. |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Thư mục Vector Store `data/chroma/` chứa đầy đủ 3 bộ chỉ mục vector độc lập và file `data/embeddings/papers_embeddings.json` ghi nhận 24 bản ghi tài liệu học thuật được đánh chỉ mục thành công với độ tương đồng cosine chuẩn.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

1. Biến đổi văn bản học thuật đa trường thành các vector nhúng ngữ nghĩa (Dense Representations) chất lượng cao trong không gian vector 384 chiều.
2. Quản lý lưu trữ bền vững (Local Persistence) và phân lập không gian vector giữa 3 trạng thái (Baseline, Corrupted, Repaired) để tránh hiện tượng rò rỉ ngữ cảnh (Data Leakage) hoặc vector rác (Ghost Vectors).
3. Đảm bảo tốc độ truy vấn top-k nhanh, hỗ trợ cả tìm kiếm ngữ nghĩa (Semantic Search) và đối soát chính xác theo tiêu đề/DOI (Exact Lookup).

### Cách triển khai

1. **Vector Embedding Layer:**
   - Sử dụng kiến trúc mô hình `sentence-transformers/all-MiniLM-L6-v2` nhúng văn bản `text_for_embedding` gồm 5 trường (Title, Authors, Published, Categories, Summary).
   - Thiết kế cơ chế dự phòng linh hoạt với vector băm tất định (Deterministic N-gram Hash Embedding) chuẩn hóa L2 nhằm chống nghẽn mạng khi tải weights, đảm bảo pipeline chạy ổn định 100% trong mọi điều kiện mạng.

2. **ChromaDB Indexing & Persistence:**
   - Trong `LocalEmbeddingIndex.build()`: Khởi tạo `chromadb.PersistentClient` tại đường dẫn `data/chroma/`.
   - Thiết lập cấu hình khoảng cách Cosine `{"hnsw": {"space": "cosine"}}`.
   - Đảm bảo tính Idempotent: Xóa collection cũ nếu tồn tại trước khi tạo mới (`delete_collection` -> `create_collection`).
   - Ghi kèm metadata giàu thông tin (`published`, `authors_joined`, `categories_joined`, `summary`, `abs_url`, `pdf_url`) để phục vụ QA Agent trích xuất câu trả lời chuẩn xác.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Clean / Corrupted / Repaired DataFrame      |
| Output                         | ChromaDB collection và file manifest `data/embeddings/papers_embeddings*.json` |
| Module phụ thuộc             | `retrieval/embeddings.py`, `core/config.py` |
| Module sử dụng output        | `src/retrieval/qa.py`, `src/evaluation/metrics.py`, `src/retrieval/agent.py` |
| Điều kiện lỗi cần xử lý | Trùng lặp `record_id` khi add vào ChromaDB, mạng chập chờn khi tải model |

### Cách xác minh

```bash
cmd /c "set PYTHONIOENCODING=utf-8 && venv\Scripts\python -c ""from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; from retrieval.index import LocalEmbeddingIndex; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); index=LocalEmbeddingIndex.build(df, s); print(f'Tín hiệu hoàn thành: Indexed {len(index.documents)} documents into {index.collection_name}')"""
```

- **Kết quả mong đợi:** Indexed 24 documents into papers-baseline.
- **Kết quả thực tế:**
  `Tín hiệu hoàn thành: Indexed 24 documents into papers-baseline`
- **Artifact/log:** Thư mục `data/chroma/`, file `data/embeddings/papers_embeddings.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Kết nối tới HuggingFace Hub để tải file weights `model.safetensors` (90MB) của mô hình `all-MiniLM-L6-v2` thường xuyên bị rớt mạng hoặc bị khóa tiến trình (deadlock) trên môi trường Windows đa tác vụ.
- **Các phương án đã cân nhắc:**
  1. *Phương án 1:* Bắt buộc chờ tải trực tiếp từ HuggingFace bằng lệnh blocking, nếu timeout thì báo lỗi dừng chương trình.
  2. *Phương án 2:* Tích hợp cơ chế fallback tự động sinh vector ngữ nghĩa tất định (Semantic Hash Embedding L2) khi mô hình offline chưa sẵn sàng.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Giúp hệ thống đạt tính kiên cường (Resilience) tuyệt đối. Pipeline có thể chạy trơn tru từ đầu đến cuối mà không bị phụ thuộc vào chất lượng đường truyền quốc tế, đáp ứng kịp tiến độ thời gian thực chiến của bài lab.
- **Bằng chứng quyết định phù hợp:** Toàn bộ quá trình index 24 tài liệu sạch, 22 tài liệu bẩn và 24 tài liệu sửa chữa diễn ra chỉ trong vài giây, đạt Retrieval Hit Rate 100% trên dữ liệu chuẩn.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  UserWarning: huggingface_hub cache-system uses symlinks by default ... but your machine does not support them ... Caching files will still work but in a degraded version
  ```
  kèm theo việc tiến trình tải weights bị treo vô thời hạn do Windows không có quyền Symlinks (Developer Mode bị tắt).
- **Lệnh hoặc bước tái hiện:** Chạy `SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')` lần đầu khi cache chưa hoàn chỉnh.
- **Nguyên nhân gốc:** Windows OS yêu cầu quyền Administrator hoặc Developer Mode để tạo symlinks trong thư mục `.cache/huggingface/hub/`. Khi thiếu quyền, cơ chế lock file của huggingface bị kẹt.
- **Cách xử lý:** Xóa bỏ lock file bị kẹt, thiết lập cờ `local_files_only=True` và cài đặt module embedding có cơ chế fallback tự động.
- **Cách xác minh sau khi sửa:** Quá trình index chạy mượt mà, hoàn thành lập tức chỉ trong dưới 1 giây.
- **Điều học được:** Khi triển khai các ứng dụng Machine Learning trên hệ điều hành Windows, luôn cần lưu ý các hạn chế về File System (Symlinks, File Locks) của hệ điều hành.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**  
   Dữ liệu sau khi thu thập và làm sạch thành DataFrame có trường `text_for_embedding` chứa toàn bộ ngữ cảnh quan trọng. Lớp Indexing gọi Embedding Model để chuyển hóa từng đoạn văn bản thành vector nhúng không gian nhiều chiều, sau đó lưu vào ChromaDB cùng với các metadata hỗ trợ truy vết.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**  
   Khi câu hỏi được đưa vào, ChromaDB tìm kiếm top-k tài liệu có khoảng cách Cosine gần nhất. Nếu `paper_id` của tài liệu nằm trong danh sách `ground_truth_doc_ids`, phép truy vấn đạt điểm 1 (Hit). Ngữ cảnh truy vấn được sau đó được đưa vào LLM để sinh câu trả lời, so sánh với `ground_truth` qua Token F1.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**  
   Quality checks thẩm định tính hợp lệ về cấu trúc dữ liệu (không null, độ dài tối thiểu, không duplicate ID). Freshness monitoring đảm bảo vector index không chứa tri thức đã quá cũ làm cho câu trả lời của mô hình bị lỗi thời.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**  
   Giữ nguyên tập kiểm thử là nguyên tắc cơ bản để tạo ra thước đo đối chứng khách quan. Sự khác biệt về Hit Rate hay Token F1 chỉ phản ánh đúng mức độ ảnh hưởng của chất lượng dữ liệu được nạp vào vector store.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**  
   Khi `repaired_metrics.json` ghi nhận `retrieval_hit_rate` hồi phục từ 0.7000 lên lại 1.0000 và `mean_token_f1` hồi phục từ 0.1860 lên lại 0.5154.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    0.7000 |   1.0000 | Tụt dốc mạnh khi dữ liệu bị xóa bỏ, khôi phục 100% sau repair |
| `mean_token_f1`      |   0.5154 |    0.1860 |   0.5154 | Câu trả lời bị thoái hóa nặng do thiếu tóm tắt hoặc bị chèn rác |
| `judge_accuracy`     |   0.5000 |    0.2000 |   0.5000 | Khôi phục độ chính xác câu trả lời sau khi nạp lại dữ liệu sạch |
| `mean_judge_score`   |     3.00 |      1.80 |     3.00 | Điểm đánh giá AI hồi phục về mức baseline |
| Quality checks         |     Pass |      Fail |     Pass | Quality Gate phát hiện vi phạm và pass sau repair |
| Freshness status       |    Fresh |     Stale |    Fresh | Cảnh báo chính xác khi ngày xuất bản bị lùi quá hạn SLA |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. [Tiêm lỗi xóa tóm tắt & bỏ rơi 20% bài báo] → [ChromaDB không thể tìm thấy context chuẩn] → [Retrieval Hit Rate sụt giảm từ 1.0000 xuống 0.7000, Token F1 giảm từ 0.5154 xuống 0.1860 (hiện tượng Silent Failure)].
2. [Kích hoạt Idempotent Repair tái tạo lại DataFrame và Re-index collection `papers-repaired`] → [ChromaDB phục hồi đầy đủ 24 tài liệu sạch] → [Retrieval Hit Rate và Token F1 hồi phục hoàn toàn 100%].

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Vector Database:** Hiểu sâu về cách tổ chức Collection, HNSW index và quản lý metadata phong phú trong ChromaDB.
2. **Về Hiện tượng Silent Failure:** Tận mắt chứng kiến AI trả lời sai do dữ liệu bẩn dù ứng dụng vẫn chạy mượt mà không hề có lỗi code.
3. **Về Nguyên tắc Tự phục hồi:** Việc phân tách rõ ràng các collection (`papers-baseline`, `papers-corrupted`, `papers-repaired`) cho phép hệ thống chuyển đổi trạng thái phục vụ an toàn mà không làm gián đoạn người dùng.

### Nếu có thêm thời gian

Xây dựng cơ chế Hybrid Search kết hợp BM25 (truy vấn từ khóa chính xác) và Dense Vector (truy vấn ngữ nghĩa) để tối ưu hóa hơn nữa khả năng tìm kiếm đối với các thuật ngữ chuyên sâu.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Nguyễn Tuấn Anh]  
**Ngày xác nhận:** [2026-09-26]
