from __future__ import annotations
from langgraph.graph import StateGraph, START, END
from src.agent.state import AgentState
from src.models import NextAction
from src.agent.nodes import (
    retrieve_node, gather_node, reconcile_node, recommend_node,
    approval_node, submit_node, finalize_node,
)


def _route_after_recommend(state: AgentState) -> str:
    action = state.recommendation.next_action
    if action is NextAction.REQUEST_APPROVAL:
        return "approval"          # payment → needs a human
    if action is NextAction.REQUEST_INFO:
        return "finalize"          # can't decide → no decision to record
    return "submit"                # hold / reject → record directly


def build_graph(checkpointer=None):
    g = StateGraph(AgentState)
    for name, fn in [
        ("retrieve", retrieve_node), ("gather", gather_node),
        ("reconcile", reconcile_node), ("recommend", recommend_node),
        ("approval", approval_node), ("submit", submit_node), ("finalize", finalize_node),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "gather")
    g.add_edge("gather", "reconcile")
    g.add_edge("reconcile", "recommend")
    g.add_conditional_edges("recommend", _route_after_recommend,
                            {"approval": "approval", "submit": "submit", "finalize": "finalize"})
    g.add_edge("approval", "submit")
    g.add_edge("submit", "finalize")
    g.add_edge("finalize", END)

    return g.compile(checkpointer=checkpointer)