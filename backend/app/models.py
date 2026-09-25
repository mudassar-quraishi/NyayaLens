"""SQLAlchemy ORM models for NyayaLens."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _default_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=24)


def _uuid() -> str:
    return uuid.uuid4().hex


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(32), primary_key=True, default=_uuid)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    language = Column(String(16), default="en", nullable=False)
    reading_level = Column(String(16), default="standard", nullable=False)
    expires_at = Column(DateTime, default=_default_expiry, nullable=False)

    documents = relationship("Document", back_populates="session", cascade="all, delete-orphan")
    comparisons = relationship("Comparison", back_populates="session", cascade="all, delete-orphan")
    qa_messages = relationship("QAMessage", back_populates="session", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(32), primary_key=True, default=_uuid)
    session_id = Column(String(32), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(512), nullable=False)
    doc_type = Column(String(64), default="other")
    raw_text = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True)
    redacted_text = Column(Text, nullable=True)
    redaction_map_json = Column(Text, default="{}")
    key_facts_json = Column(Text, default="{}")
    status = Column(String(32), default="uploaded")  # uploaded, processing, analyzed, error

    session = relationship("Session", back_populates="documents")
    clauses = relationship("Clause", back_populates="document", cascade="all, delete-orphan")
    missing_clauses = relationship("MissingClause", back_populates="document", cascade="all, delete-orphan")
    obligations = relationship("Obligation", back_populates="document", cascade="all, delete-orphan")


class Clause(Base):
    __tablename__ = "clauses"

    id = Column(String(32), primary_key=True, default=_uuid)
    document_id = Column(String(32), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    ordinal = Column(Integer, nullable=False)
    heading = Column(String(512), default="")
    text = Column(Text, nullable=False)
    char_start = Column(Integer, nullable=False)
    char_end = Column(Integer, nullable=False)
    page = Column(Integer, default=0)
    embedding_blob = Column(LargeBinary, nullable=True)
    content_hash = Column(String(64), nullable=True)

    document = relationship("Document", back_populates="clauses")
    findings = relationship("Finding", back_populates="clause", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String(32), primary_key=True, default=_uuid)
    clause_id = Column(String(32), ForeignKey("clauses.id", ondelete="CASCADE"), nullable=False)
    clause_type = Column(String(64), default="general")
    plain_text = Column(Text, default="")
    what_it_means = Column(Text, default="")
    risk_level = Column(String(16), default="low")  # low, medium, high
    risk_reasons_json = Column(Text, default="[]")
    favors = Column(String(32), default="unclear")
    questions_json = Column(Text, default="[]")
    needs_review = Column(Boolean, default=False)
    confidence = Column(Float, default=0.0)
    evidence_quote = Column(Text, default="")
    verified = Column(Boolean, default=False)
    verification_method = Column(String(32), nullable=True)  # exact, fuzzy, failed

    clause = relationship("Clause", back_populates="findings")


class MissingClause(Base):
    __tablename__ = "missing_clauses"

    id = Column(String(32), primary_key=True, default=_uuid)
    document_id = Column(String(32), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(256), nullable=False)
    why_it_matters = Column(Text, default="")
    severity = Column(String(16), default="medium")

    document = relationship("Document", back_populates="missing_clauses")


class Obligation(Base):
    __tablename__ = "obligations"

    id = Column(String(32), primary_key=True, default=_uuid)
    document_id = Column(String(32), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    clause_id = Column(String(32), ForeignKey("clauses.id"), nullable=True)
    party = Column(String(32), nullable=False)  # you, other, both
    action = Column(Text, nullable=False)
    due_kind = Column(String(32), default="none")  # absolute, relative, recurring, conditional, none
    due_value = Column(String(256), default="")
    consequence = Column(Text, default="")
    evidence_quote = Column(Text, default="")

    document = relationship("Document", back_populates="obligations")


class Comparison(Base):
    __tablename__ = "comparisons"

    id = Column(String(32), primary_key=True, default=_uuid)
    session_id = Column(String(32), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    doc_a_id = Column(String(32), ForeignKey("documents.id"), nullable=False)
    doc_b_id = Column(String(32), ForeignKey("documents.id"), nullable=False)
    result_json = Column(Text, default="{}")

    session = relationship("Session", back_populates="comparisons")


class QAMessage(Base):
    __tablename__ = "qa_messages"

    id = Column(String(32), primary_key=True, default=_uuid)
    session_id = Column(String(32), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(16), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    citations_json = Column(Text, default="[]")
    grounded = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)

    session = relationship("Session", back_populates="qa_messages")
