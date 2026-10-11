"""文档管理服务：上传、入库、删除。"""
import os
import shutil
import uuid

from app.core.config import settings
from app.core.logger import logger
from app.document.pipeline import DocumentPipeline
from app.models.entities import Document
from app.rag.vector_store import get_vector_store
from app.repositories.repository import DocumentRepository


class DocumentService:
    """文档管理业务逻辑。"""

    def __init__(self, db):
        self.db = db
        self.repo = DocumentRepository(db)

    def upload(self, file, document_type: str, version: str,
               run_async: bool = True) -> dict:
        """保存文件并创建处理任务。"""
        doc_id = str(uuid.uuid4())
        save_dir = settings.DOCUMENT_DIR
        os.makedirs(save_dir, exist_ok=True)

        # 保存文件
        filename = file.filename
        safe_name = os.path.basename(filename)
        file_path = os.path.join(save_dir, f"{doc_id}_{safe_name}")
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 写 PostgreSQL
        doc = Document(
            id=doc_id,
            name=safe_name,
            type=document_type,
            path=file_path,
            version=version,
            status="pending",
        )
        self.repo.create(doc)

        # 提交任务
        if run_async:
            self._dispatch_task(doc_id, file_path, safe_name, document_type, version)
        else:
            # 同步处理（本地验证）
            result = DocumentPipeline().process(
                file_path, doc_id, safe_name, document_type, version
            )
            self.repo.update_status(doc_id, result.get("status", "failed"))

        return {"document_id": doc_id, "status": doc.status}

    def _dispatch_task(self, doc_id, file_path, name, doc_type, version):
        try:
            from app.tasks.document_tasks import process_document_task

            process_document_task.delay(doc_id, file_path, name, doc_type, version)
        except Exception as e:
            # Celery 不可用时回退同步处理
            logger.warning("celery unavailable, fallback sync: %s", e)
            result = DocumentPipeline().process(file_path, doc_id, name, doc_type, version)
            self.repo.update_status(doc_id, result.get("status", "failed"))

    def delete(self, doc_id: str) -> None:
        """删除文档：PostgreSQL + Milvus + Neo4j。"""
        self.repo.delete(doc_id)
        # 清理向量
        try:
            get_vector_store().delete_by_document(doc_id)
        except Exception as e:
            logger.warning("vector delete failed: %s", e)
