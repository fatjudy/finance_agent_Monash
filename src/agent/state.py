from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel, Field
from src.models import ProcessingRequest, RetrievedChunk, Recommendation, FinalResult
from src.tools.vendor import VendorRecord
from src.tools.purchase_order import PurchaseOrder
from src.tools.invoice_history import InvoiceMatch
from src.tools.decision import SubmitDecisionOutput


class AgentState(BaseModel):
    # --- input ---
    request: ProcessingRequest

    # --- evidence gathered by tools ---
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    vendor: VendorRecord | None = None
    purchase_order: PurchaseOrder | None = None
    duplicate_matches: list[InvoiceMatch] = Field(default_factory=list)

    # --- reasoning ---
    calculations: dict[str, Decimal] = Field(default_factory=dict)
    exceptions: list[str] = Field(default_factory=list)
    recommendation: Recommendation | None = None

    # --- outcome ---
    approved: bool | None = None
    decision: SubmitDecisionOutput | None = None
    result: FinalResult | None = None

    # --- control ---
    status: str = "running"
    steps: int = 0
    audit: list[str] = Field(default_factory=list)
    