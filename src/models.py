from __future__ import annotations
from decimal import Decimal
from datetime import date
from pydantic import BaseModel, Field
from enum import Enum

class NextAction(str, Enum):
    REQUEST_APPROVAL = "request_approval"   # FIN-001: evidence matches, ask a human
    HOLD = "hold"                           # FIN-002: duplicate — freeze it
    REJECT = "reject"                       # recommend rejection
    REQUEST_INFO = "request_info"           # FIN-004: missing evidence, can't decide


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class DocStatus(str, Enum):
    CURRENT = "current"
    SUPERSEDED = "superseded"
    UNTRUSTED = "untrusted"


class ProcessingRequest(BaseModel):
    case_id: str = Field(..., description="Unique case identifier, e.g. FIN-001")
    invoice_ref: str
    vendor: str
    amount: Decimal
    currency: str = Field(..., min_length=3, max_length=3)
    notes: str | None = None


class ChunkMetadata(BaseModel):
    document_id: str
    title: str
    version: str
    status: DocStatus                          # current | superseded | untrusted
    effective_date: date | None = None
    classification: str | None = None    # internal | restricted | external-unverified
    section: str | None = None           # chunk heading, filled by the chunker later

class Chunk(BaseModel):
    text: str
    metadata: ChunkMetadata
    

class RetrievedChunk(BaseModel):
    text: str
    relevance: float = Field(..., ge=0.0, le=1.0)
    metadata: ChunkMetadata


class Recommendation(BaseModel):
    next_action: NextAction
    confidence: Confidence
    cited_evidence: list[RetrievedChunk] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    rationale: str


class SourcedFact(BaseModel):
    statement: str
    document_ids: list[str]   # which corpus docs back this fact


class FinalResult(BaseModel):
    case_id: str
    recommendation: Recommendation
    sourced_facts: list[SourcedFact] = Field(default_factory=list)
    calculations: dict[str, Decimal] = Field(default_factory=dict)
    inferences: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    policy_findings: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)

