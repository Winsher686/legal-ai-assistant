"""Repository 数据访问层：封装数据库操作。"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.entities import (
    ChatHistory,
    Document,
    DocumentChunk,
    DocumentPermission,
    DocumentTask,
    User,
)


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, doc: Document) -> Document:
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get(self, doc_id: str) -> Optional[Document]:
        return self.db.query(Document).filter(Document.id == doc_id).first()

    def list(self) -> List[Document]:
        return self.db.query(Document).order_by(Document.created_at.desc()).all()

    def delete(self, doc_id: str) -> None:
        doc = self.get(doc_id)
        if doc:
            self.db.delete(doc)
            self.db.commit()

    def update_status(self, doc_id: str, status: str) -> None:
        doc = self.get(doc_id)
        if doc:
            doc.status = status
            self.db.commit()


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, record: ChatHistory) -> ChatHistory:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_by_user(self, user_id: str) -> List[ChatHistory]:
        return (self.db.query(ChatHistory)
                .filter(ChatHistory.user_id == user_id)
                .order_by(ChatHistory.created_at.desc())
                .all())
