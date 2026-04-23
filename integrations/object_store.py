from __future__ import annotations

import hashlib
import uuid


class InMemoryObjectStore:
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


object_store = InMemoryObjectStore()


def get_object_store() -> InMemoryObjectStore:
    return object_store
