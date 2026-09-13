from __future__ import annotations
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field


class DecisionAction(str, Enum):
    POST = "post"        # pay / post to ledger — the consequential one
    HOLD = "hold"
    REJECT = "reject"


class SubmitDecisionInput(BaseModel):
    case_id: str = Field(..., min_length=1)
    action: DecisionAction
    amount: Decimal
    currency: str = Field(..., min_length=3, max_length=3)
    approved: bool = False               # deny-by-default: must be explicitly True
    idempotency_key: str = Field(..., min_length=1)


class SubmitDecisionOutput(BaseModel):
    idempotency_key: str
    case_id: str
    action: DecisionAction
    status: str                          # "posted" | "held" | "rejected" | "denied"
    replayed: bool = False               # True when returned from the ledger (duplicate call)
    message: str


# --- idempotency ledger: key -> the decision we already made ---
_LEDGER: dict[str, SubmitDecisionOutput] = {}


def submit_finance_decision(payload: SubmitDecisionInput) -> SubmitDecisionOutput:
    # 1. Idempotency: if we've seen this key, replay the SAME result — do not act again.
    if payload.idempotency_key in _LEDGER:
        prior = _LEDGER[payload.idempotency_key]
        return prior.model_copy(update={"replayed": True})

    # 2. Deny-by-default: a POST (payment) requires explicit approval.
    if payload.action is DecisionAction.POST and not payload.approved:
        return SubmitDecisionOutput(
            idempotency_key=payload.idempotency_key, case_id=payload.case_id,
            action=payload.action, status="denied", replayed=False,
            message="Denied: posting requires explicit approval.",
        )

    # 3. Perform the (simulated) action and record it.
    status = {"post": "posted", "hold": "held", "reject": "rejected"}[payload.action.value]
    result = SubmitDecisionOutput(
        idempotency_key=payload.idempotency_key, case_id=payload.case_id,
        action=payload.action, status=status, replayed=False,
        message=f"{status} (simulated - no real money moved)",
    )
    _LEDGER[payload.idempotency_key] = result
    return result