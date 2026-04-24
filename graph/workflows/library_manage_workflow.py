from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from domain.context import RequestContext
from graph.nodes.choose_library_candidate_node import choose_library_candidate_node
from graph.nodes.common import run_node
from graph.nodes.observability_node import observability_node
from graph.nodes.save_library_node import save_library_node
from graph.nodes.search_node import search_node
from graph.state import AgentState
from tools.library.add_paper_note import AddPaperNoteInput, add_paper_note_tool
from tools.library.list_library_papers import ListLibraryPapersInput, list_library_papers_tool
from tools.library.tag_paper import TagPaperInput, tag_paper_tool


def _state_get(state: AgentState, key: str, default=None):
    if isinstance(state, dict):
        return state.get(key, default)
    if hasattr(state, key):
        value = getattr(state, key)
        return default if value is None else value
    if hasattr(state, "model_dump"):
        return state.model_dump().get(key, default)
    return default


def _normalize_context_with_idempotency(state: dict) -> RequestContext:
    base = dict(state.get("context") or {"user_id": "anonymous"})
    idem = state.get("idempotency_key")
    if idem and not base.get("request_id"):
        base["request_id"] = idem
    return RequestContext.model_validate(base)


def _action_router_node(state: dict):
    def _impl(s: dict):
        action = (s.get("action") or "save").lower()
        if action not in {"save", "list", "add_note", "tag"}:
            raise RuntimeError(f"unsupported library manage action: {action}")
        return {"action": action}

    return run_node("library_action_router_node", state, _impl)


def _library_note_node(state: dict):
    def _impl(s: dict):
        ctx = _normalize_context_with_idempotency(s)
        paper_id = s.get("paper_id") or s.get("selected_paper_id") or s.get("saved_paper_id")
        note = s.get("library_note")
        if not paper_id or not note:
            raise RuntimeError("add_note requires paper_id and library_note")
        noted = add_paper_note_tool.execute(AddPaperNoteInput(context=ctx, paper_id=paper_id, note=note))
        if not noted.success:
            raise RuntimeError(noted.error.message if noted.error else "add_paper_note failed")
        return {"note_result": noted.data, "saved_paper_id": paper_id}

    return run_node("library_note_node", state, _impl)


def _library_tag_node(state: dict):
    def _impl(s: dict):
        ctx = _normalize_context_with_idempotency(s)
        paper_id = s.get("paper_id") or s.get("selected_paper_id") or s.get("saved_paper_id")
        tags = s.get("paper_tags") or []
        if not paper_id:
            raise RuntimeError("tag requires paper_id")
        tagged = tag_paper_tool.execute(TagPaperInput(context=ctx, paper_id=paper_id, tags=tags))
        if not tagged.success:
            raise RuntimeError(tagged.error.message if tagged.error else "tag_paper failed")
        return {"tag_result": tagged.data, "saved_paper_id": paper_id}

    return run_node("library_tag_node", state, _impl)


def _library_list_node(state: dict):
    def _impl(s: dict):
        ctx = _normalize_context_with_idempotency(s)
        listed = list_library_papers_tool.execute(ListLibraryPapersInput(context=ctx))
        if not listed.success:
            raise RuntimeError(listed.error.message if listed.error else "list_library_papers failed")
        return {"library_paper_ids": listed.data.get("paper_ids", [])}

    return run_node("library_list_node", state, _impl)


def _library_compose_node(state: dict):
    def _impl(s: dict):
        action = (s.get("action") or "save").lower()
        selected = s.get("saved_paper_id") or s.get("selected_paper_id")
        count = len(s.get("library_paper_ids", []))
        tag_info = s.get("tag_result", {})
        note_info = s.get("note_result", {})
        if action == "list":
            message = f"Library contains {count} paper(s)."
        elif action == "add_note":
            message = f"Note added to {selected}. Total papers now: {count}."
        elif action == "tag":
            message = f"Tags updated for {selected}. Tagged={tag_info.get('tagged', False)}. Total papers now: {count}."
        else:
            message = f"Library updated with {selected}. Total papers now: {count}."
        if note_info:
            message += f" NoteAdded={note_info.get('added', False)}."
        return {"answer": message, "final_answer": message}

    return run_node("library_compose_node", state, _impl)


def _route_after_action(state: AgentState) -> str:
    action = (_state_get(state, "action", "save") or "save").lower()
    if action == "list":
        return "library_list_node"
    return "ensure_idempotency_node"


def _ensure_idempotency_node(state: dict):
    def _impl(s: dict):
        action = (s.get("action") or "save").lower()
        if action in {"save", "add_note", "tag"} and not s.get("idempotency_key"):
            raise RuntimeError(f"{action} action requires idempotency_key")
        return {}

    return run_node("ensure_idempotency_node", state, _impl)


def _route_after_idempotency(state: AgentState) -> str:
    action = (_state_get(state, "action", "save") or "save").lower()
    if action == "add_note":
        return "library_note_node"
    if action == "tag":
        return "library_tag_node"
    return "search_node"


def build_library_manage_workflow():
    graph = StateGraph(AgentState)
    graph.add_node("library_action_router_node", _action_router_node)
    graph.add_node("ensure_idempotency_node", _ensure_idempotency_node)
    graph.add_node("search_node", search_node)
    graph.add_node("choose_library_candidate_node", choose_library_candidate_node)
    graph.add_node("save_library_node", save_library_node)
    graph.add_node("library_note_node", _library_note_node)
    graph.add_node("library_tag_node", _library_tag_node)
    graph.add_node("library_list_node", _library_list_node)
    graph.add_node("library_compose_node", _library_compose_node)
    graph.add_node("observability_node", observability_node)

    graph.add_edge(START, "library_action_router_node")
    graph.add_conditional_edges(
        "library_action_router_node",
        _route_after_action,
        {
            "search_node": "search_node",
            "library_list_node": "library_list_node",
            "ensure_idempotency_node": "ensure_idempotency_node",
        },
    )
    graph.add_conditional_edges(
        "ensure_idempotency_node",
        _route_after_idempotency,
        {
            "search_node": "search_node",
            "library_note_node": "library_note_node",
            "library_tag_node": "library_tag_node",
        },
    )
    graph.add_edge("search_node", "choose_library_candidate_node")
    graph.add_edge("choose_library_candidate_node", "save_library_node")
    graph.add_edge("save_library_node", "library_list_node")
    graph.add_edge("library_note_node", "library_list_node")
    graph.add_edge("library_tag_node", "library_list_node")
    graph.add_edge("library_list_node", "library_compose_node")
    graph.add_edge("library_compose_node", "observability_node")
    graph.add_edge("observability_node", END)

    return graph.compile()
