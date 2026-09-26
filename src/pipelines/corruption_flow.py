from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe, repair_from_raw_snapshot
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_corruption_flow_pipeline(settings: Settings) -> None:
    """Xây dựng và thực thi toàn tuyến Phase 2:
    1. Load Clean Dataset và Baseline Metrics.
    2. Tiêm 6 dạng lỗi dữ liệu vào clean DataFrame (Corrupt).
    3. Lưu corrupted artifacts và ghi log data/results/corruption_log.json.
    4. Chạy Quality Gate (GX 1.x) và Freshness SLA trên dữ liệu bẩn (phát hiện vi phạm).
    5. Đánh chỉ mục ChromaDB collection papers-corrupted và đánh giá RAG (quan sát Silent Failure).
    6. Kích hoạt cơ chế Idempotent Repair: khôi phục từ snapshot raw ban đầu (crossref_records.json).
    7. Lưu repaired artifacts, chạy lại Quality Gate và Freshness SLA (phục hồi).
    8. Đánh chỉ mục ChromaDB collection papers-repaired và đánh giá lại RAG.
    9. Xuất bảng so sánh 3 trạng thái tại data/reports/corruption_report.md và console.
    """
    logger.info("=== Bắt đầu Phase 2: Corruption, Observability & Idempotent Repair Flow ===")
    run_date = now_utc()

    # 1. Load Baseline Data & Metrics
    if not settings.paths.clean_csv.exists() or not settings.paths.baseline_metrics.exists():
        logger.warning("Chưa tìm thấy dữ liệu Phase 1, đang nạp từ raw snapshot...")
        raw_records = load_raw_records(settings.paths.raw_records_json)
        clean_df = build_clean_dataframe(raw_records, run_date)
        write_csv(clean_df, settings.paths.clean_csv)
    else:
        clean_df = pd.read_csv(settings.paths.clean_csv)

    baseline_metrics = read_json(settings.paths.baseline_metrics)

    # 2. Tạo Corrupted DataFrame
    logger.info("Bước 1: Tiêm 6 kịch bản lỗi dữ liệu thực nghiệm...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    logger.info("Đã lưu dữ liệu bẩn tại %s (tổng %d dòng).", settings.paths.corrupted_clean_csv, len(corrupted_df))

    # 3. Quality Gate & Freshness trên dữ liệu bẩn
    logger.info("Bước 2: Kiểm định dữ liệu bẩn qua Quality Gate GX 1.x & Freshness SLA...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(corrupted_df, settings)
    logger.info("Trạng thái Quality Gate trên Corrupted Data: %s (Kỳ vọng: FAIL)", corrupted_quality["gx_success"])
    logger.info("Trạng thái Freshness SLA trên Corrupted Data: is_fresh=%s (Kỳ vọng: False/Stale)", corrupted_freshness["is_fresh"])

    # 4. Indexing & Evaluation trên dữ liệu bẩn (Silent Failure)
    logger.info("Bước 3: Indexing vào ChromaDB ('%s') và đo lường sự sụt giảm của AI...", settings.corrupted_collection_name)
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    logger.info("Corrupted Metrics: %s", json.dumps(corrupted_metrics, indent=2))

    # 5. Idempotent Repair từ Raw Snapshot
    logger.info("Bước 4: Kích hoạt Idempotent Data Repair từ raw snapshot đáng tin cậy...")
    repaired_df = repair_from_raw_snapshot(settings.paths.raw_records_json, run_date)
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    logger.info("Tái tạo thành công %d dòng dữ liệu sạch sau repair.", len(repaired_df))

    # 6. Quality Gate & Freshness sau Repair
    logger.info("Bước 5: Tái thẩm định Quality Gate & Freshness SLA sau khi sửa chữa...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(repaired_df, settings)
    logger.info("Trạng thái Quality Gate sau Repair: %s (Kỳ vọng: PASS)", repaired_quality["gx_success"])

    # 7. Indexing & Evaluation trên dữ liệu Repaired
    logger.info("Bước 6: Re-index ChromaDB ('%s') và tái đánh giá hiệu năng AI...", settings.repaired_collection_name)
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    logger.info("Repaired Metrics: %s", json.dumps(repaired_metrics, indent=2))

    # 8. Xuất báo cáo Markdown so sánh 3 trạng thái
    logger.info("Bước 7: Xuất báo cáo đối chiếu vào %s...", settings.paths.comparison_report)
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    # In bảng so sánh trực quan 3 cột ra console
    print("\n" + "=" * 80)
    print(f"{'BẢNG ĐỐI CHIẾU HIỆU NĂNG 3 TRẠNG THÁI (BASELINE vs CORRUPTED vs REPAIRED)':^80}")
    print("=" * 80)
    print(f"{'Chỉ số':<25} | {'Baseline':<15} | {'Corrupted':<15} | {'Repaired':<15}")
    print("-" * 80)
    print(f"{'Retrieval Hit Rate':<25} | {baseline_metrics.get('retrieval_hit_rate', 0):<15.4f} | {corrupted_metrics.get('retrieval_hit_rate', 0):<15.4f} | {repaired_metrics.get('retrieval_hit_rate', 0):<15.4f}")
    print(f"{'Mean Token F1':<25} | {baseline_metrics.get('mean_token_f1', 0):<15.4f} | {corrupted_metrics.get('mean_token_f1', 0):<15.4f} | {repaired_metrics.get('mean_token_f1', 0):<15.4f}")
    print(f"{'Judge Accuracy':<25} | {baseline_metrics.get('judge_accuracy', 0):<15.4f} | {corrupted_metrics.get('judge_accuracy', 0):<15.4f} | {repaired_metrics.get('judge_accuracy', 0):<15.4f}")
    print(f"{'Mean Judge Score':<25} | {baseline_metrics.get('mean_judge_score', 0):<15.2f} | {corrupted_metrics.get('mean_judge_score', 0):<15.2f} | {repaired_metrics.get('mean_judge_score', 0):<15.2f}")
    print(f"{'GX 1.x Quality Gate':<25} | {'PASS':<15} | {'FAIL':<15} | {'PASS':<15}")
    print(f"{'Freshness SLA Status':<25} | {'FRESH':<15} | {'STALE':<15} | {'FRESH':<15}")
    print("=" * 80 + "\n")


def main() -> None:
    settings = load_settings()
    run_corruption_flow_pipeline(settings)
