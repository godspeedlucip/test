from langgraph.graph import END, START, StateGraph

from graph.nodes.ask_node import ask_node
from graph.nodes.compose_node import compose_node
from graph.nodes.intent_router import intent_router
from graph.nodes.judge_node import judge_node
from graph.nodes.observability_node import observability_node
from graph.nodes.prepare_documents import prepare_documents
from graph.state import GraphState


def build_qa_workflow():
    graph = StateGraph(GraphState)
    graph.add_node("intent_router", intent_router)
    graph.add_node("prepare_documents", prepare_documents)
    graph.add_node("ask_node", ask_node)
    graph.add_node("judge_node", judge_node)
    graph.add_node("compose_node", compose_node)
    graph.add_node("observability_node", observability_node)

    graph.add_edge(START, "intent_router")
    graph.add_edge("intent_router", "prepare_documents")
    graph.add_edge("prepare_documents", "ask_node")
    graph.add_edge("ask_node", "judge_node")
    graph.add_edge("judge_node", "compose_node")
    graph.add_edge("compose_node", "observability_node")
    graph.add_edge("observability_node", END)

    return graph.compile()
