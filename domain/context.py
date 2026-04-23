from pydantic import BaseModel


class RequestContext(BaseModel):
    user_id: str
    project_id: str | None = None
    conversation_id: str | None = None
    task_id: str | None = None
    session_id: str | None = None
    request_id: str | None = None
