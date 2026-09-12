from __future__ import annotations
from datetime import date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    PENDING = "pending"
    NOT_REQUIRED = "not_required"


class POLine(BaseModel):
    line_id: str
    description: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class GoodsReceipt(BaseModel):
    receipt_id: str
    line_id: str                         # which PO line this receipt fulfills
    quantity_received: int
    received_date: date


class PurchaseOrder(BaseModel):
    po_number: str
    vendor: str
    currency: str
    lines: list[POLine]
    total: Decimal
    tolerance_pct: Decimal               # allowed variance when matching (e.g. 2%)
    approval_status: ApprovalStatus
    receipts: list[GoodsReceipt] = Field(default_factory=list)


class GetPurchaseOrderInput(BaseModel):
    po_number: str = Field(..., min_length=1)


class GetPurchaseOrderOutput(BaseModel):
    found: bool
    purchase_order: PurchaseOrder | None = None


class ToolTimeoutError(Exception):
    """Raised to simulate the PO system timing out (drives FIN-004)."""


# --- mock purchase-order data (fixtures) ---
_TIMEOUT_POS = {"PO-TIMEOUT"}

_PURCHASE_ORDERS: dict[str, PurchaseOrder] = {
    "PO-5001": PurchaseOrder(
        po_number="PO-5001", vendor="Acme Supplies", currency="AUD",
        lines=[POLine(line_id="L1", description="Copy paper, A4 box",
                      quantity=10, unit_price=Decimal("125.00"), line_total=Decimal("1250.00"))],
        total=Decimal("1250.00"), tolerance_pct=Decimal("2.0"),
        approval_status=ApprovalStatus.APPROVED,
        receipts=[GoodsReceipt(receipt_id="GR-1", line_id="L1",
                               quantity_received=10, received_date=date(2026, 9, 1))],
    ),
}


def get_purchase_order(payload: GetPurchaseOrderInput) -> GetPurchaseOrderOutput:
    key = payload.po_number.strip().upper()
    if key in _TIMEOUT_POS:
        raise ToolTimeoutError(f"PO system timed out for {payload.po_number}")
    po = _PURCHASE_ORDERS.get(payload.po_number.strip())
    if po is None:
        return GetPurchaseOrderOutput(found=False, purchase_order=None)
    return GetPurchaseOrderOutput(found=True, purchase_order=po)