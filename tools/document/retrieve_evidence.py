from pydantic import BaseModel, Field

from domain.context import RequestContext
from domain.document import DocumentAnchor
from domain.evidence import EvidenceSpan
from domain.runtime import RuntimeConfig
from integrations import get_vector_store
from tools.base import BaseToolHandler, success_result


class RetrieveEvidenceInput(BaseModel):
    context: RequestContext
    runtime: RuntimeConfig | None = None
    document_id: str
    query: str
    top_k: int = 5
    section_filter: list[str] = Field(default_factory=list)
    page_filter: list[int] = Field(default_factory=list)


class RetrieveEvidenceOutputData(BaseModel):
    document_id: str
    evidences: list[EvidenceSpan]


class RetrieveEvidenceHandler(BaseToolHandler):
    tool_name = "retrieve_evidence"
    input_model = RetrieveEvidenceInput
    output_model = RetrieveEvidenceOutputData

    def run(self, payload: RetrieveEvidenceInput):
        items = get_vector_store().query(f"doc-{payload.document_id}", payload.query, top_k=payload.top_k)
        evidences = []
        for i, item in enumerate(items):
            page_no = item.metadata.get("page_no")
            section_title = item.metadata.get("section_title")
            if payload.page_filter and page_no not in payload.page_filter:
                continue
            if payload.section_filter and section_title not in payload.section_filter:
                continue
            evidences.append(
                EvidenceSpan(
                    text=item.text,
                    anchor=DocumentAnchor(
                        document_id=payload.document_id,
                        page_no=page_no,
                        section_title=section_title,
                        chunk_id=item.chunk_id,
                    ),
                    score=max(0.1, 1.0 - i * 0.1),
                )
            )
        return success_result(tool_name=self.tool_name, data=RetrieveEvidenceOutputData(document_id=payload.document_id, evidences=evidences))


retrieve_evidence_tool = RetrieveEvidenceHandler()
