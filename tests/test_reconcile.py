"""Deterministic tests for the reconcile node's three-way-match logic. No LLM needed."""
from decimal import Decimal
from datetime import date

from src.models import ProcessingRequest
from src.agent.state import AgentState
from src.agent.nodes import gather_node, reconcile_node


def _reconciled(req: ProcessingRequest) -> dict:
    s = AgentState(request=req)
    s = s.model_copy(update=gather_node(s))
    return reconcile_node(s)


def test_clean_match_has_no_exceptions():
    req = ProcessingRequest(case_id="T", invoice_ref="INV-CLEAN", vendor="Acme Supplies",
                            amount=Decimal("1250.00"), currency="AUD",
                            invoice_date=date(2026, 9, 10), po_number="PO-5001")
    u = _reconciled(req)
    assert u["exceptions"] == []
    assert u["calculations"]["variance_pct"] == Decimal("0")


def test_amount_mismatch_exceeds_tolerance():
    req = ProcessingRequest(case_id="T", invoice_ref="INV-X", vendor="Acme Supplies",
                            amount=Decimal("2000.00"), currency="AUD",
                            invoice_date=date(2026, 9, 10), po_number="PO-5001")
    u = _reconciled(req)
    assert "amount_exceeds_tolerance" in u["exceptions"]


def test_duplicate_of_paid_flagged():
    req = ProcessingRequest(case_id="T", invoice_ref="INV-2045", vendor="Acme Supplies",
                            amount=Decimal("4800.00"), currency="AUD",
                            invoice_date=date(2026, 7, 28), po_number=None)
    u = _reconciled(req)
    assert "duplicate_of_paid_invoice" in u["exceptions"]


def test_missing_po_recorded():
    req = ProcessingRequest(case_id="T", invoice_ref="INV-NOPO", vendor="Acme Supplies",
                            amount=Decimal("500.00"), currency="AUD",
                            invoice_date=date(2026, 9, 10), po_number=None)
    u = _reconciled(req)
    assert "no_purchase_order" in u["exceptions"]
