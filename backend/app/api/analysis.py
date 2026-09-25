"""
API routes for document analysis (Phase 2).
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session
from app.models import Document, Clause, Finding, MissingClause
from app.agents.aggregator import analyze_document

logger = logging.getLogger("nyayalens.api.analysis")

router = APIRouter(prefix="/api", tags=["analysis"])


async def _run_analysis(doc_id: str):
    """Background task to run full document analysis."""
    async with async_session() as db:
        # Load document
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            logger.error("Document %s not found for analysis", doc_id)
            return

        # Load clauses
        result = await db.execute(
            select(Clause).where(Clause.document_id == doc_id).order_by(Clause.ordinal)
        )
        clauses_db = result.scalars().all()
        if not clauses_db:
            logger.error("No clauses found for document %s", doc_id)
            doc.status = "error"
            await db.commit()
            return

        clauses = [
            {
                "id": c.id,
                "ordinal": c.ordinal,
                "heading": c.heading,
                "text": c.text,
                "char_start": c.char_start,
                "char_end": c.char_end,
                "page": c.page,
                "content_hash": c.content_hash or "",
            }
            for c in clauses_db
        ]

        # Load session for language/reading level
        from app.models import Session
        sess_result = await db.execute(select(Session).where(Session.id == doc.session_id))
        session = sess_result.scalar_one_or_none()
        language = session.language if session else "en"
        reading_level = session.reading_level if session else "standard"

        try:
            doc.status = "analyzing"
            await db.commit()

            analysis = await analyze_document(
                doc_id=doc_id,
                raw_text=doc.raw_text,
                clauses=clauses,
                content_hash=doc.content_hash or "",
                language=language,
                reading_level=reading_level,
            )

            # Save findings
            for finding_data in analysis["findings"]:
                ordinal = finding_data["clause_ordinal"]
                # Find clause ID
                clause_obj = next((c for c in clauses_db if c.ordinal == ordinal), None)
                if not clause_obj:
                    continue

                finding = Finding(
                    clause_id=clause_obj.id,
                    clause_type=finding_data.get("clause_type", "general"),
                    plain_text=finding_data.get("plain_english", ""),
                    what_it_means=finding_data.get("what_it_means_for_you", ""),
                    risk_level=finding_data.get("risk_level", "low"),
                    risk_reasons_json=json.dumps(finding_data.get("risk_reasons", [])),
                    favors=finding_data.get("favors", "unclear"),
                    questions_json=json.dumps(finding_data.get("questions_to_ask", [])),
                    needs_review=finding_data.get("needs_lawyer_review", False),
                    confidence=finding_data.get("confidence", 0.0),
                    evidence_quote=finding_data.get("evidence_quote", ""),
                    verified=finding_data.get("verified", False),
                    verification_method=finding_data.get("verification_method"),
                )
                db.add(finding)

            # Save missing clauses
            for mc_data in analysis["missing_clauses"]:
                mc = MissingClause(
                    document_id=doc_id,
                    name=mc_data.get("name", ""),
                    why_it_matters=mc_data.get("why_it_matters", ""),
                    severity=mc_data.get("severity", "medium"),
                )
                db.add(mc)

            # Update document
            doc.doc_type = analysis["doc_type"]
            doc.key_facts_json = json.dumps(analysis["key_facts"])
            doc.redaction_map_json = json.dumps(analysis["redaction"])
            doc.status = "analyzed"
            await db.commit()

            logger.info(
                "Analysis complete for %s: score=%d, %d findings, %d missing clauses",
                doc_id, analysis["risk_score"], len(analysis["findings"]),
                len(analysis["missing_clauses"]),
            )

        except Exception as e:
            logger.error("Analysis failed for %s: %s", doc_id, e, exc_info=True)
            doc.status = "error"
            await db.commit()


@router.post("/documents/{doc_id}/analyze")
async def trigger_analysis(
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger document analysis as a background task."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    if doc.status == "analyzing":
        return {"status": "already_analyzing", "doc_id": doc_id}

    background_tasks.add_task(_run_analysis, doc_id)
    return {"status": "analysis_started", "doc_id": doc_id}


@router.get("/documents/{doc_id}/analysis")
async def get_analysis(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Get the full analysis results for a document."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    if doc.status not in ("analyzed",):
        return {
            "status": doc.status,
            "doc_id": doc_id,
            "message": f"Document is in '{doc.status}' state. "
            + ("Trigger analysis first." if doc.status == "segmented" else "Please wait."),
        }

    # Load clauses with findings
    result = await db.execute(
        select(Clause).where(Clause.document_id == doc_id).order_by(Clause.ordinal)
    )
    clauses = result.scalars().all()

    clauses_data = []
    for clause in clauses:
        # Load findings for this clause
        findings_result = await db.execute(
            select(Finding).where(Finding.clause_id == clause.id)
        )
        findings = findings_result.scalars().all()

        findings_data = []
        for f in findings:
            findings_data.append({
                "id": f.id,
                "clause_type": f.clause_type,
                "plain_text": f.plain_text,
                "what_it_means": f.what_it_means,
                "risk_level": f.risk_level,
                "risk_reasons": json.loads(f.risk_reasons_json),
                "favors": f.favors,
                "questions": json.loads(f.questions_json),
                "needs_review": f.needs_review,
                "confidence": f.confidence,
                "evidence_quote": f.evidence_quote,
                "verified": f.verified,
                "verification_method": f.verification_method,
            })

        clauses_data.append({
            "clause": {
                "id": clause.id,
                "ordinal": clause.ordinal,
                "heading": clause.heading,
                "text": clause.text,
                "char_start": clause.char_start,
                "char_end": clause.char_end,
                "page": clause.page,
            },
            "findings": findings_data,
        })

    # Load missing clauses
    mc_result = await db.execute(
        select(MissingClause).where(MissingClause.document_id == doc_id)
    )
    missing_clauses = [
        {"name": mc.name, "why_it_matters": mc.why_it_matters, "severity": mc.severity}
        for mc in mc_result.scalars().all()
    ]

    # Parse stored data
    key_facts = json.loads(doc.key_facts_json) if doc.key_facts_json else {}
    redaction_info = json.loads(doc.redaction_map_json) if doc.redaction_map_json else {}

    # Compute risk score from findings
    from app.agents.aggregator import compute_risk_score, compute_top_concerns
    findings_for_score = []
    for cd in clauses_data:
        for f in cd["findings"]:
            findings_for_score.append({**f, "clause_ordinal": cd["clause"]["ordinal"]})

    risk_score, risk_breakdown = compute_risk_score(
        findings_for_score, missing_clauses, []
    )
    top_concerns = compute_top_concerns(findings_for_score, missing_clauses, [])

    return {
        "document_id": doc_id,
        "doc_type": doc.doc_type,
        "status": doc.status,
        "key_facts": key_facts,
        "clauses": clauses_data,
        "missing_clauses": missing_clauses,
        "risk_score": risk_score,
        "risk_breakdown": risk_breakdown,
        "top_concerns": top_concerns,
        "redaction": redaction_info,
    }
