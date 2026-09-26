from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import ensure_parent, write_json

logger = logging.getLogger(__name__)


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | None = None) -> dict[str, Any]:
    """Tổng hợp freshness report và kiểm tra Freshness SLA.

    Logic nghiệp vụ:
    1. Tìm latest và oldest published date.
    2. Đếm số dòng stale dựa trên ngưỡng settings.freshness_threshold_days (mặc định 180 ngày).
    3. Freshness SLA: Cảnh báo is_fresh = False nếu tỷ lệ dòng stale vượt quá 25% tổng số bản ghi.
    4. Ghi JSON report nếu report_path được truyền vào.
    """
    total_rows = len(df)
    if total_rows == 0:
        report = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "threshold_days": settings.freshness_threshold_days,
            "is_fresh": True,
        }
        if report_path:
            write_json(Path(report_path), report)
        return report

    published_series = df["published"].dropna().astype(str).str[:10]
    latest_published = published_series.max() if not published_series.empty else "N/A"
    oldest_published = published_series.min() if not published_series.empty else "N/A"

    threshold = settings.freshness_threshold_days
    stale_rows = int((df["age_days"] > threshold).sum()) if "age_days" in df.columns else 0
    stale_ratio = stale_rows / total_rows if total_rows > 0 else 0.0

    # Freshness SLA: Nếu tỷ lệ stale > 25%, gắn cờ is_fresh = False
    is_fresh = stale_ratio <= 0.25

    report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "threshold_days": threshold,
        "is_fresh": is_fresh,
    }

    if report_path:
        write_json(Path(report_path), report)

    return report


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Thực thi Data Quality Gate bằng Great Expectations 1.x (Ephemeral Context).

    4 Expectations bắt buộc theo Rubric:
    1. ExpectTableRowCountToBeBetween: Số lượng bản ghi nằm trong khoảng [5, 5000].
    2. ExpectColumnValuesToNotBeNull: paper_id, title, text_for_embedding không được rỗng (null).
    3. ExpectColumnValuesToBeUnique: paper_id là duy nhất.
    4. ExpectColumnValueLengthsToBeBetween: summary có độ dài tối thiểu 30 ký tự.
    """
    context = gx.get_context(mode="ephemeral")

    # Tạo data source, data asset và batch definition
    source_name = f"papers_source_{report_name}"
    asset_name = f"papers_asset_{report_name}"
    batch_name = f"papers_batch_{report_name}"

    data_source = context.data_sources.add_pandas(name=source_name)
    data_asset = data_source.add_dataframe_asset(name=asset_name)
    batch_def = data_asset.add_batch_definition_whole_dataframe(batch_name)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # Khởi tạo Expectation Suite
    suite = gx.ExpectationSuite(name=f"papers_quality_suite_{report_name}")

    # 1. Row count between 5 and 5000
    suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))

    # 2. Columns not null
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))

    # 3. paper_id unique
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"))

    # 4. summary length at least 30 characters
    suite.add_expectation(gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    # Validate batch
    validation_result = batch.validate(suite)
    gx_success = bool(validation_result.success)

    # Chi tiết từng expectation
    checks: list[dict[str, Any]] = []
    for res in validation_result.results:
        exp_type = res.expectation_config.type if hasattr(res.expectation_config, "type") else res.expectation_config.expectation_type
        kwargs = res.expectation_config.kwargs if hasattr(res.expectation_config, "kwargs") else {}
        checks.append(
            {
                "expectation": exp_type,
                "kwargs": kwargs,
                "success": bool(res.success),
                "result": res.result,
            }
        )

    # Đánh giá Freshness SLA
    freshness_report = build_freshness_report(df, settings)

    overall_success = gx_success and freshness_report["is_fresh"]

    report_payload = {
        "report_name": report_name,
        "success": overall_success,
        "gx_success": gx_success,
        "row_count": len(df),
        "freshness": freshness_report,
        "expectations": checks,
    }

    # Ghi file kết quả tương ứng với stage/report_name
    output_dir = settings.paths.quality_dir
    ensure_parent(output_dir / "placeholder.txt")

    if report_name in {"baseline", "phase1"}:
        out_path = settings.paths.baseline_quality_report
    elif report_name in {"corrupted"}:
        out_path = settings.paths.corrupted_quality_report
    else:
        out_path = output_dir / f"{report_name}_quality_report.json"

    write_json(out_path, report_payload)

    return report_payload