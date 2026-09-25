"""
Segmenter agent — splits raw text into numbered clauses.

Uses heading/numbering heuristics first, then an LLM pass to refine boundaries.
Each clause gets: ordinal, heading, text, char_start, char_end, page.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Optional

from app.llm import generate_json, compute_content_hash
from app.prompts import P_SEGMENT_SYSTEM, P_SEGMENT_USER
from app.schemas import SegmentedClauseLLM

logger = logging.getLogger("nyayalens.segmenter")


@dataclass
class ClauseSegment:
    ordinal: int
    heading: str
    text: str
    char_start: int
    char_end: int
    page: int
    content_hash: str


# ── Heading/numbering patterns ────────────────────────────────────

# Matches patterns like "1.", "1.1", "Section 1", "ARTICLE I", "Clause 2", "(a)", etc.
_HEADING_PATTERNS = [
    # "1. Title" or "1.2.3 Title"
    re.compile(r"^(\d+(?:\.\d+)*)\.\s+(.+)$", re.MULTILINE),
    # "Section 1: Title" or "SECTION 1 - Title"
    re.compile(r"^(?:section|clause|article)\s+(\d+|[IVXLC]+)[:\.\s\-–—]+(.+)$", re.MULTILINE | re.IGNORECASE),
    # "ARTICLE I" standalone
    re.compile(r"^(?:ARTICLE|SCHEDULE|ANNEXURE|APPENDIX)\s+([IVXLC\d]+)(?:\s*[:\.\-–—]\s*(.*))?$", re.MULTILINE),
    # "(a)" or "(i)" or "(1)"
    re.compile(r"^\(([a-z]|\d+|[ivx]+)\)\s+(.+)$", re.MULTILINE),
]

# All-caps line (likely a heading)
_ALLCAPS_HEADING = re.compile(r"^([A-Z][A-Z\s&,]{4,})$", re.MULTILINE)


def _heuristic_segment(raw_text: str) -> list[ClauseSegment]:
    """
    Split text using heading/numbering heuristics.
    Returns a list of clause segments with char offsets.
    """
    # Find all potential section boundaries
    boundaries: list[tuple[int, str]] = []

    for pattern in _HEADING_PATTERNS:
        for match in pattern.finditer(raw_text):
            heading = match.group(0).strip()
            boundaries.append((match.start(), heading))

    for match in _ALLCAPS_HEADING.finditer(raw_text):
        heading = match.group(0).strip()
        if len(heading) > 5:  # Skip very short all-caps
            boundaries.append((match.start(), heading))

    # Sort by position and deduplicate nearby boundaries
    boundaries.sort(key=lambda x: x[0])
    deduped: list[tuple[int, str]] = []
    for pos, heading in boundaries:
        if deduped and pos - deduped[-1][0] < 20:
            continue  # Skip if too close to the previous boundary
        deduped.append((pos, heading))

    if not deduped:
        # No headings found — treat the whole text as one clause
        return [ClauseSegment(
            ordinal=1,
            heading="",
            text=raw_text.strip(),
            char_start=0,
            char_end=len(raw_text),
            page=0,
            content_hash=hashlib.sha256(raw_text.strip().encode()).hexdigest()[:12],
        )]

    # Build clauses from boundaries
    clauses: list[ClauseSegment] = []

    # Text before first boundary (preamble)
    if deduped[0][0] > 50:
        preamble = raw_text[: deduped[0][0]].strip()
        if preamble:
            clauses.append(ClauseSegment(
                ordinal=1,
                heading="Preamble",
                text=preamble,
                char_start=0,
                char_end=deduped[0][0],
                page=0,
                content_hash=hashlib.sha256(preamble.encode()).hexdigest()[:12],
            ))

    for i, (pos, heading) in enumerate(deduped):
        end = deduped[i + 1][0] if i + 1 < len(deduped) else len(raw_text)
        text = raw_text[pos:end].strip()
        if not text:
            continue

        ordinal = len(clauses) + 1
        clauses.append(ClauseSegment(
            ordinal=ordinal,
            heading=_clean_heading(heading),
            text=text,
            char_start=pos,
            char_end=end,
            page=0,
            content_hash=hashlib.sha256(text.encode()).hexdigest()[:12],
        ))

    return clauses


def _clean_heading(heading: str) -> str:
    """Clean up a heading string."""
    # Remove numbering prefix
    heading = re.sub(r"^\d+(?:\.\d+)*\.\s*", "", heading)
    heading = re.sub(r"^(?:section|clause|article)\s+\d+[:\.\s\-–—]*", "", heading, flags=re.IGNORECASE)
    return heading.strip()


async def _llm_refine_segments(
    raw_text: str,
    content_hash: str,
) -> list[ClauseSegment]:
    """Use the LLM to segment the document when heuristics produce poor results."""
    from pydantic import BaseModel, Field

    class SegmentListLLM(BaseModel):
        clauses: list[SegmentedClauseLLM]

    # Truncate very long documents for the segmentation pass
    text_for_llm = raw_text[:15000] if len(raw_text) > 15000 else raw_text

    result = await generate_json(
        schema=SegmentListLLM,
        system=P_SEGMENT_SYSTEM,
        user=P_SEGMENT_USER.format(raw_text=text_for_llm),
        prompt_name="segment",
        content_hash=content_hash,
    )

    clauses: list[ClauseSegment] = []
    for seg in result.clauses:
        # Find the text in the original to get char offsets
        start = raw_text.find(seg.text[:80])  # First 80 chars
        if start == -1:
            start = raw_text.lower().find(seg.text[:80].lower())
        if start == -1:
            start = 0  # fallback

        text = seg.text
        end = start + len(text)

        clauses.append(ClauseSegment(
            ordinal=seg.ordinal,
            heading=seg.heading,
            text=text,
            char_start=start,
            char_end=min(end, len(raw_text)),
            page=0,
            content_hash=hashlib.sha256(text.encode()).hexdigest()[:12],
        ))

    return clauses


async def segment_document(
    raw_text: str,
    content_hash: str,
    use_llm_refinement: bool = True,
) -> list[ClauseSegment]:
    """
    Segment a document into clauses.

    1. Try heuristic segmentation first.
    2. If too few clauses or poor quality, refine with LLM.
    3. Compute char offsets and content hashes.
    """
    clauses = _heuristic_segment(raw_text)

    # If heuristics produced too few or a single giant clause, try LLM
    if use_llm_refinement and (
        len(clauses) <= 2
        or (len(clauses) == 1 and len(clauses[0].text) > 500)
    ):
        logger.info("Heuristic segmentation produced %d clauses, using LLM refinement", len(clauses))
        try:
            llm_clauses = await _llm_refine_segments(raw_text, content_hash)
            if len(llm_clauses) > len(clauses):
                clauses = llm_clauses
        except Exception as e:
            logger.warning("LLM segmentation failed, using heuristic results: %s", e)

    # Ensure ordinals are sequential
    for i, clause in enumerate(clauses):
        clause.ordinal = i + 1

    logger.info("Segmented into %d clauses", len(clauses))
    return clauses


def estimate_page(char_offset: int, chars_per_page: int = 3000) -> int:
    """Estimate page number from character offset."""
    return char_offset // chars_per_page + 1
