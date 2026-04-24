from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import unquote, urlparse

from domain.observability import CheckpointState


class CheckpointStore(Protocol):
    def save(self, *, trace_id: str, node_name: str, state: dict[str, Any]) -> CheckpointState:
        ...

    def list_by_trace(self, trace_id: str) -> list[CheckpointState]:
        ...

    def load(self, serialized_state_uri: str) -> dict[str, Any] | None:
        ...

    def load_checkpoint(self, checkpoint_id: str) -> dict[str, Any] | None:
        ...

    def get_checkpoint(self, checkpoint_id: str) -> CheckpointState | None:
        ...

    def clear(self) -> None:
        ...


@dataclass
class InMemoryCheckpointStore:
    _state_by_uri: dict[str, dict[str, Any]] = field(default_factory=dict)
    _checkpoints_by_trace: dict[str, list[CheckpointState]] = field(default_factory=dict)
    _checkpoint_by_id: dict[str, CheckpointState] = field(default_factory=dict)

    def save(self, *, trace_id: str, node_name: str, state: dict[str, Any]) -> CheckpointState:
        checkpoint_id = str(uuid.uuid4())
        uri = f"memory://checkpoints/{checkpoint_id}.json"
        self._state_by_uri[uri] = dict(state)
        cp = CheckpointState(
            checkpoint_id=checkpoint_id,
            trace_id=trace_id,
            node_name=node_name,
            serialized_state_uri=uri,
            created_at_ms=int(time.time() * 1000),
        )
        self._checkpoints_by_trace.setdefault(trace_id, []).append(cp)
        self._checkpoint_by_id[checkpoint_id] = cp
        return cp

    def list_by_trace(self, trace_id: str) -> list[CheckpointState]:
        return list(self._checkpoints_by_trace.get(trace_id, []))

    def load(self, serialized_state_uri: str) -> dict[str, Any] | None:
        snapshot = self._state_by_uri.get(serialized_state_uri)
        return dict(snapshot) if snapshot is not None else None

    def load_checkpoint(self, checkpoint_id: str) -> dict[str, Any] | None:
        cp = self._checkpoint_by_id.get(checkpoint_id)
        if cp is None:
            return None
        return self.load(cp.serialized_state_uri)

    def get_checkpoint(self, checkpoint_id: str) -> CheckpointState | None:
        cp = self._checkpoint_by_id.get(checkpoint_id)
        return CheckpointState.model_validate(cp.model_dump()) if cp is not None else None

    def clear(self) -> None:
        self._state_by_uri.clear()
        self._checkpoints_by_trace.clear()
        self._checkpoint_by_id.clear()


class FileCheckpointStore:
    def __init__(self, root_dir: str | Path | None = None) -> None:
        self.root = Path(root_dir or (Path.cwd() / ".artifacts" / "checkpoints")).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self._index = self._load_index()

    def _load_index(self) -> dict[str, Any]:
        if self.index_path.exists():
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        return {"by_trace": {}, "by_id": {}}

    def _flush_index(self) -> None:
        self.index_path.write_text(json.dumps(self._index, ensure_ascii=False, indent=2), encoding="utf-8")

    def _checkpoint_dir(self, trace_id: str) -> Path:
        path = self.root / trace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save(self, *, trace_id: str, node_name: str, state: dict[str, Any]) -> CheckpointState:
        checkpoint_id = str(uuid.uuid4())
        cp_dir = self._checkpoint_dir(trace_id)
        state_path = cp_dir / f"{checkpoint_id}.json"
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        cp = CheckpointState(
            checkpoint_id=checkpoint_id,
            trace_id=trace_id,
            node_name=node_name,
            serialized_state_uri=state_path.resolve().as_uri(),
            created_at_ms=int(time.time() * 1000),
        )
        self._index["by_trace"].setdefault(trace_id, []).append(cp.model_dump())
        self._index["by_id"][checkpoint_id] = cp.model_dump()
        self._flush_index()
        return cp

    def list_by_trace(self, trace_id: str) -> list[CheckpointState]:
        return [CheckpointState.model_validate(x) for x in self._index.get("by_trace", {}).get(trace_id, [])]

    def load(self, serialized_state_uri: str) -> dict[str, Any] | None:
        parsed = urlparse(serialized_state_uri)
        if parsed.scheme == "file":
            path = Path(unquote(parsed.path))
            if os.name == "nt" and path.as_posix().startswith("/") and len(path.as_posix()) > 2 and path.as_posix()[2] == ":":
                path = Path(path.as_posix().lstrip("/"))
        else:
            path = Path(serialized_state_uri)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def load_checkpoint(self, checkpoint_id: str) -> dict[str, Any] | None:
        cp = self.get_checkpoint(checkpoint_id)
        if cp is None:
            return None
        return self.load(cp.serialized_state_uri)

    def get_checkpoint(self, checkpoint_id: str) -> CheckpointState | None:
        raw = self._index.get("by_id", {}).get(checkpoint_id)
        if raw is None:
            return None
        return CheckpointState.model_validate(raw)

    def clear(self) -> None:
        if self.root.exists():
            for child in self.root.glob("**/*"):
                if child.is_file():
                    child.unlink(missing_ok=True)
            for child in sorted(self.root.glob("**/*"), reverse=True):
                if child.is_dir():
                    child.rmdir()
        self.root.mkdir(parents=True, exist_ok=True)
        self._index = {"by_trace": {}, "by_id": {}}
        self._flush_index()


checkpoint_store: CheckpointStore | None = None


def build_checkpoint_store() -> CheckpointStore:
    mode = os.getenv("CHECKPOINT_STORE_MODE", "memory").lower()
    if mode in {"file", "local"}:
        return FileCheckpointStore(root_dir=os.getenv("CHECKPOINT_STORE_ROOT"))
    return InMemoryCheckpointStore()


def get_checkpoint_store() -> CheckpointStore:
    global checkpoint_store
    if checkpoint_store is None:
        checkpoint_store = build_checkpoint_store()
    return checkpoint_store
