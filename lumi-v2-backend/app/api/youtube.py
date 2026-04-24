from fastapi import APIRouter

router = APIRouter(prefix="/youtube", tags=["YouTube"])


@router.get("/status")
def youtube_status() -> dict[str, str]:
    return {"module": "youtube", "status": "future-module"}
