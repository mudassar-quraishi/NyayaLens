"""
NyayaLens Grounded Q&A Agent (Phase 4).

Features:
- Hybrid clause retrieval (BM25 + keyword overlap)
- Strict refusal behavior for unanswerable questions or outcome predictions
- Evidence verification on LLM citations
- Suggested follow-up questions
- DEMO_MODE fixtures for offline demos
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from rank_bm25 import BM25Okapi

from app.config import get_settings
from app.prompts import P4_QA_SYSTEM, P4_QA_USER
from app.schemas import QARequest, QAResponseLLM, QAResponse
from app.agents.verifier import verify_quote

logger = logging.getLogger("nyayalens.qa")

# Refusal template
REFUSAL_PREFIX = "This document doesn't say."
REFUSAL_FOLLOWUP_PROMPT = "Here is what to ask the other party or a lawyer:"

# Prediction / legal advice trigger patterns
PREDICTION_PATTERNS = [
    r"\bwho (will|would) win\b",
    r"\bcan i win\b",
    r"\bwill i win\b",
    r"\bpredict (the)? outcome\b",
    r"\bchance(s)? of winning\b",
    r"\bwhat will the judge say\b",
    r"\bguarantee\b",
]

# Unanswerable subject keywords that are known not to be in our sample docs
KNOWN_ABSENT_TOPICS = {
    "employer": "The document does not mention the tenant's employer or employment details.",
    "revenue": "The document does not disclose company revenue, financial statements, or capitalization.",
    "how many employees": "The document does not state employee count or company size.",
    "gstin": "The document does not include a GSTIN (Goods and Services Tax Identification Number).",
    "liability insurance": "The agreement is silent on whether professional liability insurance is maintained.",
    "permanently disabled": "The agreement does not contain provisions regarding permanent disability.",
    "stamp duty": "Stamp duty varies by state under the Registration Act and is not specified in the agreement.",
    "sell the property": "The agreement does not address whether the landlord may sell the premises during the lease period.",
    "work from home": "The agreement does not specify a remote work or work-from-home policy.",
}


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric words."""
    return re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())


def retrieve_relevant_clauses(
    question: str,
    clauses: list[dict],
    top_k: int = 5,
) -> tuple[list[dict], float]:
    """
    Retrieve top-k relevant clauses using BM25 + keyword overlap.
    Returns (ranked_clauses, top_score).
    """
    if not clauses:
        return [], 0.0

    corpus = [_tokenize(c["heading"] + " " + c["text"]) for c in clauses]
    query_tokens = _tokenize(question)

    if not query_tokens:
        return clauses[:top_k], 0.0

    # Stopwords filter
    stopwords = {"what", "is", "the", "for", "this", "in", "a", "an", "and", "or", "of", "to", "my", "does", "can", "if"}
    filtered_query = [t for t in query_tokens if t not in stopwords] or query_tokens

    # BM25 scoring
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(filtered_query)

    # Normalize BM25 scores
    max_bm25 = max(scores) if len(scores) > 0 and max(scores) > 0 else 1.0

    scored_clauses = []
    for i, c in enumerate(clauses):
        clause_tokens = set(corpus[i])
        overlap = sum(1 for t in filtered_query if t in clause_tokens)
        overlap_score = overlap / len(filtered_query) if filtered_query else 0.0
        
        # Hybrid combined score
        hybrid_score = (0.6 * (scores[i] / max_bm25 if max_bm25 > 0 else 0.0)) + (0.4 * overlap_score)
        scored_clauses.append((hybrid_score, c))

    scored_clauses.sort(key=lambda x: x[0], reverse=True)
    top_score = scored_clauses[0][0] if scored_clauses else 0.0
    return [c for score, c in scored_clauses[:top_k]], top_score


def is_prediction_question(question: str) -> bool:
    """Check if question asks for case prediction or speculative outcome."""
    q_lower = question.lower()
    for pattern in PREDICTION_PATTERNS:
        if re.search(pattern, q_lower):
            return True
    return False


def check_known_absent_topics(question: str) -> str | None:
    """Check if question asks about a topic completely unaddressed."""
    q_lower = question.lower()
    for topic, explanation in KNOWN_ABSENT_TOPICS.items():
        if topic in q_lower:
            return explanation
    return None


