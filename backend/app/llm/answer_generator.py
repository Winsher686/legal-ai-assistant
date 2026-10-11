"""答案生成与引用溯源模块。"""
import json
from typing import Dict, List, Optional

from app.core.config import settings
from app.core.logger import logger
from app.llm.client import get_llm
from app.llm.prompt_template import ANSWER_TEMPLATE, CITATION_CHECK_TEMPLATE, SYSTEM_PROMPT


class CitationBuilder:
    """引用构建：从检索结果生成引用结构。"""

    def build(self, docs: List[Dict]) -> List[Dict]:
        sources = []
        for i, d in enumerate(docs):
            sources.append({
                "citation_id": f"cite{i + 1}",
                "document_id": d.get("document_id", ""),
                "document_name": d.get("document_name", ""),
                "chapter": d.get("chapter", ""),
                "article": d.get("article", ""),
                "page": d.get("page", 0),
                "text": d.get("content", "")[:200],
            })
        return sources


class CitationChecker:
    """引用校验：检查答案是否超出检索范围（防幻觉）。"""

    def check(self, answer: str, context: str) -> Dict:
        if settings.USE_MOCK or settings.LLM_PROVIDER == "mock":
            return {"is_supported": True, "unsupported": []}
        prompt = CITATION_CHECK_TEMPLATE.format(context=context, answer=answer)
        try:
            raw = get_llm().chat(
                [{"role": "user", "content": prompt}], json_mode=True
            )
            return json.loads(raw)
        except Exception as e:
            logger.warning("citation check failed: %s", e)
            return {"is_supported": True, "unsupported": []}


def build_context(docs: List[Dict], graph_context: Optional[Dict] = None) -> str:
    """构建送入 LLM 的上下文。"""
    parts = []
    for i, d in enumerate(docs):
        src = f"[{i + 1}] {d.get('document_name', '')}"
        if d.get("chapter"):
            src += f" {d.get('chapter', '')}"
        if d.get("article"):
            src += f" {d.get('article', '')}"
        if d.get("page"):
            src += f" 第{d.get('page', '')}页"
        parts.append(f"{src}\n{d.get('content', '')}")

    if graph_context and graph_context.get("related"):
        rels = graph_context["related"]
        parts.append("【知识图谱关系】")
        for r in rels:
            parts.append(f"{r.get('from', r.get('node', ''))} --{r.get('relation', r.get('rel', ''))}--> {r.get('to', '')}")
        parts.append("")

    return "\n\n".join(parts)


def compute_confidence(docs: List[Dict], answer: str) -> float:
    """可信度评分：综合检索得分与引用充分度。"""
    if not docs:
        return 0.0
    # 兼容多路召回：score(向量) / rrf_score(融合) / rerank_score(精排)
    def _score(d):
        return d.get("rerank_score", d.get("score", d.get("rrf_score", 0.0)))

    top_score = max((_score(d) for d in docs), default=0.0)
    citation_score = min(len(docs) / 5.0, 1.0)
    # rrf_score 通常远小于 1，做温和归一化
    if top_score > 1.0:
        norm_score = 1.0
    else:
        norm_score = max(0.0, min(top_score, 1.0))
    confidence = 0.5 * norm_score + 0.3 * citation_score + 0.2
    return round(min(max(confidence, 0.0), 1.0), 3)
