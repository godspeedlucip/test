from __future__ import annotations

from app.config import Settings, settings
from integrations import get_llm_client, get_openalex_client, get_vector_store


def get_settings() -> Settings:
    return settings


def get_dependencies() -> dict:
    return {
        "llm_client": get_llm_client(),
        "openalex_client": get_openalex_client(),
        "vector_store": get_vector_store(),
    }
