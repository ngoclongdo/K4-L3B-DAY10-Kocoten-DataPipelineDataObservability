from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import ensure_parent, first_sentence, normalize_whitespace, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Tự động sinh bộ đề kiểm thử chuẩn (Benchmark Test Set) gồm 10 câu hỏi Ground Truth
    phân bổ qua 4 dạng bài toán: summary, authors, date, categories.

    Format mỗi câu hỏi trong test_set.json:
    {
      "id": "eval_001",
      "question_type": "summary",
      "question": "What is the summary of the paper '<Title>'?",
      "ground_truth": "<Nội dung câu đầu tóm tắt chuẩn>",
      "ground_truth_doc_ids": ["<DOI bài báo>"]
    }
    """
    total_papers = len(df)
    if total_papers < 10:
        raise ValueError(f"Số lượng bài báo ({total_papers}) không đủ tối thiểu 10 để sinh test set.")

    # Chọn 10 bài báo đại diện từ dataframe sạch
    selected_papers = df.iloc[:10].to_dict(orient="records")
    test_set: list[dict[str, Any]] = []

    # Phân bổ câu hỏi:
    # 0, 1, 2: summary (3 câu)
    # 3, 4, 5: authors (3 câu)
    # 6, 7: date (2 câu)
    # 8, 9: categories (2 câu)
    for i, paper in enumerate(selected_papers):
        qid = f"eval_{i+1:03d}"
        doi = paper["paper_id"]
        title = paper["title"]
        summary = paper["summary"]
        authors = paper["authors_joined"]
        published = paper["published"]
        categories = paper["categories_joined"]

        if i in {0, 1, 2}:
            qtype = "summary"
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(summary) or summary[:120]
        elif i in {3, 4, 5}:
            qtype = "authors"
            question = f"Who are the authors of the paper '{title}'?"
            ground_truth = authors
        elif i in {6, 7}:
            qtype = "date"
            question = f"When was the paper '{title}' published?"
            ground_truth = published
        else:
            qtype = "categories"
            question = f"What are the research categories or subjects for the paper '{title}'?"
            ground_truth = categories

        test_set.append(
            {
                "id": qid,
                "question_type": qtype,
                "question": normalize_whitespace(question),
                "ground_truth": normalize_whitespace(ground_truth),
                "ground_truth_doc_ids": [doi],
            }
        )

    out_p = Path(output_path)
    write_json(out_p, test_set)
    return test_set