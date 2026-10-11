"""文档处理 Pipeline：解析 → 清洗 → 切片 → Embedding → Milvus + Neo4j。"""
import uuid
from typing import Dict, List, Optional

from app.core.logger import logger
from app.document.cleaner import TextCleaner
from app.document.parser import DocumentParser
from app.document.splitter import LegalSplitter
from app.graph.extractor import EntityExtractor
from app.graph.graph_store import get_graph_store
from app.rag.embedding import get_embedding
from app.rag.hybrid_search import get_bm25_retriever
from app.rag.vector_store import get_vector_store


class DocumentPipeline:
    """统一文档处理流程。"""

    def __init__(self):
        self.parser = DocumentParser()
        self.cleaner = TextCleaner()
        self.splitter = LegalSplitter()
        self.extractor = EntityExtractor()

    def process(self, file_path: str, document_id: str, document_name: str,
                document_type: str, version: str) -> Dict:
        """执行完整入库流程，返回统计信息。"""
        logger.info("processing document %s (%s)", document_name, document_id)

        # 1. 解析
        pages = self.parser.parse(file_path)
        if not pages:
            return {"status": "failed", "error": "parse empty"}

        # 2. 清洗 + 3. 切片
        cleaned_pages = [(p, self.cleaner.clean(t)) for p, t in pages]
        chunks = self.splitter.split(cleaned_pages)
        logger.info("document %s -> %d chunks", document_name, len(chunks))

        # 4. Embedding + Milvus 入库
        vector_store = get_vector_store()
        embedding = get_embedding()

        vectors = []
        for idx, ch in enumerate(chunks):
            vec = embedding.encode(ch.content)
            vector_id = f"{document_id}_{idx}"
            vectors.append({
                "id": vector_id,
                "embedding": vec,
                "content": ch.content,
                "document_id": document_id,
                "document_name": document_name,
                "document_type": document_type,
                "chapter": ch.chapter,
                "article": ch.article,
                "page": ch.page,
                "version": version,
            })

        vector_store.insert(vectors)

        # 5. 同步 BM25 关键词索引（供混合检索 RRF 融合使用）
        get_bm25_retriever().add(vectors)

        # 6. 实体关系抽取 + Neo4j 入库
        graph_store = get_graph_store()
        graph_store.upsert_node("Document", document_name,
                                {"type": document_type, "version": version})
        for ch in chunks:
            entities, relations = self.extractor.extract(ch.content)
            for e in entities:
                graph_store.upsert_node(e["type"], e["name"])
                # Document 包含实体（条款等）
                if e["type"] == "Clause":
                    graph_store.add_relation("Document", document_name, "CONTAINS",
                                             "Clause", e["name"])
            for r in relations:
                # 标准化关系，映射到节点类型
                sub_label = self._guess_label(r["subject"])
                obj_label = self._guess_label(r["object"])
                if sub_label and obj_label:
                    graph_store.add_relation(sub_label, r["subject"], r["relation"],
                                             obj_label, r["object"])

        return {
            "status": "completed",
            "chunk_count": len(chunks),
            "vector_count": len(vectors),
            "document_id": document_id,
        }

    def _guess_label(self, name: str) -> Optional[str]:
        """根据名称推断节点类型（用于关系入库）。"""
        for k in ["采购合同", "销售合同", "技术服务合同", "劳动合同", "合同"]:
            if k in name:
                return "ContractType"
        for k in ["法务部", "财务部", "采购部", "销售部", "人力资源部", "法律事务部"]:
            if k in name:
                return "Department"
        for k in ["风险"]:
            if k in name:
                return "Risk"
        for k in ["审核", "审批", "流程"]:
            if k in name:
                return "Process"
        for k in ["法", "民法典", "公司法"]:
            if k in name:
                return "Regulation"
        for k in ["条款"]:
            if k in name:
                return "Clause"
        return None
