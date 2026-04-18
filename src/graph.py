"""LangGraph workflow — wires up all nodes into the triage pipeline."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.models import LoanApplicationState
from src.nodes.enrich import enrich_node
from src.nodes.extract import extract_node
from src.nodes.ingest import ingest_node
from src.nodes.route import route_node
from src.nodes.score import score_node
from src.nodes.validate import should_continue_after_validation, validate_node


def build_graph() -> StateGraph:
    """Construct and compile the loan triage state graph."""

    workflow = StateGraph(LoanApplicationState)

    # Add nodes
    workflow.add_node("ingest", ingest_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("enrich", enrich_node)
    workflow.add_node("score", score_node)
    workflow.add_node("route", route_node)

    # Define edges
    workflow.set_entry_point("ingest")
    workflow.add_edge("ingest", "extract")
    workflow.add_edge("extract", "validate")
    workflow.add_conditional_edges(
        "validate",
        should_continue_after_validation,
        {
            "enrich": "enrich",
            "route": "route",  # skip scoring if too many missing fields
        },
    )
    workflow.add_edge("enrich", "score")
    workflow.add_edge("score", "route")
    workflow.add_edge("route", END)

    return workflow.compile()


# Pre-built compiled graph
triage_app = build_graph()
