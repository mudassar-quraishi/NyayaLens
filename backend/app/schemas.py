"""Pydantic v2 schemas — request/response types and LLM output schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────

class ReadingLevel(str, Enum):
    simple = "simple"
    standard = "standard"
    detailed = "detailed"

class Language(str, Enum):
    en = "en"
    hi = "hi"
    hinglish = "hinglish"

class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class Favor(str, Enum):
    party_a = "party_a"
    party_b = "party_b"
    balanced = "balanced"
    unclear = "unclear"

class ChangeType(str, Enum):
    added = "added"
    removed = "removed"
    modified = "modified"
    unchanged = "unchanged"
    moved = "moved"

class RiskDelta(str, Enum):
    better = "better"
    worse = "worse"
    neutral = "neutral"
    unclear = "unclear"

class DueKind(str, Enum):
    absolute = "absolute"
    relative = "relative"
    recurring = "recurring"
    conditional = "conditional"
    none_ = "none"

class ObligationParty(str, Enum):
    you = "you"
    other = "other"
    both = "both"

class DocType(str, Enum):
    rental = "rental"
    employment = "employment"
    freelance = "freelance"
    nda = "nda"
    loan = "loan"
    tos = "tos"
    other = "other"


# ── Session ────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    language: Language = Language.en
    reading_level: ReadingLevel = ReadingLevel.standard

class SessionResponse(BaseModel):
    id: str
    language: Language
    reading_level: ReadingLevel
    created_at: datetime
    expires_at: datetime


# ── Document ───────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    session_id: str
    filename: str
    doc_type: str
    status: str
    content_hash: str | None = None

class DocumentAnalysis(BaseModel):
    document_id: str
    doc_type: str
    key_facts: dict
    clauses: list[ClauseWithFindings]
    missing_clauses: list[MissingClauseResponse]
    risk_score: int  # 0-100
    risk_breakdown: dict
    top_concerns: list[str]

class DocumentUploadResponse(BaseModel):
    id: str
    session_id: str
    filename: str
    status: str
    clause_count: int


# ── Clause ─────────────────────────────────────────────────────────

class ClauseResponse(BaseModel):
    id: str
    ordinal: int
    heading: str
    text: str
    char_start: int
    char_end: int
    page: int

class FindingResponse(BaseModel):
    id: str
    clause_type: str
    plain_text: str
    what_it_means: str
    risk_level: RiskLevel
    risk_reasons: list[str]
    favors: Favor
    questions: list[str]
    needs_review: bool
    confidence: float
    evidence_quote: str
    verified: bool
    verification_method: str | None = None

class ClauseWithFindings(BaseModel):
    clause: ClauseResponse
    findings: list[FindingResponse]


# ── Missing Clauses ────────────────────────────────────────────────

class MissingClauseResponse(BaseModel):
    name: str
    why_it_matters: str
    severity: str


# ── LLM Output Schemas (what the LLM must return) ─────────────────

class ClauseAnalysisLLM(BaseModel):
    """Schema the LLM must return for P1 clause analysis."""
    clause_type: str = Field(description="Type of clause, e.g. termination, payment, liability")
    plain_english: str = Field(description="Plain-language rewrite of the clause")
    what_it_means_for_you: str = Field(description="One-line personal impact statement")
    risk_level: RiskLevel
    risk_reasons: list[str] = Field(description="Each reason in one plain sentence")
    favors: Favor
    questions_to_ask: list[str] = Field(default_factory=list)
    needs_lawyer_review: bool = False
    confidence: float = Field(ge=0, le=1)
    evidence_quote: str = Field(description="Exact substring from the clause supporting risk assessment")

class MissingClauseLLM(BaseModel):
    name: str
    why_it_matters: str
    severity: RiskLevel

class InconsistencyLLM(BaseModel):
    clause_a_id: int
    clause_b_id: int
    quote_a: str
    quote_b: str
    description: str

class MissingClauseScanLLM(BaseModel):
    """Schema the LLM must return for P2 missing-clause / inconsistency scan."""
    missing_clauses: list[MissingClauseLLM] = Field(default_factory=list)
    inconsistencies: list[InconsistencyLLM] = Field(default_factory=list)

class SegmentedClauseLLM(BaseModel):
    """Schema for LLM clause-boundary refinement."""
    ordinal: int
    heading: str
    text: str

class DocTypeLLM(BaseModel):
    """Schema for LLM document-type detection."""
    doc_type: DocType
    user_role: str = Field(description="The role of the likely user, e.g. tenant, employee, freelancer")
    confidence: float = Field(ge=0, le=1)

class KeyFactsLLM(BaseModel):
    """Extracted key facts from a document."""
    parties: list[str] = Field(default_factory=list)
    effective_date: str | None = None
    term: str | None = None
    amounts: list[str] = Field(default_factory=list)
    governing_law: str | None = None
    jurisdiction: str | None = None
    notice_periods: list[str] = Field(default_factory=list)

class GlossaryEntryLLM(BaseModel):
    term: str
    definition: str

class GlossaryLLM(BaseModel):
    entries: list[GlossaryEntryLLM] = Field(default_factory=list)


# ── Q&A ────────────────────────────────────────────────────────────

class QARequest(BaseModel):
    session_id: str
    question: str
    doc_ids: list[str]

class CitationLLM(BaseModel):
    clause_id: int = Field(description="Ordinal of the clause")
    quote: str = Field(description="Exact quote from the clause")

class QAResponseLLM(BaseModel):
    answer: str
    citations: list[CitationLLM] = Field(default_factory=list)
    grounded: bool
    followups: list[str] = Field(default_factory=list)

class QAResponse(BaseModel):
    answer: str
    citations: list[dict]
    grounded: bool
    followups: list[str]


# ── Compare ────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    doc_a: str
    doc_b: str

class ComparisonPairLLM(BaseModel):
    clause_a_ordinal: int | None = None
    clause_b_ordinal: int | None = None
    change_type: ChangeType
    what_changed: str
    who_benefits: str
    risk_delta: RiskDelta
    quote_a: str | None = None
    quote_b: str | None = None

class ComparisonResultLLM(BaseModel):
    pairs: list[ComparisonPairLLM]
    bottom_line: list[str] = Field(max_length=5)


# ── Obligations ────────────────────────────────────────────────────

class ObligationLLM(BaseModel):
    party: ObligationParty
    action: str
    due_kind: DueKind
    due_value: str = ""
    trigger: str = ""
    consequence_if_missed: str = ""
    clause_id: int
    evidence_quote: str

class ObligationResponse(BaseModel):
    id: str
    party: str
    action: str
    due_kind: str
    due_value: str
    consequence: str
    clause_id: str | None
    evidence_quote: str


# ── Lawyer Brief ───────────────────────────────────────────────────

class BriefSectionLLM(BaseModel):
    snapshot: str
    key_facts: list[str]
    top_risks: list[dict]
    missing_protections: list[str]
    questions_for_lawyer: list[str]
    documents_to_bring: list[str]


# ── Situation Navigator ────────────────────────────────────────────

class EscalationStepLLM(BaseModel):
    step_number: int = Field(default=1)
    title: str = Field(default="")
    timeframe: str = Field(default="")
    cost_estimate: str = Field(default="")
    action_description: str = Field(default="")
    tips: list[str] = Field(default_factory=list)

class NavigatorResponseLLM(BaseModel):
    situation_summary: str = Field(default="")
    dispute_category: str = Field(default="General Legal Dispute")
    urgent_lawyer_needed: bool = Field(default=False)
    urgent_reasons: list[str] = Field(default_factory=list)
    steps: list[EscalationStepLLM] = Field(default_factory=list)
    evidence_needed: list[str] = Field(default_factory=list)
    free_legal_aid: list[dict] = Field(default_factory=list)
    escalation_ladder: list[dict] = Field(default_factory=list)
    evidence_to_gather: list[str] = Field(default_factory=list)
    rough_cost_time: str = ""
    urgent_lawyer_triggers: list[str] = Field(default_factory=list)
    legal_aid_resources: list[dict] = Field(default_factory=list)


# ── Progress SSE ───────────────────────────────────────────────────

class ProgressEvent(BaseModel):
    stage: str
    message: str
    progress: float  # 0.0–1.0
    detail: dict | None = None
