"""Deterministic contract tests for the tools. No LLM / API key needed."""
from decimal import Decimal
from datetime import date

import pytest

from src.tools.vendor import get_vendor_record, GetVendorInput, VendorStatus
from src.tools.invoice_history import check_invoice_history, CheckInvoiceInput
from src.tools.purchase_order import get_purchase_order, GetPurchaseOrderInput, ToolTimeoutError
from src.tools.decision import submit_finance_decision, SubmitDecisionInput, DecisionAction


# --- get_vendor_record ---

def test_vendor_found():
    out = get_vendor_record(GetVendorInput(vendor="Acme Supplies"))
    assert out.found and out.vendor.status is VendorStatus.ACTIVE


def test_vendor_not_found():
    out = get_vendor_record(GetVendorInput(vendor="Nonexistent Co"))
    assert not out.found and out.vendor is None


def test_vendor_empty_input_rejected():
    with pytest.raises(Exception):
        GetVendorInput(vendor="")


# --- check_invoice_history ---

def test_duplicate_exact_ref():
    out = check_invoice_history(CheckInvoiceInput(
        invoice_ref="INV-2045", vendor="Acme Supplies",
        amount=Decimal("4800.00"), currency="AUD", invoice_date=date(2026, 7, 28)))
    assert out.is_potential_duplicate
    assert out.matches[0].match_type == "exact_ref"


def test_duplicate_vendor_amount_within_window():
    out = check_invoice_history(CheckInvoiceInput(
        invoice_ref="INV-9999", vendor="Acme Supplies",
        amount=Decimal("4800.00"), currency="AUD", invoice_date=date(2026, 8, 2)))
    assert out.is_potential_duplicate
    assert out.matches[0].match_type == "vendor_amount"


def test_no_duplicate_outside_window():
    out = check_invoice_history(CheckInvoiceInput(
        invoice_ref="INV-9999", vendor="Acme Supplies",
        amount=Decimal("4800.00"), currency="AUD", invoice_date=date(2026, 9, 20)))
    assert not out.is_potential_duplicate


# --- get_purchase_order ---

def test_po_found():
    out = get_purchase_order(GetPurchaseOrderInput(po_number="PO-5001"))
    assert out.found and out.purchase_order.total == Decimal("1250.00")


def test_po_timeout_raises():
    with pytest.raises(ToolTimeoutError):
        get_purchase_order(GetPurchaseOrderInput(po_number="PO-TIMEOUT"))


# --- submit_finance_decision ---

def test_deny_by_default():
    out = submit_finance_decision(SubmitDecisionInput(
        case_id="T", action=DecisionAction.POST, amount=Decimal("1"),
        currency="AUD", approved=False, idempotency_key="k-deny"))
    assert out.status == "denied"


def test_idempotent_replay():
    p = SubmitDecisionInput(case_id="T", action=DecisionAction.POST, amount=Decimal("1"),
                            currency="AUD", approved=True, idempotency_key="k-idem")
    first = submit_finance_decision(p)
    second = submit_finance_decision(p)
    assert first.status == "posted" and not first.replayed
    assert second.status == "posted" and second.replayed
