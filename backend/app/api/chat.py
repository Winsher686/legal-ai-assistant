"""智能问答 API。"""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, rate_limit_dependency
from app.core.database import get_db
from app.models.entities import ChatHistory, User
from app.schemas.chat import ChatRequest, ChatResponse, SourceItem
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["问答"])

_chat_service = ChatService()


@router.post("/query", response_model=ChatResponse)
def query(req: ChatRequest, current_user: User = Depends(get_current_user),
          db=Depends(get_db), _=Depends(rate_limit_dependency)):
    result = _chat_service.ask(req.question)

    # 保存历史记录
    record = ChatHistory(
        user_id=current_user.id,
        question=req.question,
        answer=result["answer"],
        sources=result["sources"],
        confidence=int(result["confidence"] * 100),
    )
    db.add(record)
    db.commit()

    sources = [SourceItem(**s) for s in result["sources"]]
    return ChatResponse(
        answer=result["answer"],
        sources=sources,
        confidence=result["confidence"],
        intent=result["intent"],
    )


@router.get("/history")
def history(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    records = (db.query(ChatHistory)
               .filter(ChatHistory.user_id == current_user.id)
               .order_by(ChatHistory.created_at.desc())
               .limit(50)
               .all())
    return [
        {"question": r.question, "answer": r.answer,
         "sources": r.sources, "created_at": r.created_at.isoformat()}
        for r in records
    ]
