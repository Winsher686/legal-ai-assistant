"""GraphRAG 查询模块：基于知识图谱的关系查询与多跳推理。

实体链接（从问题中抽取实体）：生产环境调用 LLM 抽取，Mock/无 LLM 时降级到规则词典。
"""
import json
from typing import Dict, List, Optional

from app.core.config import settings
from app.core.logger import logger
from app.graph.graph_store import get_graph_store

# 规则降级词典（LLM 不可用时使用）
_RULE_KEYWORDS = ["采购合同", "销售合同", "技术服务合同", "劳动合同",
                  "付款条款", "知识产权条款", "法务审核", "合同审批",
                  "法务部", "财务部", "采购部", "付款风险", "知识产权风险"]


class GraphService:
    """图谱查询服务。"""

    def __init__(self):
        self.graph = get_graph_store()

    def search(self, question: str, entities: Optional[List[str]] = None) -> Dict:
        """根据问题查询图谱，返回关系上下文。"""
        # 优先使用外部传入实体，否则做实体链接（LLM 抽取 → 规则降级）
        if entities:
            entity_list = entities
        else:
            entity_list = self.extract_entities(question)

        if not entity_list:
            return {"entities": [], "related": [], "paths": []}

        related_all: List[Dict] = []
        for entity in entity_list:
            related_all.extend(self.graph.find_related(entity))

        # 去重
        seen = set()
        related_uniq = []
        for r in related_all:
            key = (r.get("from"), r.get("relation"), r.get("to"))
            if key in seen:
                continue
            seen.add(key)
            related_uniq.append(r)

        return {
            "entities": entity_list,
            "related": related_uniq,
            "paths": related_uniq,
        }

    def extract_entities(self, question: str) -> List[str]:
        """实体链接：LLM 抽取实体，降级到规则词典。"""
        if settings.USE_MOCK or settings.LLM_PROVIDER == "mock":
            return self._rule_entities(question)
        try:
            return self._llm_entities(question)
        except Exception as e:
            logger.warning("llm entity linking failed(%s), fallback to rules", e)
            return self._rule_entities(question)

    def _llm_entities(self, question: str) -> List[str]:
        from app.llm.client import get_llm

        prompt = f"""你是企业法务知识图谱的实体链接器。
从用户问题中抽取与法务知识图谱相关的实体（合同类型、条款、部门、流程、法规、风险等）。
只返回 JSON，格式：{{"entities": ["实体1", "实体2"]}}
如果问题中没有相关实体，返回 {{"entities": []}}。

用户问题：{question}
"""
        raw = get_llm().chat([{"role": "user", "content": prompt}], json_mode=True)
        data = json.loads(raw)
        entities = data.get("entities", [])
        return [e for e in entities if isinstance(e, str) and e]

    def _rule_entities(self, question: str) -> List[str]:
        """规则式实体检测（降级用）。"""
        return [k for k in _RULE_KEYWORDS if k in question]

    def query_contracts_needing_review(self, process_name: str = "法务审核") -> List[Dict]:
        """查询需要某流程的合同类型（对应 Cypher：ContractType -[:NEED]-> Process）。"""
        return self.graph.query_nodes_by_relation(
            from_label="ContractType", rel="NEED", to_label="Process", to_name=process_name
        )

    def traverse(self, start_label: str, start_name: str, max_depth: int = 4) -> List[Dict]:
        """多跳遍历。"""
        return self.graph.traverse_path(start_label, start_name, max_depth)
