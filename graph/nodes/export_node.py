from domain.context import RequestContext
from integrations import get_java_client
from integrations.java_client import RecordFileArtifactRequest
from tools.citation.export_bibtex import ExportBibtexInput, export_bibtex_tool
from tools.citation.format_references import FormatReferencesInput, format_references_tool

from graph.nodes.common import run_node


def export_node(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        trace_id = s.get("trace_id") or ctx.request_id or "unknown"
        result = export_bibtex_tool.execute(ExportBibtexInput(context=ctx, paper_ids=s.get("paper_ids", [])))
        if not result.success:
            raise RuntimeError(result.error.message if result.error else "export_bibtex failed")

        references = [p.get("title", pid) for pid, p in (s.get("paper_details") or {}).items()]
        formatted = []
        if references:
            fr = format_references_tool.execute(FormatReferencesInput(context=ctx, references=references))
            if fr.success:
                formatted = fr.data.get("formatted", [])

        export_uri = result.data.get("export_file_uri")
        if export_uri:
            get_java_client().record_file_artifact(
                RecordFileArtifactRequest(
                    task_id=trace_id,
                    artifact_uri=export_uri,
                    artifact_type="bibtex",
                    metadata={"entries_count": result.data.get("entries_count", 0)},
                    idempotency_key=f"{trace_id}:bibtex:{export_uri}",
                )
            )
        return {
            "bibtex": result.data,
            "formatted_references": formatted,
            "artifacts": s.get("artifacts", []) + [{"type": "bibtex", "payload": result.data}],
        }

    return run_node("export_node", state, _impl)
