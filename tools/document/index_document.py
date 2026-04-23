from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from domain.context import RequestContext
from domain.runtime import RuntimeConfig
from integrations import get_repo, get_vector_store
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
        chunks = []
        for idx, sec in enumerate(record.sections or []):
            chunks.append(
                {
                    "chunk_id": f"{payload.document_id}-c{idx+1}",
                    "text": f"{sec.title} section content for {payload.document_id}",
                    "metadata": {
                        "document_id": payload.document_id,
                        "section_title": sec.title,
                        "page_no": sec.start_page,
                    },
                }
            )
        index_name = f"doc-{payload.document_id}"
        get_vector_store().upsert_chunks(index_name, [VectorItem(**c) for c in chunks])
        repo.chunks[payload.document_id] = chunks
        record.index_status = "completed"
        return success_result(
            tool_name=self.tool_name,
            data=IndexDocumentOutputData(
                document_id=payload.document_id,
                chunks_count=len(chunks),
                vector_index_name=index_name,
                index_status="completed",
            ),
        )


index_document_tool = IndexDocumentHandler()
