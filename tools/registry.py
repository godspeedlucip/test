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
