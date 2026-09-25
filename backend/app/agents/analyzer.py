"""
Analyzer agent — per-clause risk analysis using LLM.

Uses P1_CLAUSE_ANALYZER prompt. Respects clause-hash caching and concurrency cap.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.llm import generate_json
from app.prompts import P1_CLAUSE_ANALYZER_SYSTEM, P1_CLAUSE_ANALYZER_USER
from app.schemas import ClauseAnalysisLLM, DocTypeLLM, KeyFactsLLM, GlossaryLLM
from app.prompts import P_DOCTYPE_SYSTEM, P_DOCTYPE_USER, P_KEYFACTS_SYSTEM, P_KEYFACTS_USER
from app.prompts import P_GLOSSARY_SYSTEM, P_GLOSSARY_USER
from app.config import get_settings

logger = logging.getLogger("nyayalens.analyzer")


def _load_jurisdiction_hints(doc_type: str) -> str:
    """Load jurisdiction hints filtered by document type."""
    settings = get_settings()
    path = settings.jurisdiction_dir / "india.json"
    if not path.exists():
        return "No jurisdiction hints available."

    hints = json.loads(path.read_text(encoding="utf-8"))
    filtered = [h for h in hints if doc_type in h.get("applies_to_doc_types", [])]
    if not filtered:
        return "No specific jurisdiction hints for this document type."

    parts = []
    for h in filtered:
        parts.append(
            f"- {h['topic']}: {h['general_rule']} "
            f"(Source: {h['source_name']}. {h['verify_note']})"
        )
    return "\n".join(parts)


async def detect_doc_type(raw_text: str, content_hash: str) -> DocTypeLLM:
    """Detect the document type and user role."""
    preview = raw_text[:3000]
    result = await generate_json(
        schema=DocTypeLLM,
        system=P_DOCTYPE_SYSTEM,
        user=P_DOCTYPE_USER.format(text_preview=preview),
        prompt_name="doc_type",
        content_hash=content_hash,
    )
    logger.info("Detected doc_type=%s, user_role=%s (confidence=%.2f)",
                result.doc_type, result.user_role, result.confidence)
    return result


async def extract_key_facts(raw_text: str, doc_type: str, content_hash: str) -> KeyFactsLLM:
    """Extract key facts from the document."""
    result = await generate_json(
        schema=KeyFactsLLM,
        system=P_KEYFACTS_SYSTEM.format(doc_type=doc_type),
        user=P_KEYFACTS_USER.format(raw_text=raw_text[:8000]),
        prompt_name="key_facts",
        content_hash=content_hash,
    )
    logger.info("Extracted key facts: %d parties, date=%s", len(result.parties), result.effective_date)
    return result


async def generate_glossary(raw_text: str, content_hash: str) -> GlossaryLLM:
    """Generate a glossary of legal terms for hover definitions."""
    result = await generate_json(
        schema=GlossaryLLM,
        system=P_GLOSSARY_SYSTEM,
        user=P_GLOSSARY_USER.format(raw_text=raw_text[:8000]),
        prompt_name="glossary",
        content_hash=content_hash,
    )
    logger.info("Generated glossary with %d entries", len(result.entries))
    return result


async def analyze_clause(
    clause_ordinal: int,
    clause_text: str,
    clause_hash: str,
    doc_type: str,
    user_role: str,
    key_facts: dict,
    context_headings: str,
    language: str = "en",
    reading_level: str = "standard",
    content_hash: str | None = None,
) -> ClauseAnalysisLLM:
    """
    Analyze a single clause for risks, plain-language rewrite, etc.

    Uses clause_hash for caching — if the same clause appears again, the cached
    result is served from fixtures.
    """
    jurisdiction_hints = _load_jurisdiction_hints(doc_type)

    system = P1_CLAUSE_ANALYZER_SYSTEM.format(
        doc_type=doc_type,
        user_role=user_role,
        reading_level=reading_level,
        language=language,
    )
    user = P1_CLAUSE_ANALYZER_USER.format(
        ordinal=clause_ordinal,
        clause_text=clause_text,
        context_headings=context_headings,
        key_facts=json.dumps(key_facts, ensure_ascii=False),
        jurisdiction_hints=jurisdiction_hints,
    )

    # Use clause_hash or content_hash as cache key
    cache_hash = clause_hash or content_hash or ""
    try:
        result = await generate_json(
            schema=ClauseAnalysisLLM,
            system=system,
            user=user,
            prompt_name=f"clause_analysis_{clause_ordinal}",
            content_hash=cache_hash,
        )
    except Exception:
        result = await generate_json(
            schema=ClauseAnalysisLLM,
            system=system,
            user=user,
            prompt_name=f"clause_{clause_ordinal}",
            content_hash=cache_hash,
        )

    return result


# ── Suggested Question Chips (per doc type) ───────────────────────

SUGGESTED_QUESTIONS: dict[str, list[str]] = {
    "rental": [
        "When must my deposit be returned?",
        "Can the landlord increase rent during the lease?",
        "What happens if I need to leave early?",
        "Can the landlord enter my apartment without notice?",
        "Who pays for repairs?",
        "What is the notice period to vacate?",
    ],
    "employment": [
        "Is the non-compete clause enforceable?",
        "What happens to my personal side projects?",
        "Can they change my role without my consent?",
        "What is the notice period and can I buy it out?",
        "Am I entitled to overtime pay?",
        "What are the termination conditions?",
    ],
    "freelance": [
        "When will I get paid?",
        "Who owns the work I create?",
        "Can they change the scope without paying more?",
        "What is my liability cap?",
        "How can I terminate this contract?",
        "Is there a non-compete restriction?",
    ],
    "nda": [
        "How long does the NDA last?",
        "What information is excluded from confidentiality?",
        "What happens if I accidentally disclose information?",
        "Can I talk about the existence of this NDA?",
    ],
    "loan": [
        "What is the total interest I will pay?",
        "Are there prepayment penalties?",
        "What happens if I miss a payment?",
        "Can the lender change the interest rate?",
    ],
    "tos": [
        "Can they change the terms without telling me?",
        "What data do they collect?",
        "How can I cancel my account?",
        "Where do disputes get resolved?",
    ],
    "other": [
        "What are my main obligations?",
        "What are the risks I should know about?",
        "Are there any deadlines I need to watch?",
        "What happens if either party breaks the agreement?",
    ],
}


def get_suggested_questions(doc_type: str) -> list[str]:
    """Return suggested Q&A question chips for a document type."""
    return SUGGESTED_QUESTIONS.get(doc_type, SUGGESTED_QUESTIONS["other"])
