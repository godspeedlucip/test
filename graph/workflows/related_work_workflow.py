from langgraph.graph import END, START, StateGraph

from graph.nodes.compose_node import compose_node
from graph.nodes.compute_node import compute_node
from graph.nodes.human_review_node import human_review_node
from graph.nodes.intent_router import intent_router
from graph.nodes.judge_node import judge_node
from graph.nodes.observability_node import observability_node
from graph.nodes.prepare_documents import prepare_documents
from graph.nodes.related_work_node import related_work_node
from graph.nodes.revise_node import revise_node
from graph.nodes.search_node import search_node
from graph.nodes.trajectory_judge_node import trajectory_judge_node
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
    return _state_get(state, "route_after_judge", "trajectory_judge")


def _route_after_human_review(state: AgentState) -> str:
    return _state_get(state, "route_after_human_review", "trajectory_judge")


def build_related_work_workflow():
    graph = StateGraph(AgentState)
    graph.add_node("intent_router", intent_router)
    graph.add_node("compute_node", compute_node)
    graph.add_node("search_node", search_node)
    graph.add_node("prepare_documents", prepare_documents)
    graph.add_node("related_work_node", related_work_node)
    graph.add_node("judge_node", judge_node)
    graph.add_node("revise_node", revise_node)
    graph.add_node("human_review_node", human_review_node)
    graph.add_node("trajectory_judge_node", trajectory_judge_node)
    graph.add_node("compose_node", compose_node)
    graph.add_node("observability_node", observability_node)

    graph.add_edge(START, "intent_router")
    graph.add_conditional_edges(
        "intent_router",
        lambda s: _state_get(s, "intent_route", "documents"),
        {
            "compute": "compute_node",
            "documents": "search_node",
        },
    )
    graph.add_edge("compute_node", "compose_node")
    graph.add_edge("search_node", "prepare_documents")
    graph.add_edge("prepare_documents", "related_work_node")
    graph.add_edge("related_work_node", "judge_node")

    graph.add_conditional_edges(
        "judge_node",
        _route_after_judge,
        {
            "revise": "revise_node",
            "human_review": "human_review_node",
            "trajectory_judge": "trajectory_judge_node",
        },
    )

    graph.add_edge("revise_node", "judge_node")
    graph.add_conditional_edges(
        "human_review_node",
        _route_after_human_review,
        {
            "revise": "revise_node",
            "trajectory_judge": "trajectory_judge_node",
        },
    )
    graph.add_edge("trajectory_judge_node", "compose_node")
    graph.add_edge("compose_node", "observability_node")
    graph.add_edge("observability_node", END)

    return graph.compile()
