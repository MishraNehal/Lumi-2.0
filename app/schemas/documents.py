from pydantic import BaseModel


class DocumentItem(BaseModel):
    document_id: str
    filename: str
    created_at: str
    chunks_count: int
    is_deleted: bool = False
    deleted_at: str = ""


class DocumentListResponse(BaseModel):
    documents: list[DocumentItem]
    total: int
    page: int
    page_size: int
    has_next: bool


class DeleteDocumentResponse(BaseModel):
    document_id: str
    deleted_chunks: int
    message: str


class ReprocessDocumentResponse(BaseModel):
    job_id: str
    document_id: str
    status: str
    requested_at: str
    message: str
