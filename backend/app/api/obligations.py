"""
API routes for Obligations, Calendar (.ics), and Lawyer Brief (.pdf) (Phase 6).
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document, Clause, Finding, MissingClause, Obligation
from app.agents.obligation_extractor import extract_obligations, generate_ics_calendar
from app.agents.brief_writer import generate_brief_pdf

logger = logging.getLogger("nyayalens.api.obligations")

router = APIRouter(prefix="/api/documents", tags=["obligations"])


@router.get("/{doc_id}/obligations")
async def get_document_obligations(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get obligations checklist grouped by 'You must', 'They must', 'Dates to remember'.
    """
    # Fetch document
    res = await db.execute(select(Document).where(Document.id == doc_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Fetch existing obligations from DB
    ob_res = await db.execute(select(Obligation).where(Obligation.document_id == doc_id))
    obs_db = ob_res.scalars().all()

    if not obs_db:
        # Load clauses
        c_res = await db.execute(
            select(Clause).where(Clause.document_id == doc_id).order_by(Clause.ordinal)
        )
        clauses = [
            {"ordinal": c.ordinal, "heading": c.heading, "text": c.text}
            for c in c_res.scalars().all()
        ]
        key_facts = json.loads(doc.key_facts_json or "{}")

        # Extract obligations
        extracted = await extract_obligations(
            doc_id=doc_id,
            clauses=clauses,
            doc_type=doc.doc_type,
            key_facts=key_facts,
            content_hash=doc.content_hash or "",
        )

        # Save to DB
        for item in extracted:
            ob = Obligation(
                document_id=doc_id,
                party=item.get("party", "you"),
                action=item.get("action", ""),
                due_kind=item.get("due_kind", "none"),
                due_value=item.get("due_value", ""),
                consequence=item.get("consequence_if_missed", ""),
                evidence_quote=item.get("evidence_quote", ""),
            )
            db.add(ob)
        await db.commit()

        # Reload
        ob_res = await db.execute(select(Obligation).where(Obligation.document_id == doc_id))
        obs_db = ob_res.scalars().all()

    all_obs = [
        {
            "id": o.id,
            "party": o.party,
            "action": o.action,
            "due_kind": o.due_kind,
            "due_value": o.due_value,
            "consequence": o.consequence,
            "evidence_quote": o.evidence_quote,
        }
        for o in obs_db
    ]

    # Group into checklist
    you_must = [o for o in all_obs if o["party"] in ("you", "both")]
    they_must = [o for o in all_obs if o["party"] in ("other", "both")]
    dates_to_remember = [o for o in all_obs if o["due_kind"] in ("absolute", "relative", "recurring")]

    return {
        "document_id": doc_id,
        "total_count": len(all_obs),
        "obligations": all_obs,
        "grouped": {
            "you_must": you_must,
            "they_must": they_must,
            "dates_to_remember": dates_to_remember,
        },
    }


@router.get("/{doc_id}/obligations.ics")
async def download_calendar_ics(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Download .ics iCalendar file with obligations and reminders.
    """
    # Fetch document
    res = await db.execute(select(Document).where(Document.id == doc_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Fetch obligations
    ob_res = await db.execute(select(Obligation).where(Obligation.document_id == doc_id))
    obs_db = ob_res.scalars().all()

    if not obs_db:
        # Generate inline
        c_res = await db.execute(
            select(Clause).where(Clause.document_id == doc_id).order_by(Clause.ordinal)
        )
        clauses = [
            {"ordinal": c.ordinal, "heading": c.heading, "text": c.text}
            for c in c_res.scalars().all()
        ]
        key_facts = json.loads(doc.key_facts_json or "{}")
        extracted = await extract_obligations(
            doc_id=doc_id,
            clauses=clauses,
            doc_type=doc.doc_type,
            key_facts=key_facts,
            content_hash=doc.content_hash or "",
        )
        obligations_list = extracted
    else:
        obligations_list = [
            {
                "party": o.party,
                "action": o.action,
                "due_kind": o.due_kind,
                "due_value": o.due_value,
                "consequence_if_missed": o.consequence,
                "clause_id": "",
            }
            for o in obs_db
        ]

    key_facts = json.loads(doc.key_facts_json or "{}")
    effective_date = key_facts.get("effective_date")

    ics_bytes = generate_ics_calendar(
        doc_title=doc.filename,
        obligations=obligations_list,
        effective_date_str=effective_date,
    )

    clean_name = doc.filename.rsplit(".", 1)[0]
    return Response(
        content=ics_bytes,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="{clean_name}_deadlines.ics"',
        },
    )


@router.get("/{doc_id}/brief.pdf")
async def download_lawyer_brief_pdf(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate and download the 1-page Lawyer Brief in PDF format.
    """
    # Fetch document
    res = await db.execute(select(Document).where(Document.id == doc_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Fetch findings
    f_res = await db.execute(
        select(Finding, Clause.ordinal)
        .join(Clause, Finding.clause_id == Clause.id)
        .where(Clause.document_id == doc_id)
        .order_by(Clause.ordinal)
    )
    findings_rows = f_res.all()
    findings_list = [
        {
            "clause_ordinal": ordinal,
            "clause_type": f.clause_type,
            "what_it_means": f.what_it_means,
            "risk_level": f.risk_level,
            "evidence_quote": f.evidence_quote,
        }
        for f, ordinal in findings_rows
    ]

    # Fetch missing clauses
    mc_res = await db.execute(
        select(MissingClause).where(MissingClause.document_id == doc_id)
    )
    missing_clauses = [
        {"name": mc.name, "why_it_matters": mc.why_it_matters, "severity": mc.severity}
        for mc in mc_res.scalars().all()
    ]

    key_facts = json.loads(doc.key_facts_json or "{}")

    # Compute risk score if needed
    high_count = sum(1 for f in findings_list if f["risk_level"] == "high")
    med_count = sum(1 for f in findings_list if f["risk_level"] == "medium")
    risk_score = min(100, (high_count * 25) + (med_count * 10))

    pdf_bytes = generate_brief_pdf(
        filename=doc.filename,
        doc_type=doc.doc_type,
        key_facts=key_facts,
        risk_score=risk_score,
        top_concerns=[f["what_it_means"] for f in findings_list if f["risk_level"] == "high"][:5],
        findings=findings_list,
        missing_clauses=missing_clauses,
    )

    clean_name = doc.filename.rsplit(".", 1)[0]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{clean_name}_lawyer_brief.pdf"',
        },
    )
