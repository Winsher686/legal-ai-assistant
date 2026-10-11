"""RAG 检索器：整合 Query 处理、向量检索、关键词检索、RRF 融合、重排序。"""
from typing import List, Optional

from app.core.config import settings
from app.core.logger import logger
from app.rag.embedding import get_embedding
from app.rag.hybrid_search import Reranker, get_bm25_retriever, rrf_fusion
from app.rag.query_processor import QueryAnalyzer, QueryRewriter
from app.rag.vector_store import get_vector_store


class RAGRetriever:
    """RAG 检索主入口。"""

    def __init__(self):
        self.analyzer = QueryAnalyzer()
        self.rewriter = QueryRewriter()
        self.embedding = get_embedding()
        self.vector_store = get_vector_store()
        self.bm25 = get_bm25_retriever()
        self.reranker = Reranker()

    def retrieve(self, question: str, top_k: Optional[int] = None,
                 filter_expr: Optional[str] = None,
                 mode: str = "hybrid") -> List[dict]:
        """检索主入口。

        mode:
          - "hybrid"：向量 + BM25 关键词 → RRF 融合 → 精排（默认）。
          - "vector"：仅向量检索（用于评测对比 / 消融实验）。
        """
        final_top_k = top_k or settings.RAG_FINAL_TOP_K
        candidate_k = settings.RAG_TOP_K

        # 1. Query 理解 + 改写
        self.analyzer.analyze(question)
        variants = self.rewriter.rewrite(question)

        # 2. 多路召回（向量 + 关键词）
        vector_results: List[dict] = []
        for q in variants:
            vec = self.embedding.encode(q)
            hits = self.vector_store.search(vec, candidate_k, filter_expr)
            vector_results.extend(hits)

        if mode == "vector":
            ranked = self.reranker.rerank(question, self._dedupe(vector_results))
            return ranked[:final_top_k]

        keyword_results = self._keyword_search(question, candidate_k)

        # 3. RRF 融合
        fused = rrf_fusion(vector_results, keyword_results)

        # 4. 去重
        fused = self._dedupe(fused)

        # 5. Reranker 精排
        ranked = self.reranker.rerank(question, fused)

        return ranked[:final_top_k]

    def _keyword_search(self, query: str, top_k: int) -> List[dict]:
        """BM25 关键词检索（基于入库时维护的全局 BM25 索引）。"""
        return self.bm25.search(query, top_k)

    def _dedupe(self, docs: List[dict]) -> List[dict]:
        seen = set()
        result = []
        for d in docs:
            key = d.get("id", d.get("content", ""))
            if key in seen:
                continue
            seen.add(key)
            result.append(d)
        return result
