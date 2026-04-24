from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user
from app.integrations.qdrant import (
    delete_user_document,
    list_user_documents,
    soft_delete_user_document,
)
from app.schemas.documents import (
    DeleteDocumentResponse,
    DocumentItem,
    DocumentListResponse,
    ReprocessDocumentResponse,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/status")
def documents_status() -> dict[str, str]:
    return {"module": "documents", "status": "ready"}


@router.get("/", response_model=DocumentListResponse)
def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    include_deleted: bool = Query(default=False),
    current_user: dict[str, str | None] = Depends(get_current_user),
) -> DocumentListResponse:
    user_id = current_user["id"] or ""
    docs = list_user_documents(user_id=user_id, include_deleted=include_deleted)

    total = len(docs)
    start = (page - 1) * page_size
    end = start + page_size
    page_docs = docs[start:end]

    items = [DocumentItem(**doc) for doc in page_docs]
    has_next = end < total
    return DocumentListResponse(
        documents=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=has_next,
    )


@router.delete("/{document_id}", response_model=DeleteDocumentResponse)
def delete_document(
    document_id: str,
    hard_delete: bool = Query(default=False),
    current_user: dict[str, str | None] = Depends(get_current_user),
) -> DeleteDocumentResponse:
    user_id = current_user["id"] or ""
    if hard_delete:
        deleted_chunks = delete_user_document(user_id=user_id, document_id=document_id)
    else:
        deleted_chunks = soft_delete_user_document(user_id=user_id, document_id=document_id)

    if deleted_chunks == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found for this user.",
        )

    return DeleteDocumentResponse(
        document_id=document_id,
        deleted_chunks=deleted_chunks,
        message=(
            "Document hard deleted successfully."
            if hard_delete
            else "Document soft deleted successfully."
        ),
    )


@router.post("/{document_id}/reprocess", response_model=ReprocessDocumentResponse)
def reprocess_document_placeholder(
    document_id: str,
    current_user: dict[str, str | None] = Depends(get_current_user),
) -> ReprocessDocumentResponse:
    _ = current_user
    return ReprocessDocumentResponse(
        job_id=str(uuid4()),
        document_id=document_id,
        status="queued",
        requested_at=datetime.now(timezone.utc).isoformat(),
        message="Reprocess queued as placeholder; execution pipeline will be implemented later.",
    )
