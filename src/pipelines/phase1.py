from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path

from core.config import Settings, load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_phase1_pipeline(settings: Settings) -> dict:
    """Xây dựng và thực thi Baseline Pipeline end-to-end (Phase 1):
    1. Ingestion: Thu thập hoặc đọc snapshot thô.
    2. Cleaning: Làm sạch dữ liệu, tính age_days, tạo text_for_embedding, khử trùng lặp.
    3. Storage: Lưu artifacts clean CSV và clean JSON.
    4. Observability: Thực thi Data Quality Gate (GX 1.x) và Freshness SLA.
    5. Test Set: Sinh bộ đề kiểm thử chuẩn (10 câu Ground Truth).
    6. Indexing: Đánh chỉ mục Vector Store (ChromaDB collection papers-baseline).
    7. Evaluation: Đánh giá RAG Hit Rate & Token F1 trên bộ testset.
    8. Reporting: Xuất báo cáo data/reports/phase1_report.md.
    """
    logger.info("=== Bắt đầu Phase 1: Baseline Pipeline ===")
    run_date = now_utc()

    # 1. Ingestion
    logger.info("Bước 1: Ingest dữ liệu từ nguồn Crossref...")
    if settings.paths.raw_records_json.exists() and not settings.refresh_source:
        records = load_raw_records(settings.paths.raw_records_json)
    else:
        records = fetch_source_records(settings)
    raw_count = len(records)
    logger.info("Đã tải/nạp thành công %d bản ghi thô.", raw_count)

    # 2. Cleaning
    logger.info("Bước 2: Làm sạch dữ liệu và tạo text_for_embedding...")
    clean_df = build_clean_dataframe(records, run_date)
    clean_count = len(clean_df)
    logger.info("Làm sạch thành công %d dòng dữ liệu.", clean_count)

    # 3. Lưu artifacts sạch
    write_csv(clean_df, settings.paths.clean_csv)
    records_clean_dict = clean_df.to_dict(orient="records")
    write_json(settings.paths.clean_json, records_clean_dict)
    logger.info("Đã lưu clean artifacts: %s và %s", settings.paths.clean_csv, settings.paths.clean_json)

    # 4. Observability Quality Gate (GX 1.x)
    logger.info("Bước 3: Chạy Data Quality Gate (Great Expectations 1.x & Freshness SLA)...")
    quality_result = run_data_quality_checks(clean_df, settings, "baseline")
    freshness_result = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    logger.info("Quality Gate GX Success: %s | Freshness SLA: %s", quality_result["gx_success"], freshness_result["is_fresh"])

    # 5. Sinh Test Set
    logger.info("Bước 4: Sinh bộ đề kiểm thử chuẩn Benchmark Test Set...")
    if not settings.paths.eval_testset.exists() or settings.refresh_test_set:
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    else:
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    logger.info("Đã chuẩn bị %d câu hỏi kiểm thử tại %s", len(test_set), settings.paths.eval_testset)

    # 6. Indexing ChromaDB
    logger.info("Bước 5: Đánh chỉ mục Vector Store (ChromaDB: %s)...", settings.baseline_collection_name)
    index = LocalEmbeddingIndex.build(
        clean_df,
        settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    logger.info("Đã index %d tài liệu vào collection '%s'.", len(index.documents), index.collection_name)

    # 7. RAG Evaluation
    logger.info("Bước 6: Đánh giá hiệu năng RAG (Hit Rate & Token F1)...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    logger.info("Baseline Metrics: %s", json.dumps(eval_bundle.summary, indent=2))

    # 8. Sinh báo cáo Phase 1 Markdown
    logger.info("Bước 7: Xuất báo cáo Phase 1 vào %s...", settings.paths.baseline_report)
    source_summary = {
        "timestamp": run_date.isoformat(),
        "source_api": settings.source_api,
        "raw_count": raw_count,
        "clean_count": clean_count,
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=eval_bundle.summary,
        quality=quality_result,
        freshness=freshness_result,
    )
    logger.info("=== Phase 1 Pipeline Hoàn Thành Thành Công! ===")
    return eval_bundle.summary


def main() -> None:
    settings = load_settings()
    run_phase1_pipeline(settings)
