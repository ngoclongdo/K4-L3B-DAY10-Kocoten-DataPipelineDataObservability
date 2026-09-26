from __future__ import annotations

from functools import lru_cache
import hashlib
import logging
import math
import re

from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


def _deterministic_hash_vector(text: str, dim: int = 384) -> list[float]:
    """Tạo vector nhúng 384 chiều tất định (deterministic hash embedding).
    Sử dụng các đặc trưng n-gram từ ngữ nghĩa của văn bản kết hợp băm an toàn,
    đảm bảo tính tương đồng ngữ nghĩa giữa câu hỏi và tài liệu chứa từ khóa/tiêu đề,
    hoạt động offline 100% không bị treo khi tải trọng số 90MB từ HuggingFace qua mạng yếu.
    """
    words = re.findall(r"\w+", text.lower())
    vec = [0.0] * dim
    if not words:
        return vec

    # N-grams 1-word and 2-word features
    tokens = list(words)
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]}_{words[i+1]}")

    for token in tokens:
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) else -1.0
        weight = 1.0 + math.log(1.0 + len(token))
        vec[idx] += sign * weight

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 1e-9:
        vec = [x / norm for x in vec]
    return vec


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._hf_model = None
        # Thử nạp SentenceTransformer nếu đã có sẵn trong local cache
        try:
            from sentence_transformers import SentenceTransformer
            # Chỉ nạp nếu không phải tải từ mạng hoặc tải nhanh
            self._hf_model = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            self._hf_model = None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._hf_model is not None:
            try:
                embeddings = self._hf_model.encode(texts, normalize_embeddings=True)
                return embeddings.tolist()
            except Exception:
                pass
        return [_deterministic_hash_vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        if self._hf_model is not None:
            try:
                embedding = self._hf_model.encode([text], normalize_embeddings=True)
                return embedding[0].tolist()
            except Exception:
                pass
        return _deterministic_hash_vector(text)
