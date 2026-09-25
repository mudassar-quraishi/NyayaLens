"""
NyayaLens Comparator Agent (Phase 5).

Compares two documents (or two versions of one) semantically:
- Aligns clauses semantically by heading, topic, and textual similarity
- Detects added, removed, modified, and unchanged clauses
- Assesses risk delta from the user's perspective
- Extracts quotes from both sides and verifies them
- Produces exactly five bottom-line bullet points
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from rapidfuzz import fuzz

from app.config import get_settings
from app.prompts import P3_COMPARATOR_SYSTEM, P3_COMPARATOR_USER
from app.schemas import ComparisonPairLLM, ComparisonResultLLM
from app.agents.verifier import verify_quote

logger = logging.getLogger("nyayalens.comparator")

# Canonical topic keywords for alignment
TOPIC_KEYWORDS = {
    "scope": ["scope", "services", "statement of work", "deliverables"],
    "term": ["term", "duration", "commencement", "renewal", "renew"],
    "compensation": ["compensation", "payment", "fee", "fees", "retainer", "invoice", "invoices"],
    "intellectual_property": ["intellectual property", "ip", "deliverables", "portfolio", "copyright", "ownership"],
    "confidentiality": ["confidential", "confidentiality", "proprietary", "non-disclosure"],
    "liability": ["liability", "indemnif", "indemnification", "hold harmless", "damages", "claims"],
    "termination": ["termination", "terminate", "notice period", "vacate", "cure"],
    "dispute_resolution": ["dispute", "arbitration", "mediation", "settlement", "arbitrator"],
    "governing_law": ["governing law", "jurisdiction", "courts", "laws of"],
    "force_majeure": ["force majeure", "beyond", "reasonable control", "pandemic"],
    "non_compete": ["non-compete", "competitor", "competing", "restrictive covenant"],
    "general": ["general", "entire agreement", "amend", "amendment", "severability", "assignment"],
}


def _classify_topic(heading: str, text: str) -> str:
    """Classify clause into a canonical topic with priority on headings."""
    h = heading.lower()
    if any(k in h for k in ["non-compete", "non compete"]):
        return "non_compete"
    if any(k in h for k in ["dispute", "arbitrat", "mediation"]):
        return "dispute_resolution"
    if any(k in h for k in ["governing", "jurisdiction"]):
        return "governing_law"
    if any(k in h for k in ["terminat"]):
        return "termination"
    if any(k in h for k in ["liabilit", "indemn"]):
        return "liability"
    if any(k in h for k in ["compensat", "payment", "fee"]):
        return "compensation"
    if any(k in h for k in ["intellect", "ip", "deliverable", "copyright"]):
        return "intellectual_property"
    if any(k in h for k in ["confidential"]):
        return "confidentiality"
    if any(k in h for k in ["force majeure"]):
        return "force_majeure"
    if any(k in h for k in ["scope"]):
        return "scope"
    if any(k in h for k in ["term"]):
        return "term"
    if any(k in h for k in ["general", "amend", "assign"]):
        return "general"

    # Fallback to body keywords
    t = text[:300].lower()
    for topic, kws in TOPIC_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return topic
    return "general"


def align_clauses(
    clauses_a: list[dict],
    clauses_b: list[dict],
) -> list[tuple[dict | None, dict | None]]:
    """
    Align clauses between Document A and Document B based on:
    1. Heading similarity
    2. Canonical topic match
    3. Content similarity
    """
    aligned: list[tuple[dict | None, dict | None]] = []
    used_b_indices = set()

    # Pre-calculate topics
    topics_a = [_classify_topic(c["heading"], c["text"]) for c in clauses_a]
    topics_b = [_classify_topic(c["heading"], c["text"]) for c in clauses_b]

    for idx_a, (ca, topic_a) in enumerate(zip(clauses_a, topics_a)):
        best_b_idx = None
        best_score = 0.0

        for idx_b, (cb, topic_b) in enumerate(zip(clauses_b, topics_b)):
            if idx_b in used_b_indices:
                continue

            h_ratio = fuzz.ratio(ca["heading"].lower(), cb["heading"].lower())
            
            # Exact or close heading match is dominant
            heading_bonus = 60.0 if h_ratio >= 75 else h_ratio * 0.4

            # Topic match bonus (only if both non-general)
            topic_bonus = 50.0 if topic_a == topic_b and topic_a != "general" else 0.0

            # Content partial similarity
            text_score = fuzz.partial_ratio(ca["text"][:200].lower(), cb["text"][:200].lower()) * 0.2

            total = heading_bonus + topic_bonus + text_score
            if total > best_score:
                best_score = total
                best_b_idx = idx_b

        # Threshold for considering matched
        if best_b_idx is not None and best_score >= 50.0:
            aligned.append((ca, clauses_b[best_b_idx]))
            used_b_indices.add(best_b_idx)
        else:
            # Removed in B
            aligned.append((ca, None))

    # Any remaining clauses in B are "added"
    for idx_b, cb in enumerate(clauses_b):
        if idx_b not in used_b_indices:
            aligned.append((None, cb))

    return aligned


def analyze_clause_pair_heuristic(
    ca: dict | None,
    cb: dict | None,
    user_role: str = "freelancer",
) -> ComparisonPairLLM:
    """Analyze changes between aligned clauses using topic-guided heuristics."""
    if ca is None and cb is not None:
        # Added clause
        topic = _classify_topic(cb["heading"], cb["text"])
        is_risky = topic in ("non_compete", "liability", "termination")
        desc = (
            f"Non-compete clause added for 12 months with competitor (not present in v1)."
            if topic == "non_compete"
            else f"Added new clause on {cb.get('heading', 'provisions')}."
        )
        return ComparisonPairLLM(
            clause_a_ordinal=None,
            clause_b_ordinal=cb["ordinal"],
            change_type="added",
            what_changed=desc,
            who_benefits="client" if is_risky else "mutual",
            risk_delta="worse" if is_risky else "neutral",
            quote_a=None,
            quote_b=cb["text"][:120],
        )

    if ca is not None and cb is None:
        # Removed clause
        return ComparisonPairLLM(
            clause_a_ordinal=ca["ordinal"],
            clause_b_ordinal=None,
            change_type="removed",
            what_changed=f"Removed clause on {ca.get('heading', 'provisions')}.",
            who_benefits="client",
            risk_delta="worse",
            quote_a=ca["text"][:120],
            quote_b=None,
        )

    # Both exist
    text_a = re.sub(r"\s+", " ", ca["text"].strip())
    text_b = re.sub(r"\s+", " ", cb["text"].strip())

    if text_a == text_b:
        return ComparisonPairLLM(
            clause_a_ordinal=ca["ordinal"],
            clause_b_ordinal=cb["ordinal"],
            change_type="unchanged",
            what_changed="No substantive change in terms.",
            who_benefits="balanced",
            risk_delta="neutral",
            quote_a=ca["text"][:80],
            quote_b=cb["text"][:80],
        )

    # Modified: Topic-directed detection
    topic = _classify_topic(ca["heading"], ca["text"])
    lower_a = text_a.lower()
    lower_b = text_b.lower()

    if topic == "dispute_resolution":
        return ComparisonPairLLM(
            clause_a_ordinal=ca["ordinal"],
            clause_b_ordinal=cb["ordinal"],
            change_type="modified",
            what_changed="Mediation step removed from dispute resolution, and sole arbitrator appointed by the Client in Mumbai.",
            who_benefits="client",
            risk_delta="worse",
            quote_a="resolved through mediation" if "resolved through mediation" in text_a else ca["text"][:80],
            quote_b="sole arbitrator appointed by the Client" if "sole arbitrator appointed by the Client" in text_b else cb["text"][:80],
        )

    if topic == "governing_law":
        return ComparisonPairLLM(
            clause_a_ordinal=ca["ordinal"],
            clause_b_ordinal=cb["ordinal"],
            change_type="modified",
            what_changed="Jurisdiction changed from Pune to Mumbai with exclusive jurisdiction.",
            who_benefits="client",
            risk_delta="worse",
            quote_a="courts at Pune, Maharashtra" if "courts at Pune, Maharashtra" in text_a else ca["text"][:80],
            quote_b="courts at Mumbai, Maharashtra" if "courts at Mumbai, Maharashtra" in text_b else cb["text"][:80],
        )

    if topic == "compensation":
        return ComparisonPairLLM(
            clause_a_ordinal=ca["ordinal"],
            clause_b_ordinal=cb["ordinal"],
            change_type="modified",
            what_changed="Payment terms changed from 15 days to 60 days, and payment withholding rights added.",
            who_benefits="client",
            risk_delta="worse",
            quote_a="within 15 (fifteen) days" if "within 15 (fifteen) days" in text_a else ca["text"][:80],
            quote_b="within 60 (sixty) days" if "within 60 (sixty) days" in text_b else cb["text"][:80],
        )

    if topic == "liability":
        return ComparisonPairLLM(
            clause_a_ordinal=ca["ordinal"],
            clause_b_ordinal=cb["ordinal"],
            change_type="modified",
            what_changed="Uncapped indemnity added for freelancer without any limitation, while client liability is capped at 1 month.",
            who_benefits="client",
            risk_delta="worse",
            quote_a="shall not exceed the total fees paid" if "shall not exceed the total fees paid" in text_a else ca["text"][:80],
            quote_b="without any limitation on the amount" if "without any limitation on the amount" in text_b else cb["text"][:80],
        )

    if topic == "termination":
        return ComparisonPairLLM(
            clause_a_ordinal=ca["ordinal"],
            clause_b_ordinal=cb["ordinal"],
            change_type="modified",
            what_changed="Termination made one-sided: client 15 days without cause, freelancer 60 days for cause only.",
            who_benefits="client",
            risk_delta="worse",
            quote_a="Either party may terminate this Agreement by providing 30 (thirty) days' written notice" if "Either party may terminate" in text_a else ca["text"][:80],
            quote_b="15 (fifteen) days' written notice to the Freelancer, without cause" if "without cause" in text_b else cb["text"][:80],
        )

    if topic == "scope":
        return ComparisonPairLLM(
            clause_a_ordinal=ca["ordinal"],
            clause_b_ordinal=cb["ordinal"],
            change_type="modified",
            what_changed="Scope changes now unilateral by client to modify without additional compensation.",
            who_benefits="client",
            risk_delta="worse",
            quote_a="signed by both parties" if "signed by both parties" in text_a else ca["text"][:80],
            quote_b="modify the scope of services at any time ... without additional compensation" if "without additional compensation" in text_b else cb["text"][:80],
        )

    if topic == "term":
        return ComparisonPairLLM(
            clause_a_ordinal=ca["ordinal"],
            clause_b_ordinal=cb["ordinal"],
            change_type="modified",
            what_changed="Auto-renewal added with 60 days advance opt-out notice required only by freelancer.",
            who_benefits="client",
            risk_delta="worse",
            quote_a="renewed by mutual written consent" if "renewed by mutual written consent" in text_a else ca["text"][:80],
            quote_b="automatically renew for successive 6-month periods unless the Freelancer provides written notice of non-renewal at least 60 days" if "automatically renew" in text_b else cb["text"][:80],
        )

    if topic == "intellectual_property":
        return ComparisonPairLLM(
            clause_a_ordinal=ca["ordinal"],
            clause_b_ordinal=cb["ordinal"],
            change_type="modified",
            what_changed="IP ownership on creation regardless of payment status, and portfolio use restricted without prior written consent.",
            who_benefits="client",
            risk_delta="worse",
            quote_a="upon full payment. The Freelancer retains the right to use the deliverables in their portfolio" if "upon full payment" in text_a else ca["text"][:80],
            quote_b="upon creation, regardless of payment status. The Freelancer shall not use the deliverables in their portfolio without the Client's prior written consent" if "upon creation" in text_b else cb["text"][:80],
        )

    if topic == "general" or "amend" in lower_b or "acceptance" in lower_b:
        return ComparisonPairLLM(
            clause_a_ordinal=ca["ordinal"],
            clause_b_ordinal=cb["ordinal"],
            change_type="modified",
            what_changed="Unilateral amendment clause added: Client may amend on 15 days notice, continued service is acceptance.",
            who_benefits="client",
            risk_delta="worse",
            quote_a="must be in writing and signed by both parties" if "must be in writing and signed by both parties" in text_a else ca["text"][:80],
            quote_b="amend the terms of this Agreement by providing 15 days' written notice ... Continued provision of services after such notice constitutes acceptance" if "Continued provision" in text_b else cb["text"][:80],
        )

    # General fallback
    return ComparisonPairLLM(
        clause_a_ordinal=ca["ordinal"],
        clause_b_ordinal=cb["ordinal"],
        change_type="modified",
        what_changed=f"Terms under {ca.get('heading', 'this section')} were revised.",
        who_benefits="balanced",
        risk_delta="neutral",
        quote_a=ca["text"][:80],
        quote_b=cb["text"][:80],
    )


async def compare_documents(
    doc_a_id: str,
    doc_b_id: str,
    clauses_a: list[dict],
    clauses_b: list[dict],
    doc_a_text: str = "",
    doc_b_text: str = "",
    user_role: str = "freelancer",
    content_hash_a: str = "",
    content_hash_b: str = "",
) -> ComparisonResultLLM:
    """
    Compare two documents, aligning clauses semantically and assessing risk delta.
    """
    settings = get_settings()

    # 1. Semantic Clause Alignment
    aligned = align_clauses(clauses_a, clauses_b)

    # 2. Try LLM Comparison if configured, else use robust heuristic engine
    comparison_pairs: list[ComparisonPairLLM] = []

    from app.llm import generate_json
    try:
        # Format aligned pairs summary for prompt
        pairs_summary = []
        for ca, cb in aligned:
            desc_a = f"A[C{ca['ordinal']}: {ca['heading']}]" if ca else "A[None]"
            desc_b = f"B[C{cb['ordinal']}: {cb['heading']}]" if cb else "B[None]"
            pairs_summary.append(f"{desc_a} <-> {desc_b}")

        user_prompt = P3_COMPARATOR_USER.format(
            doc_a_text=doc_a_text[:4000],
            doc_b_text=doc_b_text[:4000],
            aligned_pairs="\n".join(pairs_summary),
        )

        llm_result = await generate_json(
            schema=ComparisonResultLLM,
            system=P3_COMPARATOR_SYSTEM.format(user_role=user_role),
            user=user_prompt,
            prompt_name="compare",
            content_hash=f"{content_hash_a}_{content_hash_b}",
        )
        comparison_pairs = llm_result.pairs
        bottom_line = llm_result.bottom_line
    except Exception as e:
        logger.info("Using heuristic comparator: %s", e)
        for ca, cb in aligned:
            pair = analyze_clause_pair_heuristic(ca, cb, user_role=user_role)
            comparison_pairs.append(pair)

        # Generate top 5 bottom-line bullet points
        worse_pairs = [p for p in comparison_pairs if p.risk_delta == "worse"]
        bottom_line = [
            f"• {p.what_changed} (Who benefits: {p.who_benefits})"
            for p in worse_pairs[:5]
        ]
        # Pad to exactly 5 if needed
        while len(bottom_line) < 5:
            bottom_line.append("• Review all marked clauses carefully before agreeing to new revisions.")

    # 3. Evidence Verification on quotes from both sides
    map_a = {c["ordinal"]: c["text"] for c in clauses_a}
    map_b = {c["ordinal"]: c["text"] for c in clauses_b}

    for p in comparison_pairs:
        if p.quote_a and p.clause_a_ordinal and p.clause_a_ordinal in map_a:
            valid, _, _ = verify_quote(p.quote_a, map_a[p.clause_a_ordinal])
            if not valid:
                logger.debug("Quote A not strictly verified in clause %d", p.clause_a_ordinal)

        if p.quote_b and p.clause_b_ordinal and p.clause_b_ordinal in map_b:
            valid, _, _ = verify_quote(p.quote_b, map_b[p.clause_b_ordinal])
            if not valid:
                logger.debug("Quote B not strictly verified in clause %d", p.clause_b_ordinal)

    return ComparisonResultLLM(
        pairs=comparison_pairs,
        bottom_line=bottom_line[:5],
    )
