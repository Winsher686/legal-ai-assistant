"""Embedding 向量化封装（BGE / OpenAI / Mock），含重试 + 熔断。"""
import hashlib
from typing import List

from app.core.config import settings
from app.core.logger import logger
from app.utils.retry import get_embedding_breaker, retry_call

_model = None


class EmbeddingModel:
    """统一 Embedding 接口。"""

    def __init__(self):
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        if settings.USE_MOCK or settings.EMBEDDING_PROVIDER == "mock":
            self._model = "mock"
        elif settings.EMBEDDING_PROVIDER == "openai":
            self._model = "openai"
        else:  # bge / sentence-transformers
            try:
                from sentence_transformers import SentenceTransformer

                logger.info("loading embedding model %s ...", settings.EMBEDDING_MODEL)
                self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            except Exception as e:
                logger.warning("BGE load failed(%s), fallback to mock", e)
                self._model = "mock"
        return self._model

    def _mock_vector(self, text: str, dim: int) -> List[float]:
        """确定性伪向量：相同文本得到相同向量，可用于本地验证检索流程。"""
        h = hashlib.md5(text.encode("utf-8")).digest()
        vec = []
        for i in range(dim):
            b = h[i % len(h)]
            vec.append((b / 255.0) - 0.5)
        return vec

    def encode(self, text: str) -> List[float]:
        model = self._load()
        if model == "mock":
            return self._mock_vector(text, settings.EMBEDDING_DIM)
        if model == "openai":
            return self._openai_encode(text)
        return self._model.encode(text, normalize_embeddings=True).tolist()

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        model = self._load()
        if model == "mock":
            return [self._mock_vector(t, settings.EMBEDDING_DIM) for t in texts]
        if model == "openai":
            return [self._openai_encode(t) for t in texts]
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def _openai_encode(self, text: str) -> List[float]:
        from openai import OpenAI

        client = OpenAI(api_key=settings.EMBEDDING_API_KEY or settings.LLM_API_KEY,
                        base_url=settings.EMBEDDING_BASE_URL or None)

        def _call():
            resp = client.embeddings.create(model=settings.EMBEDDING_MODEL, input=text)
            return resp.data[0].embedding

        breaker = get_embedding_breaker()
        return breaker(lambda: retry_call(_call))


_embedding: EmbeddingModel = None


def get_embedding() -> EmbeddingModel:
    global _embedding
    if _embedding is None:
        _embedding = EmbeddingModel()
    return _embedding
