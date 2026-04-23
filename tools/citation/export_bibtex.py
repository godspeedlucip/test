from pydantic import BaseModel

from domain.context import RequestContext
from domain.runtime import RuntimeConfig
from integrations import get_repo
from tools.base import BaseToolHandler, success_result


class ExportBibtexInput(BaseModel):
    context: RequestContext
    runtime: RuntimeConfig | None = None
    paper_ids: list[str]
    deduplicate: bool = True


class ExportBibtexOutputData(BaseModel):
    entries_count: int
    bibtex_text: str
    export_file_uri: str | None = None


class ExportBibtexHandler(BaseToolHandler):
    tool_name = "export_bibtex"
    input_model = ExportBibtexInput
    output_model = ExportBibtexOutputData

    def run(self, payload: ExportBibtexInput):
        repo = get_repo()
        paper_ids = list(dict.fromkeys(payload.paper_ids)) if payload.deduplicate else payload.paper_ids
        entries = []
        for pid in paper_ids:
            p = repo.papers.get(pid)
            title = p.title if p else pid
            year = p.year if p and p.year else 2024
            entries.append(f"@article{{{pid},\\n  title={{ {title} }},\\n  year={{ {year} }}\\n}}")
        bib = "\n\n".join(entries)
        return success_result(
            tool_name=self.tool_name,
            data=ExportBibtexOutputData(entries_count=len(entries), bibtex_text=bib, export_file_uri="memory://exports/references.bib"),
        )


export_bibtex_tool = ExportBibtexHandler()
