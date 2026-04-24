from functools import lru_cache

from groq import Groq

from app.core.config import get_settings


@lru_cache
def get_groq_client() -> Groq:
    settings = get_settings()
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is missing in environment configuration.")
    return Groq(api_key=settings.groq_api_key)
