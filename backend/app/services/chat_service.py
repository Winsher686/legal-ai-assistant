"""问答服务：串联 RAG 检索、GraphRAG 查询、LLM 生成、引用溯源。"""
import json
from typing import Dict, Optional

from app.core.config import settings
from app.core.logger import logger
from app.graph.graph_query import GraphService
from app.llm.answer_generator import (
    CitationBuilder,
    CitationChecker,
    build_context,
    compute_confidence,
)
from app.llm.client import get_llm
from app.llm.prompt_template import ANSWER_TEMPLATE, SYSTEM_PROMPT
from app.rag.query_processor import QueryAnalyzer
from app.rag.retriever import RAGRetriever


class ChatService:
    """智能问答核心服务。"""

    def __init__(self):
        self.rag = RAGRetriever()
        self.graph = GraphService()
        self.analyzer = QueryAnalyzer()
        self.citation_builder = CitationBuilder()
        self.citation_checker = CitationChecker()

    def ask(self, question: str, filter_expr: Optional[str] = None) -> Dict:
        # 1. Query 理解
        analysis = self.analyzer.analyze(question)

        # 2. RAG 检索
        docs = self.rag.retrieve(question, filter_expr=filter_expr)

        # 3. GraphRAG 查询（关系类问题）
        graph_context = {}
        if analysis["need_graph"]:
            graph_context = self.graph.search(question)

        # 4. 上下文融合
        context = build_context(docs, graph_context)

        # 5. LLM 生成
        answer = self._generate(question, context, docs)

        # 6. 引用绑定
        sources = self.citation_builder.build(docs)

        # 7. 可信度评分
        confidence = compute_confidence(docs, answer)

        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "intent": analysis["intent"],
        }

    def _generate(self, question: str, context: str, docs) -> str:
        """调用 LLM 生成答案；无检索结果时给出兜底。"""
        if not docs:
            return "当前知识库未找到相关依据，无法回答该问题。"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": ANSWER_TEMPLATE.format(
                question=question, context=context)},
        ]
        try:
            answer = get_llm().chat(messages)
        except Exception as e:
            logger.error("LLM generate failed: %s", e)
            # 降级：直接返回检索到的第一条内容
            answer = docs[0].get("content", "")

        # Citation Checker（生产环境校验，Mock 跳过）
        checker = self.citation_checker.check(answer, context)
        if not checker.get("is_supported", True):
            answer += "\n（提示：部分内容可能超出知识库范围，请以来源为准。）"

        return answer