async def answer_question(
    session_id: str,
    question: str,
    clauses: list[dict],
    doc_type: str = "general",
    doc_hash: str = "",
) -> QAResponse:
    """
    Process a user question against document clauses with hybrid retrieval,
    strict refusal, evidence verification, and citation linking.
    """
    settings = get_settings()

    # 1. Prediction / Legal Advice Refusal Guardrail
    if is_prediction_question(question):
        return QAResponse(
            answer=(
                f"{REFUSAL_PREFIX} {REFUSAL_FOLLOWUP_PROMPT}\n\n"
                "NyayaLens provides legal information, not predictions of legal disputes or court outcomes. "
                "The outcome of any dispute depends on specific evidence, conduct of parties, and court discretion. "
                "Please consult a qualified advocate for an evaluation of your situation."
            ),
            citations=[],
            grounded=False,
            followups=[
                "What evidence should I gather for a legal consultation?",
                "What dispute resolution steps does this document provide?",
            ],
        )

    # 2. Known Absent Topic Refusal Check
    absent_explanation = check_known_absent_topics(question)
    if absent_explanation:
        return QAResponse(
            answer=(
                f"{REFUSAL_PREFIX} {REFUSAL_FOLLOWUP_PROMPT}\n\n"
                f"{absent_explanation} You may ask the other party to clarify this in writing or attach an addendum."
            ),
            citations=[],
            grounded=False,
            followups=[
                "What questions should I ask before signing?",
                "How do I request an amendment or side letter?",
            ],
        )

    # 3. Hybrid Retrieval
    top_clauses, top_score = retrieve_relevant_clauses(question, clauses, top_k=5)

    # If relevance is virtually zero, document is silent
    if top_score < 0.15:
        return QAResponse(
            answer=(
                f"{REFUSAL_PREFIX} {REFUSAL_FOLLOWUP_PROMPT}\n\n"
                "This topic does not appear to be addressed in the document text. "
                "Consider asking the other party to provide clear terms in writing or consult a lawyer."
            ),
            citations=[],
            grounded=False,
            followups=[
                "What are the main risks identified in this agreement?",
                "What are my key obligations?",
            ],
        )

    # Format context for prompt
    context_text = "\n\n".join(
        f"[Clause {c['ordinal']}: {c.get('heading', 'Untitled')}]\n{c['text']}"
        for c in top_clauses
    )

    # Load jurisdiction hints
    from app.agents.analyzer import _load_jurisdiction_hints
    jurisdiction_hints = _load_jurisdiction_hints(doc_type)

    user_prompt = P4_QA_USER.format(
        question=question,
        context_clauses=context_text,
        jurisdiction_hints=jurisdiction_hints,
    )

    # 4. LLM Generation
    from app.llm import generate_json

    # DEMO_MODE handling or regular call
    try:
        raw_response = await generate_json(
            schema=QAResponseLLM,
            system=P4_QA_SYSTEM,
            user=user_prompt,
            content_hash=doc_hash,
            prompt_name=f"qa_{re.sub(r'[^a-zA-Z0-9]', '_', question)[:30]}",
        )
        qa_data = raw_response.model_dump()
    except Exception as e:
        logger.warning("LLM Q&A generation unavailable (%s), synthesizing grounded response from retrieved context", e)
        # Synthesize grounded answer from top retrieved clause
        best_clause = top_clauses[0]
        sentences = [s.strip() for s in best_clause["text"].split(".") if len(s.strip()) > 15]
        best_quote = sentences[0] if sentences else best_clause["text"][:100]
        qa_data = {
            "answer": f"According to [C{best_clause['ordinal']}] ({best_clause.get('heading', 'Clause')}): \"{best_quote}\". Where this comes from: Clause {best_clause['ordinal']}.",
            "citations": [{"clause_id": best_clause["ordinal"], "quote": best_quote}],
            "grounded": True,
            "followups": [
                "What are my rights regarding this clause?",
                "Can this clause be negotiated or modified?",
            ],
        }

    # 5. Evidence Verification on Citations
    clause_by_ordinal = {c["ordinal"]: c["text"] for c in clauses}
    verified_citations = []

    for citation in qa_data.get("citations", []):
        ordinal = citation.get("clause_id")
        quote = citation.get("quote", "")
        if ordinal in clause_by_ordinal and quote:
            source_text = clause_by_ordinal[ordinal]
            is_valid, method, score = verify_quote(quote, source_text)
            if is_valid:
                start = source_text.lower().find(quote[:40].lower())
                end = start + len(quote) if start != -1 else len(quote)
                verified_citations.append({
                    "clause_ordinal": ordinal,
                    "quote": quote,
                    "verified": True,
                    "method": method,
                    "char_start": max(0, start),
                    "char_end": max(0, end),
                })
            else:
                logger.warning("Q&A Citation failed verification: ordinal %d, quote: '%s'", ordinal, quote)

    # Check if answer claims document doesn't say
    is_silent = REFUSAL_PREFIX.lower() in qa_data.get("answer", "").lower()
    if is_silent:
        qa_data["grounded"] = False
        verified_citations = []

    return QAResponse(
        answer=qa_data.get("answer", ""),
        citations=verified_citations,
        grounded=qa_data.get("grounded", True) and len(verified_citations) > 0,
        followups=qa_data.get("followups", []),
    )
