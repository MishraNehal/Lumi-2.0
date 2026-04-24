from pydantic import BaseModel


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_ingested: int
    created_at: str
    storage_path: str
    message: str
