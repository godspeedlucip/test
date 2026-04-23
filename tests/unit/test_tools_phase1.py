from domain.context import RequestContext
from domain.judge import JudgeRubric
from domain.runtime import ModelConfig, PromptConfig
from tools.academic.search_papers import SearchPapersInput, search_papers_tool
from tools.document.ask_paper import AskPaperInput, ask_paper_tool
from tools.document.fetch_pdf import FetchPdfInput, fetch_pdf_tool
from tools.document.index_document import IndexDocumentInput, index_document_tool
from tools.document.parse_pdf import ParsePdfInput, parse_pdf_tool
from tools.judge.judge_answer_quality import JudgeAnswerQualityInput, judge_answer_quality_tool


def test_phase1_tool_chain_runs():
    ctx = RequestContext(user_id="u1", request_id="trace-1")

    sr = search_papers_tool.execute(SearchPapersInput(context=ctx, query="graph"))
    assert sr.success
    paper_id = sr.data["papers"][0]["paper_id"]

    fr = fetch_pdf_tool.execute(FetchPdfInput(context=ctx, paper_id=paper_id))
    assert fr.success
    document_id = fr.data["document_id"]

    pr = parse_pdf_tool.execute(ParsePdfInput(context=ctx, document_id=document_id))
    assert pr.success and pr.data["parse_status"] == "completed"

    ir = index_document_tool.execute(IndexDocumentInput(context=ctx, document_id=document_id))
    assert ir.success and ir.data["index_status"] == "completed"

    ar = ask_paper_tool.execute(AskPaperInput(context=ctx, document_id=document_id, question="what method?"))
    assert ar.success
    assert isinstance(ar.data["answer"], str)

    jr = judge_answer_quality_tool.execute(
        JudgeAnswerQualityInput(
            context=ctx,
            model=ModelConfig(provider="mock", model_name="judge"),
            prompt=PromptConfig(prompt_name="judge_answer_quality", prompt_version="v1"),
            question="what method?",
            answer=ar.data["answer"],
            evidences=ar.data["evidences"],
            rubric=JudgeRubric(rubric_name="r", rubric_version="v1", dimensions=["correctness", "grounding"]),
        )
    )
    assert jr.success
    assert "overall_score" in jr.data
