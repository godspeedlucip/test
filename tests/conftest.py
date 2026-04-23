import pytest

from integrations import get_repo
from observability.recorder import get_recorder


@pytest.fixture(autouse=True)
def reset_in_memory_state():
    repo = get_repo()
    repo.papers.clear()
    repo.documents.clear()
    repo.chunks.clear()
    repo.library.clear()
    repo.notes.clear()
    get_recorder().events.clear()
    yield
