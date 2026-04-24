from fastapi import FastAPI
from loguru import logger

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.upload import router as upload_router
from app.api.website import router as website_router
from app.api.youtube import router as youtube_router
from app.core.config import get_settings
from app.core.logger import configure_logging
from app.integrations.llamaindex import llamaindex_healthcheck
from app.integrations.qdrant import bootstrap_qdrant, qdrant_healthcheck
from app.integrations.supabase import ensure_storage_bucket

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(upload_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(documents_router, prefix=settings.api_prefix)
app.include_router(youtube_router, prefix=settings.api_prefix)
app.include_router(website_router, prefix=settings.api_prefix)


@app.on_event("startup")
def on_startup() -> None:
    qdrant_bootstrap_result = bootstrap_qdrant()
    logger.info("Startup Qdrant bootstrap result: {}", qdrant_bootstrap_result)
    
    try:
        ensure_storage_bucket()
        logger.info("Storage bucket initialized successfully")
    except Exception as exc:
        logger.warning("Storage bucket initialization skipped: {}", exc)


@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@app.get("/health", tags=["System"])
def health() -> dict[str, object]:
    qdrant_status = qdrant_healthcheck()
    llamaindex_status = llamaindex_healthcheck()
    overall_status = "ok"
    if qdrant_status["status"] != "ok" or llamaindex_status["status"] != "ok":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "integrations": {
            "qdrant": qdrant_status,
            "llamaindex": llamaindex_status,
        },
    }


@app.get("/health/integrations", tags=["System"])
def integration_health() -> dict[str, dict[str, str]]:
    return {
        "qdrant": qdrant_healthcheck(),
        "llamaindex": llamaindex_healthcheck(),
    }
