"""
API routes for sessions and documents (Phase 1).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Session, Document, Clause
from app.schemas import (
    SessionCreate, SessionResponse, DocumentResponse, DocumentUploadResponse,
    ClauseResponse, DocumentAnalysis, ClauseWithFindings, FindingResponse,
    MissingClauseResponse,
)
from app.agents.ingestor import extract_text
from app.agents.segmenter import segment_document, estimate_page
from app.llm import compute_content_hash, is_sample_document

logger = logging.getLogger("nyayalens.api")

router = APIRouter(prefix="/api", tags=["core"])


# ── Sessions ──────────────────────────────────────────────────────

@router.post("/session", response_model=SessionResponse)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new session."""
    session = Session(language=body.language, reading_level=body.reading_level)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SessionResponse(
        id=session.id,
        language=session.language,
        reading_level=session.reading_level,
        created_at=session.created_at,
        expires_at=session.expires_at,
    )


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a session and all associated data."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")
    await db.delete(session)
    await db.commit()
    return {"status": "deleted", "session_id": session_id}


# ── Documents ─────────────────────────────────────────────────────

@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload and ingest a document (PDF, DOCX, image, or text)."""
    # Verify session exists
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    # Read file
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(400, "Empty file")

    # Extract text
    try:
        raw_text, content_hash = await extract_text(
            file_bytes, file.filename or "unknown", file.content_type
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Check DEMO_MODE for non-sample documents
    from app.config import get_settings
    settings = get_settings()
    demo_warning = None
    if settings.demo_mode and not is_sample_document(content_hash):
        demo_warning = "Pre-computed results are only available for sample documents. This document will be processed normally (requires API key)."
        logger.warning("DEMO_MODE: non-sample document uploaded: %s", file.filename)

    # Create document record
    doc = Document(
        session_id=session_id,
        filename=file.filename or "unknown",
        raw_text=raw_text,
        content_hash=content_hash,
        status="processing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Segment into clauses
    try:
        segments = await segment_document(raw_text, content_hash)
    except Exception as e:
        doc.status = "error"
        await db.commit()
        logger.error("Segmentation failed for %s: %s", file.filename, e)
        raise HTTPException(500, f"Segmentation failed: {e}")

    # Save clauses
    for seg in segments:
        clause = Clause(
            document_id=doc.id,
            ordinal=seg.ordinal,
            heading=seg.heading,
            text=seg.text,
            char_start=seg.char_start,
            char_end=seg.char_end,
            page=estimate_page(seg.char_start),
            content_hash=seg.content_hash,
        )
        db.add(clause)

    doc.status = "segmented"
    await db.commit()

    return DocumentUploadResponse(
        id=doc.id,
        session_id=session_id,
        filename=doc.filename,
        status=doc.status,
        clause_count=len(segments),
    )


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Get document metadata."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return DocumentResponse(
        id=doc.id,
        session_id=doc.session_id,
        filename=doc.filename,
        doc_type=doc.doc_type,
        status=doc.status,
        content_hash=doc.content_hash,
    )


@router.get("/documents/{doc_id}/clauses", response_model=list[ClauseResponse])
async def get_clauses(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Get all clauses for a document."""
    result = await db.execute(
        select(Clause)
        .where(Clause.document_id == doc_id)
        .order_by(Clause.ordinal)
    )
    clauses = result.scalars().all()
    if not clauses:
        raise HTTPException(404, "No clauses found")
    return [
        ClauseResponse(
            id=c.id,
            ordinal=c.ordinal,
            heading=c.heading,
            text=c.text,
            char_start=c.char_start,
            char_end=c.char_end,
            page=c.page,
        )
        for c in clauses
    ]


@router.get("/documents/{doc_id}/text")
async def get_document_text(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Get raw document text."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return {"text": doc.raw_text, "content_hash": doc.content_hash}
