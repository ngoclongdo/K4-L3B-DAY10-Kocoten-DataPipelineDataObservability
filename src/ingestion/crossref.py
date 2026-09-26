from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import logging
from pathlib import Path
import re
from typing import Any
import urllib.parse
import urllib.request
import urllib.error

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace, read_json, write_json

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_abstract(raw_abstract: str) -> str:
    """Loại bỏ các thẻ HTML/XML rác như <jats:p>, <jats:title>, v.v. và chuẩn hóa khoảng trắng."""
    if not raw_abstract:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", raw_abstract)
    return normalize_whitespace(cleaned)


def _format_date_parts(date_parts: list[Any] | None) -> str:
    """Format Crossref date-parts [[YYYY, MM, DD]] thành ISO format YYYY-MM-DD."""
    if not date_parts or not isinstance(date_parts, list) or not date_parts[0]:
        return ""
    parts = date_parts[0]
    year = int(parts[0]) if len(parts) > 0 else 1970
    month = int(parts[1]) if len(parts) > 1 else 1
    day = int(parts[2]) if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thành danh sách PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        # Title
        titles = item.get("title", [])
        title = normalize_whitespace(titles[0]) if titles and isinstance(titles, list) else ""
        if not title:
            continue

        # Abstract / Summary
        raw_abstract = item.get("abstract", "")
        summary = _clean_abstract(raw_abstract)

        # Authors
        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = normalize_whitespace(f"{given} {family}")
            if full_name:
                authors.append(full_name)
            elif family:
                authors.append(family)

        # Subjects / Categories
        subjects = item.get("subject", [])
        categories = [normalize_whitespace(s) for s in subjects if normalize_whitespace(s)]
        primary_category = categories[0] if categories else "General"

        # Dates
        published = _format_date_parts(item.get("published", {}).get("date-parts"))
        if not published:
            published_print = _format_date_parts(item.get("published-print", {}).get("date-parts"))
            published_online = _format_date_parts(item.get("published-online", {}).get("date-parts"))
            published = published_print or published_online or "2026-01-01"

        updated = item.get("created", {}).get("date-time", "")
        if not updated:
            updated = f"{published}T00:00:00Z"

        # URLs
        url = item.get("URL", f"https://doi.org/{doi}")
        abs_url = url
        pdf_url = ""
        for link in item.get("link", []):
            content_type = link.get("content-type", "")
            if "pdf" in content_type:
                pdf_url = link.get("URL", "")
                break
        if not pdf_url:
            pdf_url = f"{url}.pdf"

        record = PaperRecord(
            paper_id=doi,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment="",
        )
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Gọi API Crossref hoặc đọc snapshot local, lưu 2 file raw artifacts và trả về list records."""
    payload: dict | None = None
    snapshot_path = settings.paths.raw_api_response

    # Nếu settings cấu hình refresh_source, thử gọi Crossref API
    if settings.refresh_source:
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": str(settings.max_results),
        }
        url = f"https://api.crossref.org/works?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "VinUniDataObservabilityLab/1.0 (mailto:student@vinuni.edu.vn)"
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, Exception) as exc:
            logger.warning("Không thể gọi Crossref API (%s), kích hoạt chế độ Fallback sang local snapshot.", exc)

    # Fallback: Nếu không gọi API hoặc API lỗi / refresh_source=False, đọc snapshot có sẵn
    if payload is None:
        if snapshot_path.exists():
            payload = read_json(snapshot_path)
        else:
            raise FileNotFoundError(f"Không tìm thấy file snapshot raw tại {snapshot_path}")

    # Đảm bảo lưu lại toàn bộ raw response JSON phục vụ Lineage Anchor
    write_json(settings.paths.raw_api_response, payload)

    # Parse payload thành PaperRecord
    records = parse_crossref_payload(payload)

    # Lưu danh sách PaperRecord đã bóc tách ra data/raw/crossref_records.json
    records_dict = [asdict(record) for record in records]
    write_json(settings.paths.raw_records_json, records_dict)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Đọc JSON snapshot và map thành list PaperRecord."""
    data = read_json(path)
    if isinstance(data, dict) and "message" in data:
        return parse_crossref_payload(data)
    elif isinstance(data, list):
        return [PaperRecord(**item) for item in data]
    raise ValueError(f"Định dạng file không hợp lệ tại {path}")
