from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LUMI v2"
    app_version: str = "0.1.0"
    app_env: Literal["dev", "staging", "prod"] = "dev"
    api_prefix: str = "/api/v1"
    log_level: str = Field(default="INFO")
    supabase_url: str = Field(default="", validation_alias=AliasChoices("SUPABASE_URL"))
    supabase_anon_key: str = Field(
        default="",
        validation_alias=AliasChoices("SUPABASE_ANON_KEY", "SUPABASE_KEY"),
    )
    qdrant_url: str = Field(default="", validation_alias=AliasChoices("QDRANT_URL"))
    qdrant_api_key: str = Field(default="", validation_alias=AliasChoices("QDRANT_API_KEY"))
    qdrant_collection_name: str = Field(default="lumi_documents")
    embedding_dimension: int = Field(default=384, ge=1)
    embedding_model_name: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    chunk_size_chars: int = Field(default=1000, ge=200)
    chunk_overlap_chars: int = Field(default=150, ge=0)
    upload_max_file_size_mb: int = Field(default=20, ge=1)
    groq_api_key: str = Field(default="", validation_alias=AliasChoices("GROQ_API_KEY"))
    groq_model_name: str = Field(default="llama-3.1-8b-instant")
    retrieval_top_k: int = Field(default=5, ge=1, le=20)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
