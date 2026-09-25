"""
API routes for document comparison (Phase 5).
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document, Clause, Comparison
from app.schemas import CompareRequest, ComparisonResultLLM
from app.agents.comparator import compare_documents

logger = logging.getLogger("nyayalens.api.compare")

router = APIRouter(prefix="/api", tags=["compare"])


@router.post("/compare")
async def start_comparison(
    req: CompareRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Compare two documents semantically.
    Aligns clauses, detects risk changes, and generates 5-bullet bottom line.
    """
    # Fetch Document A
    res_a = await db.execute(select(Document).where(Document.id == req.doc_a))
    doc_a = res_a.scalar_one_or_none()
    if not doc_a:
        raise HTTPException(404, f"Document A ({req.doc_a}) not found")

    # Fetch Document B
    res_b = await db.execute(select(Document).where(Document.id == req.doc_b))
    doc_b = res_b.scalar_one_or_none()
    if not doc_b:
        raise HTTPException(404, f"Document B ({req.doc_b}) not found")

    # Load clauses for Document A
    ca_res = await db.execute(select(Clause).where(Clause.document_id == doc_a.id).order_by(Clause.ordinal))
    clauses_a = [
        {"id": c.id, "ordinal": c.ordinal, "heading": c.heading, "text": c.text, "char_start": c.char_start, "char_end": c.char_end}
        for c in ca_res.scalars().all()
    ]

    # Load clauses for Document B
    cb_res = await db.execute(select(Clause).where(Clause.document_id == doc_b.id).order_by(Clause.ordinal))
    clauses_b = [
        {"id": c.id, "ordinal": c.ordinal, "heading": c.heading, "text": c.text, "char_start": c.char_start, "char_end": c.char_end}
        for c in cb_res.scalars().all()
    ]

    result = await compare_documents(
        doc_a_id=doc_a.id,
        doc_b_id=doc_b.id,
        clauses_a=clauses_a,
        clauses_b=clauses_b,
        doc_a_text=doc_a.raw_text,
        doc_b_text=doc_b.raw_text,
        user_role="freelancer",
        content_hash_a=doc_a.content_hash or "",
        content_hash_b=doc_b.content_hash or "",
    )

    # Store comparison record in database
    comp = Comparison(
        session_id=doc_a.session_id,
        doc_a_id=doc_a.id,
        doc_b_id=doc_b.id,
        result_json=result.model_dump_json(),
    )
    db.add(comp)
    await db.commit()
    await db.refresh(comp)

    return {
        "id": comp.id,
        "doc_a_id": doc_a.id,
        "doc_b_id": doc_b.id,
        "result": result.model_dump(),
    }


@router.get("/compare/{comp_id}")
async def get_comparison(
    comp_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve an existing comparison result."""
    res = await db.execute(select(Comparison).where(Comparison.id == comp_id))
    comp = res.scalar_one_or_none()
    if not comp:
        raise HTTPException(404, "Comparison not found")

    return {
        "id": comp.id,
        "session_id": comp.session_id,
        "doc_a_id": comp.doc_a_id,
        "doc_b_id": comp.doc_b_id,
        "result": json.loads(comp.result_json),
    }
