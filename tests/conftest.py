import pytest

from integrations import get_checkpoint_store, get_repo
from integrations import java_client as java_client_module
from observability.recorder import get_recorder


@pytest.fixture(autouse=True)
def reset_in_memory_state():
    java_client_module.java_client = None
    repo = get_repo()
    repo.papers.clear()
    repo.documents.clear()
    repo.chunks.clear()
    repo.library.clear()
    repo.notes.clear()
    get_checkpoint_store().clear()
    get_recorder().events.clear()
    yield
