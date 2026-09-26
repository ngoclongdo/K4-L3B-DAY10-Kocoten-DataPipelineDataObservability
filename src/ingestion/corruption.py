from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import ensure_parent, normalize_whitespace, write_json
from ingestion.cleaning import _format_embedding_text


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Giả lập 6 dạng sự cố dữ liệu thực tế (Synthetic Data Corruption Suite):
    1. Drop latest records: Bỏ rơi 20% các bài báo mới nhất (dựa trên published date).
    2. Blank summary: Xóa trắng phần tóm tắt ở một số dòng.
    3. Inject noise: Chèn các chuỗi ký tự rác vào tóm tắt.
    4. Truncate title: Cắt ngắn tiêu đề xuống dưới 8 ký tự.
    5. Stale date: Lùi ngày xuất bản về 365 ngày trước để vi phạm Freshness SLA.
    6. Duplicate rows: Nhân đôi các dòng để tạo trùng lặp khóa chính paper_id.

    Ghi lại nhật ký toàn bộ các thay đổi vào output_log_path (corruption_log.json).
    """
    corrupted_df = df.copy()
    logs: list[dict[str, Any]] = []

    # 1. Drop 20% latest records
    if len(corrupted_df) >= 5:
        # Sắp xếp theo ngày xuất bản giảm dần để tìm các bài mới nhất
        sorted_by_date = corrupted_df.sort_values(by=["published"], ascending=False)
        drop_count = max(1, int(len(corrupted_df) * 0.20))
        dropped_records = sorted_by_date.iloc[:drop_count]
        dropped_ids = set(dropped_records["paper_id"].tolist())

        for _, r in dropped_records.iterrows():
            logs.append(
                {
                    "corruption_type": "drop_latest_record",
                    "paper_id": r["paper_id"],
                    "title": r["title"],
                    "detail": f"Dropped latest record published on {r['published']}",
                }
            )
        corrupted_df = corrupted_df[~corrupted_df["paper_id"].isin(dropped_ids)].copy().reset_index(drop=True)

    # 2. Blank summary ở một vài dòng
    if len(corrupted_df) > 1:
        target_idx = 0
        p_id = corrupted_df.at[target_idx, "paper_id"]
        old_val = corrupted_df.at[target_idx, "summary"]
        corrupted_df.at[target_idx, "summary"] = ""
        corrupted_df.at[target_idx, "summary_chars"] = 0
        logs.append(
            {
                "corruption_type": "blank_summary",
                "paper_id": p_id,
                "original_summary_snippet": old_val[:50],
                "detail": "Set summary to empty string",
            }
        )

    # 3. Inject noise vào summary
    if len(corrupted_df) > 2:
        target_idx = 1
        p_id = corrupted_df.at[target_idx, "paper_id"]
        old_val = corrupted_df.at[target_idx, "summary"]
        noise_text = " @@ERROR_NOISE_CORRUPTED_STRING_RANDOM_GARBAGE_PAYLOAD@@ "
        new_val = noise_text + old_val
        corrupted_df.at[target_idx, "summary"] = new_val
        corrupted_df.at[target_idx, "summary_chars"] = len(new_val)
        logs.append(
            {
                "corruption_type": "inject_noise",
                "paper_id": p_id,
                "injected_noise": noise_text.strip(),
                "detail": "Prepended noisy corrupt payload to summary",
            }
        )

    # 4. Truncate title xuống dưới 8 ký tự
    if len(corrupted_df) > 3:
        target_idx = 2
        p_id = corrupted_df.at[target_idx, "paper_id"]
        old_title = corrupted_df.at[target_idx, "title"]
        corrupted_df.at[target_idx, "title"] = "Paper"  # 5 ký tự (< 8)
        logs.append(
            {
                "corruption_type": "truncate_title",
                "paper_id": p_id,
                "original_title": old_title,
                "new_title": "Paper",
                "detail": "Truncated title to 5 characters",
            }
        )

    # 5. Stale date: Lùi ngày xuất bản về 365 ngày trước cho 35% số bản ghi để vi phạm Freshness SLA (> 25%)
    stale_count = max(2, int(len(corrupted_df) * 0.35))
    for idx in range(stale_count):
        p_id = corrupted_df.at[idx, "paper_id"]
        old_published = str(corrupted_df.at[idx, "published"])
        old_age = int(corrupted_df.at[idx, "age_days"])
        # Cộng thêm 365 ngày vào age_days
        new_age = old_age + 365
        try:
            pub_dt = datetime.strptime(old_published[:10], "%Y-%m-%d")
            new_pub = pub_dt.replace(year=pub_dt.year - 1).strftime("%Y-%m-%d")
        except Exception:
            new_pub = "2024-01-01"

        corrupted_df.at[idx, "published"] = new_pub
        corrupted_df.at[idx, "age_days"] = new_age
        logs.append(
            {
                "corruption_type": "stale_date",
                "paper_id": p_id,
                "original_published": old_published,
                "corrupted_published": new_pub,
                "new_age_days": new_age,
                "detail": "Shifted publication date back by 365 days to induce SLA violation",
            }
        )

    # 6. Rebuild text_for_embedding cho các dòng đã thay đổi
    for idx in range(len(corrupted_df)):
        corrupted_df.at[idx, "text_for_embedding"] = _format_embedding_text(
            title=str(corrupted_df.at[idx, "title"]),
            authors=str(corrupted_df.at[idx, "authors_joined"]),
            published=str(corrupted_df.at[idx, "published"]),
            categories=str(corrupted_df.at[idx, "categories_joined"]),
            summary=str(corrupted_df.at[idx, "summary"]),
        )

    # 7. Duplicate rows: Nhân bản một số dòng để tạo trùng lặp paper_id
    if len(corrupted_df) > 0:
        dup_rows = corrupted_df.iloc[:2].copy()
        for _, r in dup_rows.iterrows():
            logs.append(
                {
                    "corruption_type": "duplicate_row",
                    "paper_id": r["paper_id"],
                    "detail": "Duplicated existing row to violate unique primary key constraint",
                }
            )
        corrupted_df = pd.concat([corrupted_df, dup_rows], ignore_index=True)

    out_p = Path(output_log_path)
    write_json(out_p, logs)

    return corrupted_df
