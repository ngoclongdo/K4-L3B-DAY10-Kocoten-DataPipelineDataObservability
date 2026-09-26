from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

from core.utils import compact_join, normalize_whitespace, write_csv, write_json
from ingestion.crossref import PaperRecord


def _format_embedding_text(
    title: str,
    authors: str,
    published: str,
    categories: str,
    summary: str,
) -> str:
    """Format đoạn text_for_embedding chuẩn theo đúng quy định của bài lab:
    Title: <Tiêu đề bài báo>
    Authors: <Danh sách tác giả>
    Published: <Ngày xuất bản>
    Categories: <Lĩnh vực chuyên môn>
    Summary: <Tóm tắt nội dung>
    """
    return (
        f"Title: {title}\n"
        f"Authors: {authors}\n"
        f"Published: {published}\n"
        f"Categories: {categories}\n"
        f"Summary: {summary}"
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thành dataframe sạch sẵn sàng để embed và đánh giá chất lượng.

    Các bước thực hiện:
    1. Chuyển đổi list PaperRecord thành danh sách dict chuẩn hóa.
    2. Chuẩn hóa khoảng trắng cho title, summary.
    3. Ghép authors_joined, categories_joined.
    4. Tính tuổi đời dữ liệu: age_days = (run_date - published).days.
    5. Tạo text_for_embedding theo chuẩn 5 phần.
    6. Khử trùng lặp theo khóa duy nhất paper_id.
    7. Loại bỏ các dòng không hợp lệ (paper_id hoặc title rỗng).
    8. Sắp xếp dataframe theo paper_id và trả về.
    """
    rows: list[dict] = []

    # Đảm bảo run_date có múi giờ hoặc naive đồng nhất để trừ ngày
    if run_date.tzinfo is not None:
        run_date_dt = run_date.date()
    else:
        run_date_dt = run_date.date()

    for r in records:
        paper_id = normalize_whitespace(r.paper_id)
        title = normalize_whitespace(r.title)
        summary = normalize_whitespace(r.summary)

        if not paper_id or not title:
            continue

        authors_list = [normalize_whitespace(a) for a in r.authors if normalize_whitespace(a)]
        categories_list = [normalize_whitespace(c) for c in r.categories if normalize_whitespace(c)]

        authors_joined = compact_join(authors_list, sep=", ")
        categories_joined = compact_join(categories_list, sep=", ")

        # Parse ngày xuất bản để tính age_days
        published_str = r.published.strip()
        age_days = 0
        if published_str:
            try:
                # Định dạng chuẩn YYYY-MM-DD
                pub_date = datetime.strptime(published_str[:10], "%Y-%m-%d").date()
                age_days = (run_date_dt - pub_date).days
            except Exception:
                age_days = 0

        # Tạo text_for_embedding hoàn chỉnh 5 dòng
        text_for_embedding = _format_embedding_text(
            title=title,
            authors=authors_joined,
            published=published_str,
            categories=categories_joined,
            summary=summary,
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors_list,
                "authors_joined": authors_joined,
                "categories": categories_list,
                "categories_joined": categories_joined,
                "primary_category": r.primary_category or (categories_list[0] if categories_list else "General"),
                "published": published_str,
                "updated": r.updated,
                "abs_url": r.abs_url,
                "pdf_url": r.pdf_url,
                "comment": r.comment,
                "age_days": age_days,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Khử trùng lặp theo paper_id, giữ lại bản ghi đầu tiên
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Sắp xếp lại theo paper_id cho tính tất định (deterministic)
    df = df.sort_values(by=["paper_id"]).reset_index(drop=True)

    return df


def repair_from_raw_snapshot(raw_records_path, run_date: datetime) -> pd.DataFrame:
    """Cơ chế phục hồi dữ liệu (Idempotent Data Repair):
    Đọc snapshot thô nguyên bản từ raw_records_path và chạy lại luồng clean,
    ghi đè và tái tạo hoàn toàn DataFrame sạch ban đầu.
    """
    from ingestion.crossref import load_raw_records
    raw_records = load_raw_records(raw_records_path)
    return build_clean_dataframe(raw_records, run_date)


def save_clean_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    """Lưu dataframe đã làm sạch ra định dạng CSV và JSON."""
    write_csv(df, csv_path)
    records_payload = df.to_dict(orient="records")
    write_json(json_path, records_payload)

