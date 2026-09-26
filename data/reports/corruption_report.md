# Báo Cáo Đối Chiếu 3 Trạng Thái: Baseline vs Corrupted vs Repaired

> Báo cáo định lượng đo lường tác động của hiện tượng suy giảm ngầm (**Silent Failure**) khi dữ liệu bị lỗi và chứng minh năng lực tự phục hồi (**Self-Healing / Idempotent Repair**) từ snapshot thô ban đầu.

---

## 1. Bảng Tổng Hợp So Sánh Hiệu Năng (Performance Benchmarks)

| Chỉ số / Trạng thái | Baseline (Dữ liệu sạch) | Corrupted (Dữ liệu bẩn) | Repaired (Sau phục hồi) | Đánh giá mức độ phục hồi |
|:---|:---:|:---:|:---:|:---|
| **Retrieval Hit Rate** | `1.0000` | `0.7000` | `1.0000` | Phục hồi 100% |
| **Mean Token F1** | `0.5154` | `0.1860` | `0.5154` | Khôi phục độ trùng khớp văn bản |
| **Judge Accuracy** | `0.5000` | `0.2000` | `0.5000` | Khôi phục độ chính xác câu trả lời |
| **Mean Judge Score** | `3.00 / 5.0` | `1.80 / 5.0` | `3.00 / 5.0` | Chất lượng AI được khôi phục |

---

## 2. Tín Hiệu Cảnh Báo Data Quality Gate & Freshness SLA

| Chốt kiểm định | Trạng thái Corrupted | Trạng thái Repaired | Ghi chú quan sát |
|:---|:---:|:---:|:---|
| **Great Expectations 1.x** | `FAIL (Đã chặn)` | `PASS` | Quality Gate phát hiện các vi phạm not-null, length và unique |
| **Freshness SLA** | `STALE (Cảnh báo)` | `FRESH` | Lỗi stale date bị phát hiện do tỷ lệ quá hạn vượt ngưỡng |

---

## 3. Phân Tích Hiện Tượng Silent Failure & Cơ Chế Phục Hồi

1. **Hiện tượng Silent Failure:** Khi dữ liệu bị tiêm lỗi (xóa abstract, cắt tiêu đề, chèn rác, duplicate), ứng dụng RAG không ném ra exception nhưng độ chính xác truy vấn giảm mạnh và chất lượng câu trả lời bị thoái hóa rõ rệt.
2. **Cơ chế Phục hồi (Idempotent Repair):** Sử dụng snapshot thô ban đầu `data/raw/crossref_records.json` (Lineage Anchor), kích hoạt hàm `repair_from_raw_snapshot()` để tái tạo lại toàn bộ clean dataset và re-index lại ChromaDB, đưa toàn bộ chỉ số về trạng thái tối ưu ban đầu.
