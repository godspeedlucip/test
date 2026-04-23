from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "research_agent"
    provider_mode: str = "mock"


settings = Settings()
