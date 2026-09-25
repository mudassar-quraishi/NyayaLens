"""
API route for Grounded Q&A (Phase 4).
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Session, Document, Clause, QAMessage
from app.schemas import QARequest, QAResponse
from app.agents.qa import answer_question

logger = logging.getLogger("nyayalens.api.qa")

router = APIRouter(prefix="/api", tags=["qa"])


@router.post("/qa", response_model=QAResponse)
async def ask_question(
    req: QARequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Ask a question about one or more documents in the session.
    Retrieves relevant clauses, verifies quotes, and refuses out-of-scope queries.
    """
    # Verify session exists
    res = await db.execute(select(Session).where(Session.id == req.session_id))
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    # Fetch document clauses
    clauses_query = (
        select(Clause)
        .where(Clause.document_id.in_(req.doc_ids))
        .order_by(Clause.ordinal)
    )
    c_res = await db.execute(clauses_query)
    clauses_db = c_res.scalars().all()

    if not clauses_db:
        # Check if documents exist
        docs_res = await db.execute(select(Document).where(Document.id.in_(req.doc_ids)))
        docs = docs_res.scalars().all()
        if not docs:
            raise HTTPException(404, "Documents not found")
        # Empty document text
        return QAResponse(
            answer="This document doesn't say. Here is what to ask the other party or a lawyer: The document contains no readable clauses.",
            citations=[],
            grounded=False,
            followups=[],
        )

    # Convert to dicts
    clause_dicts = [
        {
            "id": c.id,
            "ordinal": c.ordinal,
            "heading": c.heading,
            "text": c.text,
            "char_start": c.char_start,
            "char_end": c.char_end,
            "page": c.page,
        }
        for c in clauses_db
    ]

    # Get primary document type and hash
    d_res = await db.execute(select(Document).where(Document.id == req.doc_ids[0]))
    primary_doc = d_res.scalar_one_or_none()
    doc_type = primary_doc.doc_type if primary_doc else "general"
    doc_hash = primary_doc.content_hash if primary_doc else ""

    # Record user message
    user_msg = QAMessage(
        session_id=req.session_id,
        role="user",
        content=req.question,
        citations_json="[]",
        grounded=True,
    )
    db.add(user_msg)

    # Run Q&A agent
    response = await answer_question(
        session_id=req.session_id,
        question=req.question,
        clauses=clause_dicts,
        doc_type=doc_type,
        doc_hash=doc_hash or "",
    )

    # Record assistant message
    asst_msg = QAMessage(
        session_id=req.session_id,
        role="assistant",
        content=response.answer,
        citations_json=json.dumps(response.citations),
        grounded=response.grounded,
    )
    db.add(asst_msg)
    await db.commit()

    return response


@router.get("/session/{session_id}/qa-history")
async def get_qa_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve chat history for a session."""
    res = await db.execute(
        select(QAMessage)
        .where(QAMessage.session_id == session_id)
        .order_by(QAMessage.created_at)
    )
    messages = res.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "citations": json.loads(m.citations_json or "[]"),
            "grounded": m.grounded,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]
