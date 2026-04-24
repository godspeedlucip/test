from pathlib import Path
from uuid import uuid4

from domain.context import RequestContext
from integrations import checkpoint_store as checkpoint_store_module
from integrations.checkpoint_store import get_checkpoint_store
from tools.library.tag_paper import TagPaperInput, tag_paper_tool


def test_file_checkpoint_store_roundtrip(monkeypatch):
    checkpoint_store_module.checkpoint_store = None
    base = (Path.cwd() / ".test_tmp" / str(uuid4()) / "checkpoints").resolve()
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CHECKPOINT_STORE_MODE", "file")
    monkeypatch.setenv("CHECKPOINT_STORE_ROOT", str(base))

    store = get_checkpoint_store()
    cp = store.save(trace_id="trace-cp-1", node_name="n1", state={"x": 1, "y": "ok"})
    loaded = store.load_checkpoint(cp.checkpoint_id)
    assert loaded == {"x": 1, "y": "ok"}
    listed = store.list_by_trace("trace-cp-1")
    assert listed and listed[0].checkpoint_id == cp.checkpoint_id


def test_tag_paper_is_not_fixed_true():
    ctx = RequestContext(user_id="u-tag-1", request_id="tag-req-1")
    empty = tag_paper_tool.execute(TagPaperInput(context=ctx, paper_id="p1", tags=[]))
    assert empty.success
    assert empty.data["tagged"] is False
    non_empty = tag_paper_tool.execute(TagPaperInput(context=ctx, paper_id="p1", tags=["nlp"]))
    assert non_empty.success
    assert non_empty.data["tagged"] is True
    assert "nlp" in non_empty.data["tags"]
