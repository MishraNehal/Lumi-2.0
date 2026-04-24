from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from docx import Document as DocxDocument
from fastapi import HTTPException, status
from loguru import logger
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.integrations.qdrant import upsert_points
from app.integrations.supabase import upload_file_to_storage

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
_embedding_model: SentenceTransformer | None = None


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        settings = get_settings()
        _embedding_model = SentenceTransformer(settings.embedding_model_name)
    return _embedding_model


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _extract_text_from_docx(file_bytes: bytes) -> str:
    doc = DocxDocument(BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs).strip()


def _extract_text_from_txt(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1").strip()


def _extract_text(filename: str, file_bytes: bytes) -> str:
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only PDF, DOCX, and TXT are allowed.",
        )

    try:
        if extension == ".pdf":
            text = _extract_text_from_pdf(file_bytes)
        elif extension == ".docx":
            text = _extract_text_from_docx(file_bytes)
        else:
            text = _extract_text_from_txt(file_bytes)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to parse file {}: {}", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to parse file content.",
        ) from exc

    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No extractable text found in file.",
        )
    return text


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    text_length = len(text)
    step = max(chunk_size - overlap, 1)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks


def ingest_file(file_name: str, file_bytes: bytes, user_id: str) -> dict[str, str | int]:
    settings = get_settings()
    clean_name = Path(file_name).name

    max_bytes = settings.upload_max_file_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size is {settings.upload_max_file_size_mb} MB.",
        )

    text = _extract_text(clean_name, file_bytes)
    chunks = _chunk_text(text, settings.chunk_size_chars, settings.chunk_overlap_chars)

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to generate chunks from file content.",
        )

    embedding_model = _get_embedding_model()
    vectors = embedding_model.encode(chunks, normalize_embeddings=True).tolist()

    document_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    
    # Upload raw file to Supabase Storage
    storage_path = f"users/{user_id}/documents/{document_id}/{clean_name}"
    try:
        upload_file_to_storage(file_bytes, storage_path)
        logger.info("Uploaded file to storage: {}", storage_path)
    except Exception as exc:
        logger.exception("Failed to upload file to storage: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to store raw file in storage.",
        ) from exc

    points = []
    for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
        points.append(
            {
                "id": str(uuid4()),
                "vector": vector,
                "payload": {
                    "user_id": user_id,
                    "filename": clean_name,
                    "document_id": document_id,
                    "created_at": created_at,
                    "chunk_index": index,
                    "is_deleted": False,
                    "deleted_at": None,
                    "storage_path": storage_path,
                    "text": chunk,
                },
            }
        )

    try:
        upsert_points(points)
    except Exception as exc:
        logger.exception("Failed to upsert vectors for {}: {}", clean_name, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to store embeddings in Qdrant.",
        ) from exc

    return {
        "document_id": document_id,
        "filename": clean_name,
        "chunks_ingested": len(chunks),
        "created_at": created_at,
        "storage_path": storage_path,
        "message": "File ingested successfully.",
    }
