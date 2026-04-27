from pydantic import BaseModel, HttpUrl


class YouTubeIngestRequest(BaseModel):
    youtube_url: HttpUrl


class YouTubeIngestResponse(BaseModel):
    document_id: str
    source_url: str
    video_id: str
    chunks_ingested: int
    transcript_length: int
    created_at: str
    storage_path: str
    message: str
