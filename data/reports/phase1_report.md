# Báo Cáo Pha 1: Baseline Data Pipeline & Observability

- **Thời điểm sinh báo cáo:** 2026-09-26T04:27:21.439005+00:00
- **Nguồn dữ liệu:** Crossref REST API
- **Tổng số tài liệu ingest:** 24
- **Số tài liệu sau khi làm sạch:** 24

---

## 1. Kết Quả Kiểm Định Chất Lượng (Data Quality Gate - Great Expectations 1.x)

- **Trạng thái Quality Gate:** `PASS (Thành công)`
- **Số lượng bản ghi kiểm định:** 24

### Chi tiết các Expectations:
| STT | Expectation | Chi tiết kiểm tra | Trạng thái |
|:---:|:---|:---|:---:|
| 1 | `expect_table_row_count_to_be_between` | `{'batch_id': 'papers_source_baseline-papers_asset_baseline', 'min_value': 5, 'max_value': 5000}` | **PASS** |
| 2 | `expect_column_values_to_not_be_null` | `{'batch_id': 'papers_source_baseline-papers_asset_baseline', 'column': 'paper_id'}` | **PASS** |
| 3 | `expect_column_values_to_be_unique` | `{'batch_id': 'papers_source_baseline-papers_asset_baseline', 'column': 'paper_id'}` | **PASS** |
| 4 | `expect_column_values_to_not_be_null` | `{'batch_id': 'papers_source_baseline-papers_asset_baseline', 'column': 'title'}` | **PASS** |
| 5 | `expect_column_values_to_not_be_null` | `{'batch_id': 'papers_source_baseline-papers_asset_baseline', 'column': 'text_for_embedding'}` | **PASS** |
| 6 | `expect_column_value_lengths_to_be_between` | `{'batch_id': 'papers_source_baseline-papers_asset_baseline', 'column': 'summary', 'min_value': 30}` | **PASS** |

---

## 2. Giám Sát Độ Tươi Mới Dữ Liệu (Freshness SLA)

- **Ngưỡng SLA (Threshold):** 180 ngày
- **Bài báo mới nhất:** 2026-07-22
- **Bài báo cũ nhất:** 2026-03-28
- **Số dòng quá hạn (Stale rows):** 1 / 24 (4.2%)
- **Trạng thái Freshness SLA:** `FRESH (Đạt SLA)`

---

## 3. Chỉ Số Hiệu Năng RAG Ban Đầu (Baseline Metrics)

| Chỉ số đánh giá | Giá trị Baseline | Ý nghĩa |
|:---|:---:|:---|
| **Retrieval Hit Rate** | `1.0000` | Tỷ lệ tài liệu chuẩn (Ground Truth) được truy vấn chính xác trong top-k |
| **Mean Token F1** | `0.5154` | Độ tương đồng từ khóa giữa câu trả lời AI và Ground Truth |
| **Judge Accuracy** | `0.5000` | Tỷ lệ câu trả lời được LLM/Heuristic Judge chấm là đúng |
| **Mean Judge Score** | `3.00 / 5.0` | Điểm trung bình chất lượng câu trả lời |

---
*Báo cáo được khởi tạo tự động bởi hệ thống Data Observability Pipeline.*
