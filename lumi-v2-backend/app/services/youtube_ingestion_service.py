from datetime import datetime, timezone
from re import search as re_search
from uuid import uuid4

from fastapi import HTTPException, status
from loguru import logger
from sentence_transformers import SentenceTransformer
from youtube_transcript_api import YouTubeTranscriptApi

from app.core.config import get_settings
from app.integrations.qdrant import upsert_points
from app.integrations.supabase import upload_file_to_storage

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

_embedding_model: SentenceTransformer | None = None


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        settings = get_settings()
        _embedding_model = SentenceTransformer(settings.embedding_model_name)
    return _embedding_model


def _extract_video_id(youtube_url: str) -> str:
    """Extract video ID from YouTube URL (handles various URL formats)."""
    patterns = [
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
    ]
    
    for pattern in patterns:
        match = re_search(pattern, youtube_url)
        if match:
            return match.group(1)
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid YouTube URL format. Use formats like: https://www.youtube.com/watch?v=VIDEO_ID or https://youtu.be/VIDEO_ID",
    )


def _fetch_transcript(video_id: str) -> str:
    """Fetch transcript from YouTube video with fallback mechanism."""
    # Try youtube-transcript-api first
    try:
        logger.info("Attempting to fetch transcript via youtube-transcript-api for {}", video_id)
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([item["text"] for item in transcript_list])
        
        if not transcript_text.strip():
            raise Exception("Empty transcript returned")
        
        logger.info("Successfully fetched transcript via youtube-transcript-api ({} chars)", len(transcript_text))
        return transcript_text.strip()
    except Exception as exc:
        logger.warning("youtube-transcript-api failed for {}: {}. Trying yt-dlp fallback.", video_id, exc)
        
        # Fallback to yt-dlp
        if yt_dlp is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch YouTube transcript. yt-dlp fallback not available.",
            ) from exc
        
        try:
            logger.info("Attempting to fetch transcript via yt-dlp for {}", video_id)
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "write_auto_sub": True,
                "skip_download": True,
                "writesubtitles": True,
                "subtitlesformat": "vtt",
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                
                # Try to get captions
                if info.get("subtitles"):
                    # Prefer English captions
                    captions = info["subtitles"].get("en") or info["subtitles"].get("en-US")
                    if not captions:
                        # Fall back to any available caption
                        captions = next(iter(info["subtitles"].values()), None)
                    
                    if captions:
                        # Extract text from VTT captions
                        transcript_text = ""
                        for caption in captions:
                            if isinstance(caption, dict) and "text" in caption:
                                transcript_text += caption["text"] + " "
                            elif isinstance(caption, str):
                                # Simple string parsing for VTT format
                                lines = caption.split("\n")
                                for line in lines:
                                    if line and not line.startswith("[") and "-->" not in line:
                                        transcript_text += line + " "
                        
                        if transcript_text.strip():
                            logger.info("Successfully fetched transcript via yt-dlp ({} chars)", len(transcript_text))
                            return transcript_text.strip()
            
            raise Exception("No captions found via yt-dlp")
        except HTTPException:
            raise
        except Exception as dlp_exc:
            logger.exception("yt-dlp fallback also failed for {}: {}", video_id, dlp_exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch YouTube transcript via both methods. Video may not have captions available.",
            ) from dlp_exc


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks."""
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


def ingest_youtube_video(
    youtube_url: str, user_id: str
) -> dict[str, str | int]:
    """Ingest YouTube video transcript: extract → chunk → embed → store."""
    settings = get_settings()
    
    # Extract video ID
    video_id = _extract_video_id(youtube_url)
    logger.info("Extracted video ID: {}", video_id)
    
    # Fetch transcript
    transcript_text = _fetch_transcript(video_id)
    logger.info("Fetched transcript ({} chars) for video {}", len(transcript_text), video_id)
    
    # Chunk transcript
    chunks = _chunk_text(
        transcript_text, settings.chunk_size_chars, settings.chunk_overlap_chars
    )
    
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to generate chunks from YouTube transcript.",
        )
    
    logger.info("Generated {} chunks from transcript", len(chunks))
    
    # Embed chunks
    embedding_model = _get_embedding_model()
    vectors = embedding_model.encode(chunks, normalize_embeddings=True).tolist()
    
    # Generate IDs and metadata
    document_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    
    # Store raw transcript to Supabase Storage
    storage_path = f"users/{user_id}/youtube/{document_id}/transcript.txt"
    try:
        upload_file_to_storage(transcript_text.encode("utf-8"), storage_path)
        logger.info("Uploaded transcript to storage: {}", storage_path)
    except Exception as exc:
        logger.exception("Failed to upload transcript to storage: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to store transcript in storage.",
        ) from exc
    
    # Prepare points for Qdrant
    points = []
    for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
        points.append(
            {
                "id": str(uuid4()),
                "vector": vector,
                "payload": {
                    "user_id": user_id,
                    "filename": f"youtube_{video_id}",
                    "document_id": document_id,
                    "created_at": created_at,
                    "chunk_index": index,
                    "is_deleted": False,
                    "deleted_at": None,
                    "storage_path": storage_path,
                    "source_type": "youtube",
                    "video_id": video_id,
                    "source_url": youtube_url,
                    "text": chunk,
                },
            }
        )
    
    # Upsert to Qdrant
    try:
        upsert_points(points)
        logger.info("Upserted {} points to Qdrant for video {}", len(points), video_id)
    except Exception as exc:
        logger.exception("Failed to upsert vectors for YouTube {}: {}", video_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to store embeddings in Qdrant.",
        ) from exc
    
    return {
        "document_id": document_id,
        "source_url": youtube_url,
        "video_id": video_id,
        "chunks_ingested": len(chunks),
        "transcript_length": len(transcript_text),
        "created_at": created_at,
        "storage_path": storage_path,
        "message": "YouTube transcript ingested successfully.",
    }
