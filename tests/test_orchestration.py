"""Deterministic orchestration tests: conditional routing + graph assembly. No LLM needed."""
from decimal import Decimal
from datetime import date

from langgraph.checkpoint.memory import MemorySaver

from src.models import ProcessingRequest, Recommendation, NextAction, Confidence
from src.agent.state import AgentState
from src.agent.graph import build_graph, _route_after_recommend


def _state_with(action: NextAction) -> AgentState:
    req = ProcessingRequest(case_id="T", invoice_ref="I", vendor="V",
                            amount=Decimal("1"), currency="AUD", invoice_date=date(2026, 1, 1))
    rec = Recommendation(next_action=action, confidence=Confidence.HIGH, rationale="x")
    return AgentState(request=req, recommendation=rec)


def test_route_request_approval_goes_to_approval():
    assert _route_after_recommend(_state_with(NextAction.REQUEST_APPROVAL)) == "approval"


def test_route_hold_goes_to_submit():
    assert _route_after_recommend(_state_with(NextAction.HOLD)) == "submit"


def test_route_reject_goes_to_submit():
    assert _route_after_recommend(_state_with(NextAction.REJECT)) == "submit"


def test_route_request_info_goes_to_finalize():
    assert _route_after_recommend(_state_with(NextAction.REQUEST_INFO)) == "finalize"


def test_graph_compiles_and_is_runnable():
    graph = build_graph(MemorySaver())
    assert graph is not None
    assert hasattr(graph, "invoke")
