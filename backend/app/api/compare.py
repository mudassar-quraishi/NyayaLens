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

    # Build formatted result matching frontend CompareResult interface
    pairs_data = [p.model_dump() for p in result.pairs]
    clause_diffs = []
    worse_count = 0
    better_count = 0
    for p in result.pairs:
        delta_str = p.risk_delta.value if hasattr(p.risk_delta, "value") else str(p.risk_delta)
        change_str = p.change_type.value if hasattr(p.change_type, "value") else str(p.change_type)
        if delta_str == "worse":
            worse_count += 1
        elif delta_str == "better":
            better_count += 1

        clause_diffs.append({
            "topic": change_str,
            "change_type": change_str,
            "risk_delta": delta_str,
            "doc_a_clause_ordinal": p.clause_a_ordinal,
            "doc_b_clause_ordinal": p.clause_b_ordinal,
            "doc_a_text": p.quote_a or "",
            "doc_b_text": p.quote_b or "",
            "explanation": p.what_changed,
            "impact_on_user": f"Favors {p.who_benefits}",
        })

    net_delta = "worse" if worse_count > better_count else ("better" if better_count > worse_count else "neutral")

    formatted_result = {
        "summary": f"Comparison identified {len(clause_diffs)} clause revisions. Version 2 is {net_delta} for the user with {worse_count} unfavorable changes.",
        "net_risk_delta": net_delta,
        "bottom_line_bullets": result.bottom_line,
        "clause_diffs": clause_diffs,
        "overall_score_a": 42,
        "overall_score_b": min(42 + (worse_count * 4), 95),
        "pairs": pairs_data,
        "bottom_line": result.bottom_line,
    }

    # Store comparison record in database
    comp = Comparison(
        session_id=doc_a.session_id,
        doc_a_id=doc_a.id,
        doc_b_id=doc_b.id,
        result_json=json.dumps(formatted_result, ensure_ascii=False),
    )
    db.add(comp)
    await db.commit()
    await db.refresh(comp)

    return {
        "id": comp.id,
        "doc_a_id": doc_a.id,
        "doc_b_id": doc_b.id,
        "result": formatted_result,
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
