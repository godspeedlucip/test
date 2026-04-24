from __future__ import annotations

import json
import math
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from integrations.embed_client import get_embed_client


@dataclass
class VectorItem:
    chunk_id: str
    text: str
    metadata: dict
    vector: list[float] | None = None


class BaseVectorStore:
    def upsert_chunks(self, index_name: str, chunks: list[VectorItem]) -> None:
        raise NotImplementedError

    def query(self, index_name: str, query: str, top_k: int = 5) -> list[VectorItem]:
        raise NotImplementedError


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _lexical_overlap_score(query: str, text: str) -> float:
    q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    if not q_tokens:
        return 0.0
    t_tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    if not t_tokens:
        return 0.0
    overlap = len(q_tokens.intersection(t_tokens))
    return overlap / max(1, len(q_tokens))


class InMemoryVectorStore(BaseVectorStore):
    def __init__(self) -> None:
        self._index: dict[str, dict[str, VectorItem]] = {}

    def upsert_chunks(self, index_name: str, chunks: list[VectorItem]) -> None:
        bucket = self._index.setdefault(index_name, {})
        for chunk in chunks:
            bucket[chunk.chunk_id] = chunk

    def query(self, index_name: str, query: str, top_k: int = 5) -> list[VectorItem]:
        bucket = self._index.get(index_name, {})
        if not bucket:
            return []
        qvec = get_embed_client().embed(query)
        scored: list[tuple[float, VectorItem]] = []
        for item in bucket.values():
            semantic = _cosine_similarity(qvec, item.vector or [])
            lexical = _lexical_overlap_score(query, item.text)
            score = semantic + 0.15 * lexical
            enriched = VectorItem(
                chunk_id=item.chunk_id,
                text=item.text,
                vector=item.vector,
                metadata={**item.metadata, "_score": round(score, 6)},
            )
            scored.append((score, enriched))
        scored.sort(key=lambda pair: (-pair[0], pair[1].chunk_id))
        return [item for _, item in scored[:top_k]]


class FileVectorStore(BaseVectorStore):
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or (Path.cwd() / ".artifacts" / "vector_store")).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._mem = InMemoryVectorStore()
        self._loaded_indexes: set[str] = set()

    def _index_path(self, index_name: str) -> Path:
        safe = index_name.replace("/", "_")
        return self.root / f"{safe}.json"

    def _ensure_loaded(self, index_name: str) -> None:
        if index_name in self._loaded_indexes:
            return
        path = self._index_path(index_name)
        if path.exists():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self._mem.upsert_chunks(index_name, [VectorItem(**row) for row in loaded])
        self._loaded_indexes.add(index_name)

    def upsert_chunks(self, index_name: str, chunks: list[VectorItem]) -> None:
        self._ensure_loaded(index_name)
        self._mem.upsert_chunks(index_name, chunks)
        path = self._index_path(index_name)
        full_items = self._mem.query(index_name, query="", top_k=100_000)
        sanitized = []
        for item in full_items:
            payload = asdict(item)
            payload["metadata"] = {k: v for k, v in payload["metadata"].items() if k != "_score"}
            sanitized.append(payload)
        path.write_text(json.dumps(sanitized, ensure_ascii=False, indent=2), encoding="utf-8")

    def query(self, index_name: str, query: str, top_k: int = 5) -> list[VectorItem]:
        self._ensure_loaded(index_name)
        return self._mem.query(index_name, query, top_k=top_k)


class HybridVectorStore(BaseVectorStore):
    def __init__(self, primary: BaseVectorStore, fallback: BaseVectorStore) -> None:
        self.primary = primary
        self.fallback = fallback

    def upsert_chunks(self, index_name: str, chunks: list[VectorItem]) -> None:
        try:
            self.primary.upsert_chunks(index_name, chunks)
        except Exception:
            self.fallback.upsert_chunks(index_name, chunks)

    def query(self, index_name: str, query: str, top_k: int = 5) -> list[VectorItem]:
        try:
            return self.primary.query(index_name, query, top_k=top_k)
        except Exception:
            return self.fallback.query(index_name, query, top_k=top_k)


vector_store: BaseVectorStore | None = None


def build_vector_store() -> BaseVectorStore:
    mode = os.getenv("VECTOR_STORE_PROVIDER", os.getenv("VECTOR_STORE_MODE", "local")).lower()
    if mode in {"real", "local"}:
        return FileVectorStore(root=os.getenv("VECTOR_STORE_ROOT"))
    if mode == "hybrid":
        return HybridVectorStore(primary=FileVectorStore(root=os.getenv("VECTOR_STORE_ROOT")), fallback=InMemoryVectorStore())
    return InMemoryVectorStore()


def get_vector_store() -> BaseVectorStore:
    global vector_store
    if vector_store is None:
        vector_store = build_vector_store()
    return vector_store
