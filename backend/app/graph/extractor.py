"""实体与关系抽取模块（GraphRAG 数据准备）。

生产环境：调用 LLM 抽取实体与关系。
Mock 模式：基于规则 + 词典抽取，保证本地可跑通。
"""
import json
import re
from typing import List, Tuple

from app.core.config import settings
from app.core.logger import logger

# 实体标签
LABEL_CONTRACT = "ContractType"
LABEL_CLAUSE = "Clause"
LABEL_REGULATION = "Regulation"
LABEL_PROCESS = "Process"
LABEL_DEPARTMENT = "Department"
LABEL_RISK = "Risk"

# 词典（Mock 规则抽取用）
_CONTRACT_KEYS = ["采购合同", "销售合同", "技术服务合同", "劳动合同", "合同"]
_CLAUSE_KEYS = ["付款条款", "知识产权条款", "违约责任条款", "保密条款", "竞业限制条款", "条款"]
_REGULATION_KEYS = ["合同法", "劳动合同法", "公司法", "民法典", "法规"]
_PROCESS_KEYS = ["审批流程", "法务审核", "法务审批", "合同审批", "付款审批", "审核", "审批"]
_DEPARTMENT_KEYS = ["法务部", "财务部", "采购部", "销售部", "人力资源部", "法律事务部"]
_RISK_KEYS = ["付款风险", "违约风险", "知识产权风险", "合同风险", "风险"]


class EntityExtractor:
    """实体关系抽取器。"""

    def extract(self, text: str) -> Tuple[List[dict], List[dict]]:
        if settings.USE_MOCK or settings.LLM_PROVIDER == "mock":
            return self._rule_extract(text)
        return self._llm_extract(text)

    def _rule_extract(self, text: str) -> Tuple[List[dict], List[dict]]:
        entities: List[dict] = []
        relations: List[dict] = []

        def find_entities(keys, label):
            found = []
            for k in keys:
                if k in text:
                    found.append({"name": k, "type": label})
            return found

        contracts = find_entities(_CONTRACT_KEYS, LABEL_CONTRACT)
        clauses = find_entities(_CLAUSE_KEYS, LABEL_CLAUSE)
        regulations = find_entities(_REGULATION_KEYS, LABEL_REGULATION)
        processes = find_entities(_PROCESS_KEYS, LABEL_PROCESS)
        departments = find_entities(_DEPARTMENT_KEYS, LABEL_DEPARTMENT)
        risks = find_entities(_RISK_KEYS, LABEL_RISK)

        entities = contracts + clauses + regulations + processes + departments + risks

        # 规则关系
        for c in contracts:
            for p in processes:
                if "审核" in p["name"] or "审批" in p["name"]:
                    relations.append({"subject": c["name"], "relation": "NEED",
                                      "object": p["name"]})
        for p in processes:
            for d in departments:
                relations.append({"subject": p["name"], "relation": "HANDLED_BY",
                                  "object": d["name"]})
        for cl in clauses:
            for r in risks:
                relations.append({"subject": cl["name"], "relation": "LEADS_TO",
                                  "object": r["name"]})

        return entities, relations

    def _llm_extract(self, text: str) -> Tuple[List[dict], List[dict]]:
        from app.llm.client import get_llm

        prompt = f"""
请从以下法务文本中抽取实体与关系，返回 JSON。
实体类型限定：ContractType/Clause/Regulation/Process/Department/Risk。
关系类型限定：NEED/HANDLED_BY/LEADS_TO/CONTAINS/REFERENCES。
输出格式：
{{"entities":[{{"name":"...","type":"..."}}],"relations":[{{"subject":"...","relation":"...","object":"..."}}]}}

文本：
{text}
"""
        try:
            raw = get_llm().chat(
                [{"role": "user", "content": prompt}], json_mode=True
            )
            data = json.loads(raw)
            return data.get("entities", []), data.get("relations", [])
        except Exception as e:
            logger.error("entity extract failed: %s", e)
            return [], []
