from domain.base import ToolError, ToolMeta, ToolResult
from domain.context import RequestContext
from domain.paper import Author, PaperMetadata


def test_domain_models_basic():
    ctx = RequestContext(user_id="u1", request_id="r1")
    assert ctx.user_id == "u1"

    paper = PaperMetadata(paper_id="p1", title="T", authors=[Author(name="A")])
    assert paper.authors[0].name == "A"

    result = ToolResult(
        success=False,
        error=ToolError(code="x", message="failed"),
        meta=ToolMeta(tool_name="demo"),
    )
    assert result.error.code == "x"
