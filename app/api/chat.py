from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.chat import ChatAskRequest, ChatAskResponse
from app.services.rag_service import ask_question

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/status")
def chat_status() -> dict[str, str]:
    return {"module": "chat", "status": "ready"}


@router.post("/ask", response_model=ChatAskResponse)
def chat_ask(
    payload: ChatAskRequest,
    current_user: dict[str, str | None] = Depends(get_current_user),
) -> ChatAskResponse:
    result = ask_question(question=payload.question, user_id=current_user["id"] or "")
    return ChatAskResponse(**result)
