from functools import lru_cache

from fastapi import HTTPException, status
from loguru import logger
from supabase import Client, create_client

from app.core.config import get_settings

STORAGE_BUCKET_NAME = "lumi-documents"


@lru_cache
def get_supabase_client() -> Client:
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase config missing. Set SUPABASE_URL and SUPABASE_ANON_KEY in .env.",
        )

    try:
        return create_client(settings.supabase_url, settings.supabase_anon_key)
    except Exception as exc:
        logger.exception("Failed to create Supabase client: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to initialize Supabase client.",
        ) from exc


def ensure_storage_bucket() -> None:
    """Ensure the storage bucket exists, create if needed. Non-critical on startup."""
    try:
        client = get_supabase_client()
        buckets = client.storage.list_buckets()
        bucket_names = [b.name for b in buckets]
        
        if STORAGE_BUCKET_NAME not in bucket_names:
            logger.info("Creating storage bucket: {}", STORAGE_BUCKET_NAME)
            client.storage.create_bucket(STORAGE_BUCKET_NAME)
            logger.info("Storage bucket created successfully")
        else:
            logger.info("Storage bucket already exists")
    except Exception as exc:
        logger.warning("Storage bucket initialization failed (non-critical): {}", exc)


def upload_file_to_storage(file_bytes: bytes, storage_path: str) -> str:
    """Upload file bytes to Supabase Storage and return the storage path."""
    try:
        client = get_supabase_client()
        client.storage.from_(STORAGE_BUCKET_NAME).upload(
            file=file_bytes,
            path=storage_path,
            file_options={"upsert": True},
        )
        return storage_path
    except Exception as exc:
        logger.exception("Failed to upload file to storage at {}: {}", storage_path, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to store file in storage.",
        ) from exc
