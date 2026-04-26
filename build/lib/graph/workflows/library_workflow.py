from langgraph.graph import END, START, StateGraph

from graph.nodes.choose_library_candidate_node import choose_library_candidate_node
from graph.nodes.intent_router import intent_router
from graph.nodes.library_compose_node import library_compose_node
from graph.nodes.observability_node import observability_node
from graph.nodes.save_library_node import save_library_node
from graph.nodes.search_node import search_node
from graph.state import AgentState


def _state_get(state: AgentState, key: str, default=None):
    if isinstance(state, dict):
        return state.get(key, default)
    if hasattr(state, key):
        value = getattr(state, key)
        return default if value is None else value
    if hasattr(state, "model_dump"):
        return state.model_dump().get(key, default)
    return default


def _route_after_intent(state: AgentState) -> str:
    return _state_get(state, "intent_route", "documents")


def build_library_workflow():
    graph = StateGraph(AgentState)
    graph.add_node("intent_router", intent_router)
    graph.add_node("search_node", search_node)
    graph.add_node("choose_library_candidate_node", choose_library_candidate_node)
    graph.add_node("save_library_node", save_library_node)
    graph.add_node("library_compose_node", library_compose_node)
    graph.add_node("observability_node", observability_node)

    graph.add_edge(START, "intent_router")
    graph.add_conditional_edges(
        "intent_router",
        _route_after_intent,
        {
            "documents": "search_node",
            "compute": "search_node",
        },
    )
    graph.add_edge("search_node", "choose_library_candidate_node")
    graph.add_edge("choose_library_candidate_node", "save_library_node")
    graph.add_edge("save_library_node", "library_compose_node")
    graph.add_edge("library_compose_node", "observability_node")
    graph.add_edge("observability_node", END)

    return graph.compile()
