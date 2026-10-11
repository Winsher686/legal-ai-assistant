"""Query 理解模块：分析用户意图、抽取实体、判断是否需要图谱查询。"""
import re
from typing import List

from app.core.config import settings

_RELATION_INDICATORS = [
    "哪些", "什么合同", "哪个部门", "谁负责", "什么风险", "涉及哪些",
    "有哪些", "什么类型", "关联", "负责", "关系",
]


class QueryAnalyzer:
    """查询意图分析。"""

    def analyze(self, question: str) -> dict:
        need_graph = any(k in question for k in _RELATION_INDICATORS)

        # 简单意图分类
        if any(k in question for k in ["是什么", "如何", "怎么", "流程", "要求", "规定"]):
            intent = "policy_query"
        elif any(k in question for k in ["哪些", "有哪些", "什么合同", "什么类型"]):
            intent = "relation_query"
        else:
            intent = "fact_query"

        return {
            "intent": intent,
            "need_graph": need_graph,
            "question": question,
        }


class QueryRewriter:
    """Query 改写与扩展：生成多个查询变体以提高召回率。"""

    def rewrite(self, question: str) -> List[str]:
        """返回 [原问题, 变体1, 变体2, ...]。"""
        variants = [question]
        # 补充领域同义词变体（规则式，生产可用 LLM 改写）
        mapping = {
            "付款": ["付款周期", "付款审批", "付款风险"],
            "审批": ["审核", "审批流程"],
            "审核": ["审批", "法务审核"],
            "竞业限制": ["竞业限制期限", "员工离职限制"],
            "知识产权": ["知识产权条款", "成果归属"],
        }
        extra = set()
        for k, words in mapping.items():
            if k in question:
                extra.update(words)
        variants.extend(list(extra))
        return variants
