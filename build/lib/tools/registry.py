from domain.base import ToolCapability
from tools.academic.get_paper_details import get_paper_details_tool
from tools.academic.resolve_paper_identity import resolve_paper_identity_tool
from tools.academic.search_papers import search_papers_tool
from tools.citation.export_bibtex import export_bibtex_tool
from tools.citation.format_references import format_references_tool
from tools.compute.analyze_table import analyze_table_tool
from tools.compute.execute_notebook_template import execute_notebook_template_tool
from tools.compute.execute_python_code import execute_python_code_tool
from tools.compute.generate_plot import generate_plot_tool
from tools.document.ask_paper import ask_paper_tool
from tools.document.fetch_pdf import fetch_pdf_tool
from tools.document.get_document_status import get_document_status_tool
from tools.document.index_document import index_document_tool
from tools.document.parse_pdf import parse_pdf_tool
from tools.document.retrieve_evidence import retrieve_evidence_tool
from tools.judge.judge_agent_trajectory import judge_agent_trajectory_tool
from tools.judge.judge_answer_quality import judge_answer_quality_tool
from tools.library.add_paper_note import add_paper_note_tool
from tools.library.list_library_papers import list_library_papers_tool
from tools.library.save_paper_to_library import save_paper_to_library_tool
from tools.library.tag_paper import tag_paper_tool
from tools.observability.record_observability_event import record_observability_event_tool
from tools.synthesis.compare_papers import compare_papers_tool
from tools.synthesis.extract_paper_facts import extract_paper_facts_tool
from tools.synthesis.generate_related_work import generate_related_work_tool

TOOL_REGISTRY = {
    "search_papers": search_papers_tool,
    "get_paper_details": get_paper_details_tool,
    "resolve_paper_identity": resolve_paper_identity_tool,
    "fetch_pdf": fetch_pdf_tool,
    "parse_pdf": parse_pdf_tool,
    "index_document": index_document_tool,
    "get_document_status": get_document_status_tool,
    "retrieve_evidence": retrieve_evidence_tool,
    "ask_paper": ask_paper_tool,
    "save_paper_to_library": save_paper_to_library_tool,
    "list_library_papers": list_library_papers_tool,
    "add_paper_note": add_paper_note_tool,
    "tag_paper": tag_paper_tool,
    "extract_paper_facts": extract_paper_facts_tool,
    "compare_papers": compare_papers_tool,
    "generate_related_work": generate_related_work_tool,
    "export_bibtex": export_bibtex_tool,
    "format_references": format_references_tool,
    "execute_python_code": execute_python_code_tool,
    "execute_notebook_template": execute_notebook_template_tool,
    "analyze_table": analyze_table_tool,
    "generate_plot": generate_plot_tool,
    "judge_answer_quality": judge_answer_quality_tool,
    "judge_agent_trajectory": judge_agent_trajectory_tool,
    "record_observability_event": record_observability_event_tool,
}

TOOL_CAPABILITIES: dict[str, ToolCapability] = {
    "search_papers": ToolCapability(name="search_papers", category="academic", owner="python", cacheable=True),
    "get_paper_details": ToolCapability(name="get_paper_details", category="academic", owner="python", cacheable=True),
    "resolve_paper_identity": ToolCapability(name="resolve_paper_identity", category="academic", owner="python", cacheable=True),
    "fetch_pdf": ToolCapability(name="fetch_pdf", category="document", owner="python", cacheable=True),
    "parse_pdf": ToolCapability(name="parse_pdf", category="document", owner="python", cacheable=True),
    "index_document": ToolCapability(name="index_document", category="document", owner="python", has_side_effect=True),
    "get_document_status": ToolCapability(name="get_document_status", category="document", owner="python", cacheable=True),
    "retrieve_evidence": ToolCapability(name="retrieve_evidence", category="document", owner="python", cacheable=True),
    "ask_paper": ToolCapability(name="ask_paper", category="document", owner="python", judgeable=True),
    "save_paper_to_library": ToolCapability(name="save_paper_to_library", category="library", owner="java", has_side_effect=True),
    "list_library_papers": ToolCapability(name="list_library_papers", category="library", owner="java", cacheable=True),
    "add_paper_note": ToolCapability(name="add_paper_note", category="library", owner="java", has_side_effect=True),
    "tag_paper": ToolCapability(name="tag_paper", category="library", owner="java", has_side_effect=True),
    "extract_paper_facts": ToolCapability(name="extract_paper_facts", category="synthesis", owner="python", judgeable=True),
    "compare_papers": ToolCapability(name="compare_papers", category="synthesis", owner="python", judgeable=True),
    "generate_related_work": ToolCapability(name="generate_related_work", category="synthesis", owner="python", judgeable=True),
    "export_bibtex": ToolCapability(name="export_bibtex", category="citation", owner="python", has_side_effect=True),
    "format_references": ToolCapability(name="format_references", category="citation", owner="python", cacheable=True),
    "execute_python_code": ToolCapability(name="execute_python_code", category="compute", owner="python", has_side_effect=True),
    "execute_notebook_template": ToolCapability(name="execute_notebook_template", category="compute", owner="python", has_side_effect=True),
    "analyze_table": ToolCapability(name="analyze_table", category="compute", owner="python", cacheable=True),
    "generate_plot": ToolCapability(name="generate_plot", category="compute", owner="python", has_side_effect=True),
    "judge_answer_quality": ToolCapability(name="judge_answer_quality", category="judge", owner="python", judgeable=True),
    "judge_agent_trajectory": ToolCapability(name="judge_agent_trajectory", category="judge", owner="python", judgeable=True),
    "record_observability_event": ToolCapability(name="record_observability_event", category="observability", owner="platform", has_side_effect=True),
}


def get_tool_capability(tool_name: str) -> ToolCapability | None:
    return TOOL_CAPABILITIES.get(tool_name)


def get_tool_capability_map() -> dict[str, ToolCapability]:
    return dict(TOOL_CAPABILITIES)
