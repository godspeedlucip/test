from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse


class BaseObjectStore:
    def put(self, content: bytes, file_name: str) -> tuple[str, str]:
        raise NotImplementedError

    def get(self, uri: str) -> bytes:
        raise NotImplementedError


class InMemoryObjectStore(BaseObjectStore):
    def __init__(self) -> None:
        self._files: dict[str, bytes] = {}

    def put(self, content: bytes, file_name: str) -> tuple[str, str]:
        document_id = str(uuid.uuid4())
        uri = f"memory://object-store/{document_id}/{file_name}"
        self._files[uri] = content
        checksum = hashlib.sha256(content).hexdigest()
        return uri, checksum

    def get(self, uri: str) -> bytes:
        return self._files[uri]


class FileObjectStore(BaseObjectStore):
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or (Path.cwd() / ".artifacts" / "object_store")).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, content: bytes, file_name: str) -> tuple[str, str]:
        document_id = str(uuid.uuid4())
        path = self.root / document_id / Path(file_name).name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        checksum = hashlib.sha256(content).hexdigest()
        return path.resolve().as_uri(), checksum

    def get(self, uri: str) -> bytes:
        parsed = urlparse(uri)
        if parsed.scheme == "file":
            path = Path(unquote(parsed.path))
            if os.name == "nt" and path.as_posix().startswith("/") and len(path.as_posix()) > 2 and path.as_posix()[2] == ":":
                path = Path(path.as_posix().lstrip("/"))
        else:
            path = Path(uri)
        return path.read_bytes()


class HybridObjectStore(BaseObjectStore):
    def __init__(self, primary: BaseObjectStore, fallback: BaseObjectStore) -> None:
        self.primary = primary
        self.fallback = fallback

    def put(self, content: bytes, file_name: str) -> tuple[str, str]:
        try:
            return self.primary.put(content, file_name)
        except Exception:
            return self.fallback.put(content, file_name)

    def get(self, uri: str) -> bytes:
        try:
            return self.primary.get(uri)
        except Exception:
            return self.fallback.get(uri)


object_store: BaseObjectStore | None = None


def build_object_store() -> BaseObjectStore:
    mode = os.getenv("OBJECT_STORE_PROVIDER", os.getenv("OBJECT_STORE_MODE", "local")).lower()
    if mode in {"real", "local"}:
        return FileObjectStore(root=os.getenv("OBJECT_STORE_ROOT"))
    if mode == "hybrid":
        return HybridObjectStore(primary=FileObjectStore(root=os.getenv("OBJECT_STORE_ROOT")), fallback=InMemoryObjectStore())
    return InMemoryObjectStore()


def get_object_store() -> BaseObjectStore:
    global object_store
    if object_store is None:
        object_store = build_object_store()
    return object_store
