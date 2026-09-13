from __future__ import annotations
from datetime import date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field


class InvoiceStatus(str, Enum):
    PAID = "paid"
    PENDING = "pending"
    REJECTED = "rejected"


class HistoricalInvoice(BaseModel):
    invoice_id: str                      # stable internal ID
    invoice_ref: str                     # the supplier's invoice number
    vendor: str
    amount: Decimal
    currency: str
    status: InvoiceStatus
    invoice_date: date                   # when the invoice was issued
    paid_date: date | None = None


class CheckInvoiceInput(BaseModel):
    invoice_ref: str = Field(..., min_length=1)
    vendor: str = Field(..., min_length=1)
    amount: Decimal
    currency: str = Field(..., min_length=3, max_length=3)
    invoice_date: date


class InvoiceMatch(BaseModel):
    invoice: HistoricalInvoice
    match_type: str                      # "exact_ref" | "vendor_amount"
    days_apart: int | None = None        # gap for vendor_amount matches


class CheckInvoiceOutput(BaseModel):
    query_ref: str
    matches: list[InvoiceMatch] = Field(default_factory=list)
    is_potential_duplicate: bool


DUPLICATE_WINDOW_DAYS = 14               # vendor+amount only counts within this many days

# --- mock invoice history (fixtures) ---
_HISTORY: list[HistoricalInvoice] = [
    HistoricalInvoice(invoice_id="H-9001", invoice_ref="INV-2045", vendor="Acme Supplies",
                      amount=Decimal("4800.00"), currency="AUD", status=InvoiceStatus.PAID,
                      invoice_date=date(2026, 7, 28), paid_date=date(2026, 8, 1)),
    HistoricalInvoice(invoice_id="H-9002", invoice_ref="INV-3100", vendor="Globex Trading",
                      amount=Decimal("12000.00"), currency="AUD", status=InvoiceStatus.PENDING,
                      invoice_date=date(2026, 8, 15)),
]


def check_invoice_history(payload: CheckInvoiceInput) -> CheckInvoiceOutput:
    matches: list[InvoiceMatch] = []
    for inv in _HISTORY:
        same_ref = inv.invoice_ref.strip().lower() == payload.invoice_ref.strip().lower()

        days_apart = abs((inv.invoice_date - payload.invoice_date).days)
        same_vendor_amount = (
            inv.vendor.strip().lower() == payload.vendor.strip().lower()
            and inv.amount == payload.amount
            and days_apart <= DUPLICATE_WINDOW_DAYS
        )

        if same_ref:
            matches.append(InvoiceMatch(invoice=inv, match_type="exact_ref"))
        elif same_vendor_amount:
            matches.append(InvoiceMatch(invoice=inv, match_type="vendor_amount", days_apart=days_apart))

    return CheckInvoiceOutput(
        query_ref=payload.invoice_ref,
        matches=matches,
        is_potential_duplicate=len(matches) > 0,
    )
