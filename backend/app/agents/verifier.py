"""
Verifier agent — evidence quote verification.

Strategy (per amendment #1):
1. Exact normalized-substring check first.
2. Sliding-window fuzzy match (rapidfuzz partial_ratio >= 92).
3. All numbers, dates, amounts and durations inside a quote must match exactly.
4. Verification runs on the redacted text the LLM saw, then maps back to original.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from rapidfuzz import fuzz

logger = logging.getLogger("nyayalens.verifier")


# ── Number/date/amount extraction ─────────────────────────────────

_NUMBER_RE = re.compile(r"\b\d[\d,]*\.?\d*\b")
_DURATION_RE = re.compile(
    r"\b\d+\s*(?:days?|months?|years?|weeks?|hours?|minutes?)\b",
    re.IGNORECASE,
)
_AMOUNT_RE = re.compile(
    r"(?:Rs\.?|₹|INR)\s*[\d,]+(?:\.\d+)?(?:/-)?\b",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|"
    r"Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}\b",
    re.IGNORECASE,
)


def _extract_numerics(text: str) -> set[str]:
    """Extract all numbers, dates, amounts and durations from text."""
    items: set[str] = set()
    for pattern in [_NUMBER_RE, _DURATION_RE, _AMOUNT_RE, _DATE_RE]:
        for m in pattern.finditer(text):
            # Normalize: strip whitespace, commas
            val = re.sub(r"\s+", " ", m.group(0).strip())
            items.add(val.lower())
    return items


def _normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, collapse whitespace, strip."""
    text = unicodedata.normalize("NFC", text)
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


# ── Core Verification ─────────────────────────────────────────────

def verify_quote(
    quote: str,
    source_text: str,
    fuzzy_threshold: int = 92,
) -> tuple[bool, str, float]:
    """
    Verify that a quote appears in the source text.

    Args:
        quote: The evidence quote from the LLM
        source_text: The clause text to check against
        fuzzy_threshold: Minimum partial_ratio score for fuzzy match

    Returns:
        (is_verified, method, score)
        method is one of: "exact", "fuzzy", "failed"
        score is the match score (100 for exact, fuzzy score, or 0)
    """
    if not quote or not source_text:
        return False, "failed", 0.0

    norm_quote = _normalize(quote)
    norm_source = _normalize(source_text)

    # 1. Exact normalized substring check
    if norm_quote in norm_source:
        return True, "exact", 100.0

    # 2. Sliding-window fuzzy match
    score = fuzz.partial_ratio(norm_quote, norm_source)

    if score >= fuzzy_threshold:
        # 3. Numeric exactness check: all numbers/dates/amounts in the quote
        # must appear exactly in the source
        quote_numerics = _extract_numerics(quote)
        source_numerics = _extract_numerics(source_text)

        if quote_numerics:
            missing_numerics = quote_numerics - source_numerics
            if missing_numerics:
                logger.warning(
                    "Fuzzy match passed (%.1f) but numeric mismatch: %s not in source",
                    score, missing_numerics,
                )
                return False, "failed", score

        return True, "fuzzy", score

    return False, "failed", score


def verify_finding(
    evidence_quote: str,
    clause_text: str,
    redacted_clause_text: str | None = None,
) -> tuple[bool, str, float]:
    """
    Verify a finding's evidence quote.

    Per amendment #2: verify on the redacted text first (what the LLM saw),
    then on the original text.

    Args:
        evidence_quote: The quote from the LLM output
        clause_text: The original clause text
        redacted_clause_text: The redacted version the LLM was given (if available)

    Returns:
        (is_verified, method, score)
    """
    # First try verification on the redacted text (what the LLM actually saw)
    if redacted_clause_text:
        verified, method, score = verify_quote(evidence_quote, redacted_clause_text)
        if verified:
            return verified, method, score

    # Fall back to verification on the original text
    return verify_quote(evidence_quote, clause_text)


def batch_verify_findings(
    findings: list[dict],
    clauses: dict[int, str],
    redacted_clauses: dict[int, str] | None = None,
) -> list[dict]:
    """
    Verify a batch of findings against their source clauses.

    Args:
        findings: List of finding dicts with 'clause_ordinal' and 'evidence_quote'
        clauses: Dict mapping clause ordinal -> clause text (original)
        redacted_clauses: Dict mapping clause ordinal -> redacted clause text

    Returns:
        Updated findings list with 'verified', 'verification_method', 'verification_score' fields
    """
    verified_count = 0
    total = len(findings)

    for finding in findings:
        ordinal = finding.get("clause_ordinal", 0)
        quote = finding.get("evidence_quote", "")
        clause_text = clauses.get(ordinal, "")
        redacted_text = (redacted_clauses or {}).get(ordinal)

        verified, method, score = verify_finding(quote, clause_text, redacted_text)
        finding["verified"] = verified
        finding["verification_method"] = method
        finding["verification_score"] = score

        if verified:
            verified_count += 1
        else:
            logger.warning(
                "Finding for clause %d FAILED verification (score=%.1f): %s...",
                ordinal, score, quote[:60],
            )

    rate = verified_count / total if total > 0 else 0.0
    logger.info(
        "Verification: %d/%d passed (%.1f%%)", verified_count, total, rate * 100
    )
    return findings
