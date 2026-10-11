"""知识库查询 API（文档状态 + 图谱信息）。"""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.database import get_db
from app.graph.graph_query import GraphService
from app.models.entities import User
from app.rag.vector_store import get_vector_store

router = APIRouter(prefix="/knowledge", tags=["知识库"])


@router.get("/status")
def knowledge_status(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    try:
        vector_count = get_vector_store().backend.count()
    except Exception:
        vector_count = 0
    from app.repositories.repository import DocumentRepository

    doc_count = len(DocumentRepository(db).list())
    return {"document_count": doc_count, "vector_count": vector_count}


@router.get("/graph")
def graph_related(entity: str, current_user: User = Depends(get_current_user)):
    return GraphService().search("", entities=[entity])
