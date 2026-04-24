from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from domain.context import RequestContext
from domain.runtime import RuntimeConfig
from integrations import get_embed_client, get_object_store, get_repo, get_vector_store
from integrations.vector_store import VectorItem
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result


class IndexDocumentInput(BaseModel):
    context: RequestContext
    runtime: RuntimeConfig | None = None
    document_id: str
    chunk_size: int = 1200
    chunk_overlap: int = 150
    embed_model: str = "text-embedding-3-large"


class IndexDocumentOutputData(BaseModel):
    document_id: str
    chunks_count: int
    vector_index_name: str
    index_status: Literal["completed", "partial", "failed"]


def _extract_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="ignore").strip()
    if text:
        return text
    return raw.decode("latin1", errors="ignore")


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[tuple[int, int, str]]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    size = max(200, chunk_size)
    ov = max(0, min(overlap, size // 2))
    step = max(1, size - ov)
    chunks: list[tuple[int, int, str]] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append((start, end, piece))
        if end >= len(cleaned):
            break
        start += step
    return chunks


class IndexDocumentHandler(BaseToolHandler):
    tool_name = "index_document"
    input_model = IndexDocumentInput
    output_model = IndexDocumentOutputData

    def run(self, payload: IndexDocumentInput):
        repo = get_repo()
        record = repo.documents.get(payload.document_id)
        if record is None:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="document_not_found", message=f"document {payload.document_id} not found"),
            )
        raw = get_object_store().get(record.storage_uri)
        text = _extract_text(raw)
        chunks = _chunk_text(text, payload.chunk_size, payload.chunk_overlap)
        if not chunks:
            record.index_status = "failed"
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="empty_document", message=f"document {payload.document_id} has no indexable text"),
            )

        section_titles = [sec.title for sec in (record.sections or [])]
        pages = max(1, record.pages_count or 1)
        vector_items: list[VectorItem] = []
        for idx, (char_start, char_end, chunk_text) in enumerate(chunks, start=1):
            page_no = min(pages, 1 + int((idx - 1) * pages / max(1, len(chunks))))
            section_title = section_titles[min(len(section_titles) - 1, int((idx - 1) * len(section_titles) / max(1, len(chunks))))] if section_titles else None
            vector_items.append(
                VectorItem(
                    chunk_id=f"{payload.document_id}-c{idx}",
                    text=chunk_text,
                    vector=get_embed_client().embed(chunk_text),
                    metadata={
                        "document_id": payload.document_id,
                        "section_title": section_title,
                        "page_no": page_no,
                        "char_start": char_start,
                        "char_end": char_end,
                    },
                )
            )
        index_name = f"doc-{payload.document_id}"
        get_vector_store().upsert_chunks(index_name, vector_items)
        repo.chunks[payload.document_id] = [
            {
                "chunk_id": item.chunk_id,
                "text": item.text,
                "metadata": item.metadata,
            }
            for item in vector_items
        ]
        record.index_status = "completed"
        return success_result(
            tool_name=self.tool_name,
            data=IndexDocumentOutputData(
                document_id=payload.document_id,
                chunks_count=len(vector_items),
                vector_index_name=index_name,
                index_status="completed",
            ),
        )


index_document_tool = IndexDocumentHandler()
