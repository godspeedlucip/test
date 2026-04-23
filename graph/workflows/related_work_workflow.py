from langgraph.graph import END, START, StateGraph

from graph.nodes.compose_node import compose_node
from graph.nodes.intent_router import intent_router
from graph.nodes.judge_node import judge_node
from graph.nodes.prepare_documents import prepare_documents
from graph.nodes.related_work_node import related_work_node
from graph.nodes.revise_node import revise_node
from graph.state import GraphState


def build_related_work_workflow():
    graph = StateGraph(GraphState)
    graph.add_node("intent_router", intent_router)
    graph.add_node("prepare_documents", prepare_documents)
    graph.add_node("related_work_node", related_work_node)
    graph.add_node("judge_node", judge_node)
    graph.add_node("revise_node", revise_node)
    graph.add_node("compose_node", compose_node)

    graph.add_edge(START, "intent_router")
    graph.add_edge("intent_router", "prepare_documents")
    graph.add_edge("prepare_documents", "related_work_node")
    graph.add_edge("related_work_node", "judge_node")
    graph.add_edge("judge_node", "revise_node")
    graph.add_edge("revise_node", "compose_node")
    graph.add_edge("compose_node", END)

    return graph.compile()
