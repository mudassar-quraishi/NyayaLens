"""
Aggregator agent — combines clause-level findings into document-level scores.

Computes: overall risk score (0-100 with transparent breakdown), top concerns,
runs missing-clause scan, and produces the final analysis result.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.agents.analyzer import analyze_clause, detect_doc_type, extract_key_facts, generate_glossary, get_suggested_questions
from app.agents.redactor import redact_pii, RedactionResult
from app.agents.verifier import verify_finding
from app.llm import generate_json
from app.prompts import P2_MISSING_CLAUSE_SYSTEM, P2_MISSING_CLAUSE_USER
from app.schemas import MissingClauseScanLLM, ClauseAnalysisLLM

logger = logging.getLogger("nyayalens.aggregator")


async def run_missing_clause_scan(
    clauses: list[dict],
    key_facts: dict,
    doc_type: str,
    content_hash: str,
) -> MissingClauseScanLLM:
    """Run the P2 missing-clause and inconsistency scan."""
    clause_list = "\n".join(
        f"[C{c['ordinal']}] {c['heading']}: {c['text'][:150]}..."
        for c in clauses
    )

    result = await generate_json(
        schema=MissingClauseScanLLM,
        system=P2_MISSING_CLAUSE_SYSTEM.format(doc_type=doc_type),
        user=P2_MISSING_CLAUSE_USER.format(
            clause_list=clause_list,
            key_facts=json.dumps(key_facts, ensure_ascii=False),
        ),
        prompt_name="missing_clauses",
        content_hash=content_hash,
    )

    logger.info(
        "Missing clause scan: %d missing, %d inconsistencies",
        len(result.missing_clauses), len(result.inconsistencies),
    )
    return result


def compute_risk_score(
    findings: list[dict],
    missing_clauses: list[dict],
    inconsistencies: list[dict],
) -> tuple[int, dict]:
    """
    Compute an overall risk score 0-100 with transparent breakdown.

    Breakdown components:
    - clause_risk: weighted sum of clause risks (max 40 points)
    - missing_protections: points per missing protection (max 30 points)
    - inconsistencies: points per inconsistency (max 15 points)
    - one_sidedness: bonus for heavily one-sided clauses (max 15 points)
    """
    # Clause risk component
    risk_weights = {"high": 3, "medium": 1.5, "low": 0.5}
    total_clause_weight = sum(
        risk_weights.get(f.get("risk_level", "low"), 0.5)
        for f in findings
    )
    max_possible = len(findings) * 3 if findings else 1
    clause_risk_pct = min(total_clause_weight / max_possible, 1.0)
    clause_risk_score = int(clause_risk_pct * 40)

    # Missing protections component
    severity_weights = {"high": 4, "medium": 2, "low": 1}
    missing_weight = sum(
        severity_weights.get(mc.get("severity", "medium"), 2)
        for mc in missing_clauses
    )
    missing_score = min(int(missing_weight * 3), 30)

    # Inconsistencies component
    inconsistency_score = min(len(inconsistencies) * 5, 15)

    # One-sidedness component
    one_sided_count = sum(
        1 for f in findings
        if f.get("favors") in ("party_a",) and f.get("risk_level") in ("high", "medium")
    )
    one_sided_score = min(one_sided_count * 3, 15)

    total = min(clause_risk_score + missing_score + inconsistency_score + one_sided_score, 100)

    breakdown = {
        "clause_risk": {"score": clause_risk_score, "max": 40, "detail": f"{sum(1 for f in findings if f.get('risk_level') == 'high')} high-risk clauses"},
        "missing_protections": {"score": missing_score, "max": 30, "detail": f"{len(missing_clauses)} missing protections"},
        "inconsistencies": {"score": inconsistency_score, "max": 15, "detail": f"{len(inconsistencies)} inconsistencies found"},
        "one_sidedness": {"score": one_sided_score, "max": 15, "detail": f"{one_sided_count} one-sided clauses"},
    }

    return total, breakdown


def compute_top_concerns(
    findings: list[dict],
    missing_clauses: list[dict],
    inconsistencies: list[dict],
) -> list[str]:
    """Extract top 5 concerns from findings, missing clauses, and inconsistencies."""
    concerns: list[tuple[int, str]] = []

    # High-risk findings
    priority = {"high": 3, "medium": 2, "low": 1}
    for f in findings:
        if f.get("risk_level") in ("high", "medium"):
            reasons = f.get("risk_reasons", [])
            reason_text = reasons[0] if reasons else f.get("plain_text", "")[:100]
            clause_ref = f"[C{f.get('clause_ordinal', '?')}]"
            concerns.append((
                priority.get(f.get("risk_level", "low"), 1),
                f"{clause_ref} {reason_text}",
            ))

    # Missing clauses
    for mc in missing_clauses:
        sev = priority.get(mc.get("severity", "medium"), 2)
        concerns.append((sev, f"Missing: {mc.get('name', '')} — {mc.get('why_it_matters', '')}"))

    # Inconsistencies
    for inc in inconsistencies:
        concerns.append((3, f"Inconsistency: {inc.get('description', '')}"))

    # Sort by priority (descending) and take top 5
    concerns.sort(key=lambda x: x[0], reverse=True)
    return [c[1] for c in concerns[:5]]


async def analyze_document(
    doc_id: str,
    raw_text: str,
    clauses: list[dict],
    content_hash: str,
    language: str = "en",
    reading_level: str = "standard",
    progress_callback=None,
) -> dict:
    """
    Full document analysis pipeline:
    1. Detect doc type
    2. Extract key facts
    3. Redact PII
    4. Analyze each clause (with concurrency cap via LLM semaphore)
    5. Verify evidence quotes
    6. Run missing-clause scan
    7. Compute risk score and top concerns
    8. Generate glossary
    """

    # 1. Detect document type
    if progress_callback:
        await progress_callback("detecting", "Detecting document type...", 0.05)

    doc_type_result = await detect_doc_type(raw_text, content_hash)
    doc_type = doc_type_result.doc_type.value
    user_role = doc_type_result.user_role

    # 2. Extract key facts
    if progress_callback:
        await progress_callback("extracting", "Extracting key facts...", 0.10)

    key_facts = await extract_key_facts(raw_text, doc_type, content_hash)
    key_facts_dict = key_facts.model_dump()

    # 3. Redact PII
    if progress_callback:
        await progress_callback("redacting", "Masking personal information...", 0.15)

    redaction = redact_pii(raw_text)

    # Build redacted clause texts (what the LLM will see)
    redacted_clauses: dict[int, str] = {}
    original_clauses: dict[int, str] = {}
    for clause in clauses:
        ordinal = clause["ordinal"]
        original_clauses[ordinal] = clause["text"]
        # Find the clause text within the redacted document
        # Use char offsets to slice the redacted text
        # (This is approximate — for exact mapping, we'd need per-clause redaction)
        redacted_clause = redaction.redacted_text[
            max(0, clause.get("char_start", 0)) : clause.get("char_end", len(redaction.redacted_text))
        ]
        if len(redacted_clause.strip()) < 10:
            # Fallback: redact just this clause's text independently
            clause_redaction = redact_pii(clause["text"])
            redacted_clause = clause_redaction.redacted_text
        redacted_clauses[ordinal] = redacted_clause

    # 4. Analyze each clause
    if progress_callback:
        await progress_callback("analyzing", "Analyzing clauses...", 0.20)

    # Build context headings
    headings = [f"C{c['ordinal']}: {c['heading']}" for c in clauses if c.get("heading")]
    context_headings_str = "\n".join(headings)

    # Analyze in parallel (concurrency capped by LLM semaphore)
    async def _analyze_one(clause: dict) -> dict:
        ordinal = clause["ordinal"]
        clause_text = redacted_clauses.get(ordinal, clause["text"])

        try:
            result = await analyze_clause(
                clause_ordinal=ordinal,
                clause_text=clause_text,
                clause_hash=clause.get("content_hash", ""),
                doc_type=doc_type,
                user_role=user_role,
                key_facts=key_facts_dict,
                context_headings=context_headings_str,
                language=language,
                reading_level=reading_level,
                content_hash=content_hash,
            )
            return {
                "clause_ordinal": ordinal,
                **result.model_dump(),
            }
        except Exception as e:
            logger.error("Failed to analyze clause %d: %s", ordinal, e)
            return {
                "clause_ordinal": ordinal,
                "clause_type": "error",
                "plain_english": f"Analysis failed: {e}",
                "what_it_means_for_you": "Could not analyze this clause.",
                "risk_level": "medium",
                "risk_reasons": ["Analysis failed — manual review recommended"],
                "favors": "unclear",
                "questions_to_ask": [],
                "needs_lawyer_review": True,
                "confidence": 0.0,
                "evidence_quote": "",
            }

    tasks = [_analyze_one(c) for c in clauses]
    findings = await asyncio.gather(*tasks)

    # Update progress
    if progress_callback:
        await progress_callback("verifying", "Verifying evidence quotes...", 0.70)

    # 5. Verify evidence quotes
    verified_count = 0
    for finding in findings:
        ordinal = finding["clause_ordinal"]
        quote = finding.get("evidence_quote", "")
        original_text = original_clauses.get(ordinal, "")
        redacted_text = redacted_clauses.get(ordinal)

        if quote:
            verified, method, score = verify_finding(quote, original_text, redacted_text)
            finding["verified"] = verified
            finding["verification_method"] = method
            finding["verification_score"] = score
            if verified:
                verified_count += 1
            else:
                logger.warning("Clause %d evidence FAILED verification: %.1f", ordinal, score)
        else:
            finding["verified"] = False
            finding["verification_method"] = "no_quote"
            finding["verification_score"] = 0.0

    total_with_quotes = sum(1 for f in findings if f.get("evidence_quote"))
    verification_rate = verified_count / total_with_quotes if total_with_quotes > 0 else 0.0
    logger.info("Evidence verification rate: %.1f%% (%d/%d)", verification_rate * 100, verified_count, total_with_quotes)

    # 6. Missing clause scan
    if progress_callback:
        await progress_callback("scanning", "Checking for missing protections...", 0.80)

    missing_result = await run_missing_clause_scan(
        clauses, key_facts_dict, doc_type, content_hash
    )

    missing_clauses = [mc.model_dump() for mc in missing_result.missing_clauses]
    inconsistencies = [inc.model_dump() for inc in missing_result.inconsistencies]

    # 7. Compute risk score
    if progress_callback:
        await progress_callback("scoring", "Computing risk score...", 0.90)

    risk_score, risk_breakdown = compute_risk_score(findings, missing_clauses, inconsistencies)
    top_concerns = compute_top_concerns(findings, missing_clauses, inconsistencies)

    # 8. Generate glossary
    if progress_callback:
        await progress_callback("glossary", "Building glossary...", 0.95)

    try:
        glossary = await generate_glossary(raw_text, content_hash)
        glossary_entries = [e.model_dump() for e in glossary.entries]
    except Exception as e:
        logger.warning("Glossary generation failed: %s", e)
        glossary_entries = []

    # Done
    if progress_callback:
        await progress_callback("done", "Analysis complete!", 1.0)

    return {
        "document_id": doc_id,
        "doc_type": doc_type,
        "user_role": user_role,
        "key_facts": key_facts_dict,
        "findings": findings,
        "missing_clauses": missing_clauses,
        "inconsistencies": inconsistencies,
        "risk_score": risk_score,
        "risk_breakdown": risk_breakdown,
        "top_concerns": top_concerns,
        "verification_rate": verification_rate,
        "glossary": glossary_entries,
        "suggested_questions": get_suggested_questions(doc_type),
        "redaction": {
            "pii_found": redaction.pii_found,
            "redaction_map": {k: "***" for k in redaction.redaction_map},  # Don't expose values in API
            "note": "Names and addresses are NOT masked — only structured identifiers (Aadhaar, PAN, phone, email, bank accounts).",
        },
    }
