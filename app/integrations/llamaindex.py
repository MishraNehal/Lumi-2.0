from functools import lru_cache

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from loguru import logger

from app.core.config import get_settings
from app.integrations.qdrant import get_qdrant_client


@lru_cache
def get_qdrant_vector_store() -> QdrantVectorStore:
    settings = get_settings()
    client = get_qdrant_client()

    return QdrantVectorStore(
        client=client,
        collection_name=settings.qdrant_collection_name,
    )


@lru_cache
def get_storage_context() -> StorageContext:
    vector_store = get_qdrant_vector_store()
    return StorageContext.from_defaults(vector_store=vector_store)


@lru_cache
def get_embedding_model() -> HuggingFaceEmbedding:
    settings = get_settings()
    return HuggingFaceEmbedding(model_name=settings.embedding_model_name)


def get_vector_index() -> VectorStoreIndex:
    vector_store = get_qdrant_vector_store()
    embedding_model = get_embedding_model()
    return VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=embedding_model,
    )


def llamaindex_healthcheck() -> dict[str, str]:
    try:
        get_storage_context()
        get_vector_index()
        return {"status": "ok", "detail": "storage_context_ready"}
    except Exception as exc:
        logger.warning("LlamaIndex health check failed: {}", exc)
        return {"status": "error", "detail": str(exc)}
