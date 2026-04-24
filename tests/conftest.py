import pytest
from pathlib import Path
from uuid import uuid4
import os

from integrations import get_checkpoint_store, get_repo
from integrations import embed_client as embed_client_module
from integrations import java_client as java_client_module
from integrations import checkpoint_store as checkpoint_store_module
from integrations import llm_client as llm_client_module
from integrations import object_store as object_store_module
from integrations import openalex_client as openalex_client_module
from integrations import trace_store as trace_store_module
from integrations import vector_store as vector_store_module
from observability.recorder import get_recorder


@pytest.fixture(autouse=True)
def reset_in_memory_state(monkeypatch):
    java_client_module.java_client = None
    llm_client_module.llm_client = None
    openalex_client_module.openalex_client = None
    embed_client_module.embed_client = None
    object_store_module.object_store = None
    vector_store_module.vector_store = None
    checkpoint_store_module.checkpoint_store = None
    trace_store_module.trace_store = None
    base_tmp = (Path.cwd() / ".test_tmp" / str(uuid4())).resolve()
    base_tmp.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OBJECT_STORE_MODE", "local")
    monkeypatch.setenv("VECTOR_STORE_MODE", "local")
    monkeypatch.setenv("CHECKPOINT_STORE_MODE", "memory")
    monkeypatch.setenv("TRACE_STORE_MODE", "memory")
    monkeypatch.setenv("EMBED_MODE", "local")
    if not os.getenv("LLM_PROVIDER_MODE"):
        monkeypatch.setenv("LLM_PROVIDER_MODE", "mock")
    if not os.getenv("ACADEMIC_PROVIDER_MODE"):
        monkeypatch.setenv("ACADEMIC_PROVIDER_MODE", "mock")
    if not os.getenv("JAVA_CLIENT_MODE"):
        monkeypatch.setenv("JAVA_CLIENT_MODE", "mock")
    monkeypatch.setenv("OBJECT_STORE_ROOT", str((base_tmp / "object_store").resolve()))
    monkeypatch.setenv("VECTOR_STORE_ROOT", str((base_tmp / "vector_store").resolve()))
    monkeypatch.setenv("CHECKPOINT_STORE_ROOT", str((base_tmp / "checkpoint_store").resolve()))
    monkeypatch.setenv("TRACE_STORE_ROOT", str((base_tmp / "trace_store").resolve()))
    repo = get_repo()
    repo.papers.clear()
    repo.documents.clear()
    repo.chunks.clear()
    repo.library.clear()
    repo.notes.clear()
    get_checkpoint_store().clear()
    get_recorder().clear()
    yield
