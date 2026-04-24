from collections.abc import Iterator
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import get_settings


@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()

    if not settings.qdrant_url or not settings.qdrant_api_key:
        raise ValueError("Qdrant configuration missing. Set QDRANT_URL and QDRANT_API_KEY.")

    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=15,
    )


def ensure_qdrant_collection() -> dict[str, str]:
    settings = get_settings()
    client = get_qdrant_client()

    collections = client.get_collections().collections
    existing_names = {collection.name for collection in collections}

    if settings.qdrant_collection_name in existing_names:
        return {"status": "exists", "collection": settings.qdrant_collection_name}

    client.create_collection(
        collection_name=settings.qdrant_collection_name,
        vectors_config=VectorParams(
            size=settings.embedding_dimension,
            distance=Distance.COSINE,
        ),
    )
    return {"status": "created", "collection": settings.qdrant_collection_name}


def ensure_qdrant_payload_indexes() -> dict[str, str]:
    settings = get_settings()
    client = get_qdrant_client()

    # Qdrant requires a payload index for efficient/allowed filtered search on these fields.
    index_fields = ["user_id", "document_id"]
    created: list[str] = []

    for field_name in index_fields:
        try:
            client.create_payload_index(
                collection_name=settings.qdrant_collection_name,
                field_name=field_name,
                field_schema="keyword",
            )
            created.append(field_name)
        except Exception as exc:
            # Safe to continue if index already exists.
            message = str(exc).lower()
            if "already exists" in message:
                continue
            raise

    if created:
        return {"status": "created", "fields": ",".join(created)}
    return {"status": "exists", "fields": "user_id,document_id"}


def bootstrap_qdrant() -> dict[str, str]:
    try:
        collection_result = ensure_qdrant_collection()
        index_result = ensure_qdrant_payload_indexes()
        logger.info(
            "Qdrant bootstrap successful: collection={}, payload_indexes={}",
            collection_result,
            index_result,
        )
        return {
            "status": "ok",
            "detail": f"collection:{collection_result['status']},indexes:{index_result['status']}",
        }
    except Exception as exc:
        logger.exception("Qdrant bootstrap failed: {}", exc)
        return {"status": "error", "detail": str(exc)}


def qdrant_healthcheck() -> dict[str, str]:
    try:
        client = get_qdrant_client()
        client.get_collections()
        return {"status": "ok", "detail": "connected"}
    except Exception as exc:
        logger.warning("Qdrant health check failed: {}", exc)
        return {"status": "error", "detail": str(exc)}


def upsert_points(points: list[dict[str, Any]]) -> None:
    if not points:
        return

    settings = get_settings()
    client = get_qdrant_client()

    qdrant_points = [
        PointStruct(id=point["id"], vector=point["vector"], payload=point["payload"])
        for point in points
    ]

    client.upsert(collection_name=settings.qdrant_collection_name, points=qdrant_points)


def _iter_user_points(user_id: str, batch_size: int = 256) -> Iterator[PointStruct]:
    settings = get_settings()
    client = get_qdrant_client()
    offset = None

    query_filter = Filter(
        must=[
            FieldCondition(
                key="user_id",
                match=MatchValue(value=user_id),
            )
        ]
    )

    while True:
        points, next_page_offset = client.scroll(
            collection_name=settings.qdrant_collection_name,
            scroll_filter=query_filter,
            with_payload=True,
            with_vectors=False,
            limit=batch_size,
            offset=offset,
        )

        if not points:
            break

        for point in points:
            yield point

        if next_page_offset is None:
            break
        offset = next_page_offset


def list_user_documents(user_id: str, include_deleted: bool = False) -> list[dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}

    for point in _iter_user_points(user_id=user_id):
        payload = point.payload or {}
        document_id = str(payload.get("document_id", ""))
        if not document_id:
            continue

        is_deleted = bool(payload.get("is_deleted", False))
        deleted_at = payload.get("deleted_at")
        if is_deleted and not include_deleted:
            continue

        if document_id not in documents:
            documents[document_id] = {
                "document_id": document_id,
                "filename": str(payload.get("filename", "unknown")),
                "created_at": str(payload.get("created_at", "")),
                "chunks_count": 0,
                "is_deleted": is_deleted,
                "deleted_at": str(deleted_at or ""),
            }
        else:
            if is_deleted and not documents[document_id]["is_deleted"]:
                documents[document_id]["is_deleted"] = True
                documents[document_id]["deleted_at"] = str(deleted_at or "")

        documents[document_id]["chunks_count"] += 1

    docs_list = list(documents.values())
    docs_list.sort(key=lambda d: d.get("created_at", ""), reverse=True)
    return docs_list


def delete_user_document(user_id: str, document_id: str) -> int:
    settings = get_settings()
    client = get_qdrant_client()

    delete_filter = Filter(
        must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="document_id", match=MatchValue(value=document_id)),
        ]
    )

    points, _ = client.scroll(
        collection_name=settings.qdrant_collection_name,
        scroll_filter=delete_filter,
        with_payload=False,
        with_vectors=False,
        limit=10000,
    )
    deleted_count = len(points)

    if deleted_count == 0:
        return 0

    client.delete(
        collection_name=settings.qdrant_collection_name,
        points_selector=FilterSelector(filter=delete_filter),
        wait=True,
    )
    return deleted_count


def soft_delete_user_document(user_id: str, document_id: str) -> int:
    settings = get_settings()
    client = get_qdrant_client()

    delete_filter = Filter(
        must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="document_id", match=MatchValue(value=document_id)),
        ]
    )

    points, _ = client.scroll(
        collection_name=settings.qdrant_collection_name,
        scroll_filter=delete_filter,
        with_payload=False,
        with_vectors=False,
        limit=10000,
    )
    affected_count = len(points)
    if affected_count == 0:
        return 0

    deleted_at = datetime.now(timezone.utc).isoformat()
    client.set_payload(
        collection_name=settings.qdrant_collection_name,
        payload={"is_deleted": True, "deleted_at": deleted_at},
        points=FilterSelector(filter=delete_filter),
        wait=True,
    )
    return affected_count
