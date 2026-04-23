from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VectorItem:
    chunk_id: str
    text: str
    metadata: dict


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._index: dict[str, list[VectorItem]] = {}

    def upsert_chunks(self, index_name: str, chunks: list[VectorItem]) -> None:
        existing = self._index.setdefault(index_name, [])
        existing.extend(chunks)

    def query(self, index_name: str, query: str, top_k: int = 5) -> list[VectorItem]:
        items = self._index.get(index_name, [])
        scored: list[tuple[float, VectorItem]] = []
        q_words = set(query.lower().split())
        for item in items:
            words = set(item.text.lower().split())
            overlap = len(q_words.intersection(words))
            score = overlap / (len(q_words) + 1)
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]


vector_store = InMemoryVectorStore()


def get_vector_store() -> InMemoryVectorStore:
    return vector_store
