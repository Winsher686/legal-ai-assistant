"""向量数据库客户端封装（Milvus + Mock 降级）。

生产环境：连接 Milvus。
本地/无服务器环境：USE_MOCK=true 时使用内存向量库（余弦相似度），
接口与 Milvus 一致，实现端到端逻辑验证。
"""
import math
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logger import logger

SCHEMA_FIELDS = {
    "id": "pk",
    "embedding": "vector",
    "content": "text",
    "document_id": "text",
    "document_name": "text",
    "document_type": "text",
    "chapter": "text",
    "article": "text",
    "page": "int",
    "version": "text",
}


class InMemoryVectorStore:
    """内存向量库（Mock）。"""

    def __init__(self):
        self._vectors: List[Dict[str, Any]] = []

    def connect(self):
        return self

    def create_collection(self):
        return

    def insert(self, vectors: List[Dict[str, Any]]) -> None:
        self._vectors.extend(vectors)

    def search(self, query_vector: List[float], top_k: int,
               filter_expr: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for item in self._vectors:
            v = item.get("embedding")
            if not v:
                continue
            score = self._cosine(query_vector, v)
            results.append({**item, "score": score})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def count(self) -> int:
        return len(self._vectors)

    def delete_by_document(self, document_id: str) -> None:
        self._vectors = [v for v in self._vectors if v.get("document_id") != document_id]


class MilvusVectorStore:
    """Milvus 向量库。"""

    def __init__(self):
        self._client = None
        self._collection = None

    def connect(self):
        try:
            from pymilvus import Collection, connections, utility

            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
            )
            if not utility.has_collection(settings.MILVUS_COLLECTION):
                self._create_collection()
            self._collection = Collection(settings.MILVUS_COLLECTION)
            self._collection.load()
            logger.info("milvus connected, collection=%s", settings.MILVUS_COLLECTION)
        except Exception as e:
            logger.warning("milvus connect failed: %s", e)
        return self

    def _create_collection(self):
        from pymilvus import CollectionSchema, DataType, FieldSchema, utility

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=128),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=settings.EMBEDDING_DIM),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="document_name", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="document_type", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="chapter", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="article", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="page", dtype=DataType.INT64),
            FieldSchema(name="version", dtype=DataType.VARCHAR, max_length=64),
        ]
        schema = CollectionSchema(fields, description="legal knowledge base")
        from pymilvus import Collection

        Collection(name=settings.MILVUS_COLLECTION, schema=schema)

    def insert(self, vectors: List[Dict[str, Any]]) -> None:
        if not vectors or self._collection is None:
            return
        self._collection.insert(vectors)
        self._collection.flush()

    def search(self, query_vector: List[float], top_k: int,
               filter_expr: Optional[str] = None) -> List[Dict[str, Any]]:
        if self._collection is None:
            return []
        from pymilvus import AnnSearchRequest

        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        output_fields = [
            "id", "content", "document_id", "document_name", "document_type",
            "chapter", "article", "page", "version",
        ]
        res = self._collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=output_fields,
        )
        results = []
        for hits in res:
            for hit in hits:
                results.append({**hit.entity._row_data, "score": hit.distance})
        return results

    def count(self) -> int:
        if self._collection is None:
            return 0
        return self._collection.num_entities

    def delete_by_document(self, document_id: str) -> None:
        if self._collection is None:
            return
        self._collection.delete(f'document_id == "{document_id}"')


class VectorStore:
    """统一入口：根据配置选择后端。"""

    def __init__(self):
        if settings.USE_MOCK:
            self._backend = InMemoryVectorStore()
        else:
            self._backend = MilvusVectorStore()
        self._backend.connect()

    @property
    def backend(self):
        return self._backend

    def insert(self, vectors: List[Dict[str, Any]]) -> None:
        self._backend.insert(vectors)

    def search(self, query_vector: List[float], top_k: int,
               filter_expr: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._backend.search(query_vector, top_k, filter_expr)

    def delete_by_document(self, document_id: str) -> None:
        self._backend.delete_by_document(document_id)


_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
