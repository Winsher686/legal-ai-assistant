"""文档处理异步任务。"""
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logger import logger
from app.document.pipeline import DocumentPipeline
from app.models.entities import Document, DocumentChunk
from app.tasks.celery_app import celery_app


def _update_status(document_id: str, status: str):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = status
            db.commit()
    finally:
        db.close()


@celery_app.task(name="document.process_document")
def process_document_task(document_id: str, file_path: str, document_name: str,
                          document_type: str, version: str):
    """后台处理文档：解析→切片→Embedding→Milvus→Neo4j。"""
    logger.info("task start: document %s", document_id)
    _update_status(document_id, "processing")
    try:
        pipeline = DocumentPipeline()
        result = pipeline.process(file_path, document_id, document_name,
                                  document_type, version)
        if result.get("status") == "failed":
            _update_status(document_id, "failed")
        else:
            _update_status(document_id, "completed")
        logger.info("task done: document %s, result=%s", document_id, result)
        return result
    except Exception as e:
        logger.exception("task failed: document %s", document_id)
        _update_status(document_id, "failed")
        return {"status": "failed", "error": str(e)}
