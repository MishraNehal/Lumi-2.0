from fastapi import APIRouter, Depends, File, UploadFile

from app.core.security import get_current_user
from app.schemas.upload import UploadResponse
from app.services.ingestion_service import ingest_file

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.get("/status")
def upload_status() -> dict[str, str]:
    return {"module": "upload", "status": "ready"}


@router.post("/file", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict[str, str | None] = Depends(get_current_user),
) -> UploadResponse:
    content = await file.read()
    result = ingest_file(
        file_name=file.filename or "uploaded-file",
        file_bytes=content,
        user_id=current_user["id"] or "",
    )
    return UploadResponse(**result)
