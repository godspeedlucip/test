from __future__ import annotations

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "research_agent"
    provider_mode: str = "mock"
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False


settings = Settings()
