from fastapi import APIRouter, Depends, status

from app.core.security import get_current_user
from app.schemas.youtube import YouTubeIngestRequest, YouTubeIngestResponse
from app.services.youtube_ingestion_service import ingest_youtube_video

router = APIRouter(prefix="/youtube", tags=["YouTube"])


@router.get("/status")
def youtube_status() -> dict[str, str]:
    return {"module": "youtube", "status": "active"}


@router.post("/ingest", response_model=YouTubeIngestResponse, status_code=201)
async def ingest_youtube(
    request: YouTubeIngestRequest,
    current_user: dict = Depends(get_current_user),
) -> YouTubeIngestResponse:
    """
    Ingest YouTube video transcript:
    - Extract transcript from video
    - Chunk and embed
    - Store in Qdrant with user isolation
    - Store raw transcript in Supabase Storage
    """
    result = ingest_youtube_video(str(request.youtube_url), current_user["id"])
    return YouTubeIngestResponse(**result)
