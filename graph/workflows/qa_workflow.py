from langgraph.graph import END, START, StateGraph

from graph.nodes.ask_node import ask_node
from graph.nodes.compose_node import compose_node
from graph.nodes.compute_node import compute_node
from graph.nodes.human_review_node import human_review_node
from graph.nodes.intent_router import intent_router
from graph.nodes.judge_node import judge_node
from graph.nodes.observability_node import observability_node
from graph.nodes.prepare_documents import prepare_documents
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


def _route_after_judge(state: AgentState) -> str:
    return _state_get(state, "route_after_judge", "proceed")


def _route_after_intent(state: AgentState) -> str:
    return _state_get(state, "intent_route", "documents")


def _route_after_ask(state: AgentState) -> str:
    return "judge_node" if bool(_state_get(state, "enable_judge", False)) else "compose_node"


def build_qa_workflow():
    graph = StateGraph(AgentState)
    graph.add_node("intent_router", intent_router)
    graph.add_node("compute_node", compute_node)
    graph.add_node("search_node", search_node)
    graph.add_node("prepare_documents", prepare_documents)
    graph.add_node("ask_node", ask_node)
    graph.add_node("judge_node", judge_node)
    graph.add_node("human_review_node", human_review_node)
    graph.add_node("compose_node", compose_node)
    graph.add_node("observability_node", observability_node)

    graph.add_edge(START, "intent_router")
    graph.add_conditional_edges(
        "intent_router",
        _route_after_intent,
        {
            "compute": "compute_node",
            "documents": "search_node",
        },
    )
    graph.add_edge("compute_node", "compose_node")
    graph.add_edge("search_node", "prepare_documents")
    graph.add_edge("prepare_documents", "ask_node")
    graph.add_conditional_edges(
        "ask_node",
        _route_after_ask,
        {
            "judge_node": "judge_node",
            "compose_node": "compose_node",
        },
    )
    graph.add_conditional_edges(
        "judge_node",
        _route_after_judge,
        {
            "proceed": "compose_node",
            "human_review": "human_review_node",
        },
    )
    graph.add_edge("human_review_node", "compose_node")
    graph.add_edge("compose_node", "observability_node")
    graph.add_edge("observability_node", END)

    return graph.compile()
