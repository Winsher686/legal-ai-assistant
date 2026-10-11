"""关键词检索（BM25）+ 混合检索 + RRF 融合 + Reranker。

- BM25Retriever：基于 rank_bm25 的关键词检索器，维护全局语料索引。
- Reranker：cross-encoder 精排（BGE-reranker），无模型时降级为分数排序。
- rrf_fusion：Reciprocal Rank Fusion 融合向量与关键词召回结果。
"""
from typing import Dict, List, Optional

from app.core.config import settings
from app.core.logger import logger


class BM25Retriever:
    """基于 rank_bm25 的关键词检索器（全局单例，入库时增删索引）。"""

    def __init__(self):
        self._corpus: List[str] = []
        self._docs: List[Dict] = []
        self._bm25 = None
        self._tokenize = None

    def _get_tokenizer(self):
        if self._tokenize is None:
            try:
                import jieba

                self._tokenize = lambda t: list(jieba.cut(t))
            except Exception:
                self._tokenize = lambda t: t.split()
        return self._tokenize

    def _rebuild(self) -> None:
        """根据当前语料重建 BM25 索引。"""
        self._bm25 = None
        if not self._corpus:
            return
        try:
            from rank_bm25 import BM25Okapi

            tokenize = self._get_tokenizer()
            tokenized = [tokenize(t) for t in self._corpus]
            self._bm25 = BM25Okapi(tokenized)
        except Exception as e:
            logger.warning("bm25 rebuild failed: %s", e)
            self._bm25 = None

    def add(self, docs: List[Dict]) -> None:
        """增量添加 chunk 到索引。docs: [{id, content, ...}]"""
        if not docs:
            return
        for d in docs:
            self._corpus.append(d.get("content", ""))
            self._docs.append(d)
        self._rebuild()

    def remove_by_document(self, document_id: str) -> None:
        """按 document_id 删除该文档的所有 chunk。"""
        positions = {i for i, d in enumerate(self._docs)
                     if d.get("document_id") == document_id}
        if not positions:
            return
        self._docs = [d for i, d in enumerate(self._docs) if i not in positions]
        self._corpus = [c for i, c in enumerate(self._corpus) if i not in positions]
        self._rebuild()

    def search(self, query: str, top_k: int) -> List[Dict]:
        if self._bm25 is None or not self._corpus:
            return []
        tokenize = self._get_tokenizer()
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        results = []
        for i in ranked[:top_k]:
            results.append({**self._docs[i], "bm25_score": float(scores[i])})
        return results

    def count(self) -> int:
        return len(self._docs)


class Reranker:
    """重排序器：优先 cross-encoder 精排，降级为已有 score 排序。"""

    def __init__(self):
        self._model = None
        self._load_failed = False

    def _load(self):
        if self._model is not None or self._load_failed:
            return self._model
        if settings.USE_MOCK or settings.EMBEDDING_PROVIDER == "mock":
            # mock 模式下不加载重型模型，直接用分数排序
            self._load_failed = True
            return None
        try:
            from sentence_transformers import CrossEncoder

            logger.info("loading reranker model %s ...", settings.RERANKER_MODEL)
            self._model = CrossEncoder(settings.RERANKER_MODEL)
        except Exception as e:
            logger.warning("cross-encoder load failed(%s), fallback to score rank", e)
            self._load_failed = True
            self._model = None
        return self._model

    def rerank(self, query: str, docs: List[Dict]) -> List[Dict]:
        if not docs:
            return []
        model = self._load()
        if model is None:
            # 降级：按已有 score / rrf_score 排序
            return sorted(docs,
                          key=lambda d: d.get("score", d.get("rrf_score", 0.0)),
                          reverse=True)

        pairs = [(query, d.get("content", "")) for d in docs]
        try:
            scores = model.predict(pairs)
            for d, s in zip(docs, scores):
                d["rerank_score"] = float(s)
            return sorted(docs, key=lambda d: d["rerank_score"], reverse=True)
        except Exception as e:
            logger.warning("rerank predict failed(%s), fallback to score rank", e)
            return sorted(docs,
                          key=lambda d: d.get("score", d.get("rrf_score", 0.0)),
                          reverse=True)


def rrf_fusion(vector_results: List[Dict], keyword_results: List[Dict],
               k: int = None, vector_weight: float = 1.0,
               keyword_weight: float = 1.0) -> List[Dict]:
    """Reciprocal Rank Fusion：融合向量与关键词检索结果。

    - 可为两路召回设置不同权重（默认等权）。
    - 文档标识优先取 id，其次 content。
    """
    k = k or settings.RAG_RRF_K
    score_map: Dict[str, Dict] = {}

    def add_rank(results, weight: float):
        if weight <= 0:
            return
        for rank, doc in enumerate(results):
            doc_id = doc.get("id", doc.get("content", ""))
            if doc_id not in score_map:
                score_map[doc_id] = {**doc, "rrf_score": 0.0}
            score_map[doc_id]["rrf_score"] += weight / (k + rank + 1)

    add_rank(vector_results, vector_weight)
    add_rank(keyword_results, keyword_weight)

    fused = list(score_map.values())
    fused.sort(key=lambda d: d["rrf_score"], reverse=True)
    return fused


# ------------------------------------------------------------------
# 全局单例：入库与检索共享同一份 BM25 索引
# ------------------------------------------------------------------
_bm25_retriever: Optional[BM25Retriever] = None


def get_bm25_retriever() -> BM25Retriever:
    global _bm25_retriever
    if _bm25_retriever is None:
        _bm25_retriever = BM25Retriever()
    return _bm25_retriever
