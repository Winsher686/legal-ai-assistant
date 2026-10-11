"""文档管理 API。"""
from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.entities import User
from app.schemas.chat import DocumentItem, DocumentListResponse, UploadResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/document", tags=["文档"])


@router.post("/upload", response_model=UploadResponse)
def upload(
    file: UploadFile = File(...),
    document_type: str = Form("company_policy"),
    version: str = Form("V1.0"),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = DocumentService(db).upload(file, document_type, version)
    return UploadResponse(document_id=result["document_id"], status=result["status"])


@router.get("/list", response_model=DocumentListResponse)
def list_documents(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    from app.repositories.repository import DocumentRepository

    docs = DocumentRepository(db).list()
    items = [
        DocumentItem(
            id=d.id, name=d.name, type=d.type, version=d.version,
            status=d.status, created_at=d.created_at.isoformat() if d.created_at else None,
        )
        for d in docs
    ]
    return DocumentListResponse(documents=items)


@router.delete("/{doc_id}")
def delete_document(doc_id: str, current_user: User = Depends(get_current_user),
                    db=Depends(get_db)):
    DocumentService(db).delete(doc_id)
    return {"status": "deleted"}
