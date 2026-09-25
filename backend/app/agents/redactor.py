"""
Redactor agent — PII masking and unmasking.

Masks: Aadhaar, PAN, phone, email, bank account, IFSC.
Does NOT mask: names, addresses (privacy panel will note this).
Uses reversible tokens (e.g., <PHONE_1>) so the UI can restore them.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("nyayalens.redactor")


@dataclass
class RedactionResult:
    """Result of PII redaction."""
    redacted_text: str
    redaction_map: dict[str, str]  # token -> original value
    pii_found: list[dict]  # list of {type, original, token, char_start, char_end}

    def unmask(self, text: str) -> str:
        """Restore all tokens in a text back to originals."""
        result = text
        for token, original in self.redaction_map.items():
            result = result.replace(token, original)
        return result

    def map_offset_to_original(self, redacted_offset: int) -> int:
        """Map a character offset in redacted text back to original text."""
        # Build a mapping of token positions in redacted text
        # For now, approximate by computing the cumulative shift
        shifts = []
        for item in sorted(self.pii_found, key=lambda x: x["char_start"]):
            token_len = len(item["token"])
            original_len = len(item["original"])
            shifts.append({
                "original_start": item["char_start"],
                "token": item["token"],
                "token_len": token_len,
                "original_len": original_len,
                "diff": original_len - token_len,
            })

        # Walk through shifts to compute the original offset
        cumulative_shift = 0
        redacted_pos = 0
        for shift in shifts:
            token_start_in_redacted = shift["original_start"] - cumulative_shift
            if redacted_offset < token_start_in_redacted:
                return redacted_offset + cumulative_shift
            if redacted_offset < token_start_in_redacted + shift["token_len"]:
                # Inside a token — map to the start of the original
                return shift["original_start"]
            cumulative_shift += shift["diff"]

        return redacted_offset + cumulative_shift


# ── PII Patterns ──────────────────────────────────────────────────

# Aadhaar: 4-4-4 digit format
_AADHAAR_RE = re.compile(r"\b(\d{4}[\s-]\d{4}[\s-]\d{4})\b")

# PAN: 5 upper + 4 digits + 1 upper
_PAN_RE = re.compile(r"\b([A-Z]{5}\d{4}[A-Z])\b")

# Indian phone: +91 or 0 prefix, 10 digits
_PHONE_RE = re.compile(r"(?:\+91[\s-]?)(\d{5}[\s-]?\d{5})\b|\b(0\d{10})\b")

# Email
_EMAIL_RE = re.compile(r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b")

# Bank account number: 9-18 digits
_BANK_ACCOUNT_RE = re.compile(r"\b(\d{9,18})\b(?=\s*\(?\s*IFSC|\s*$)")

# IFSC code: 4 upper + 0 + 6 alphanum
_IFSC_RE = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")


def redact_pii(text: str) -> RedactionResult:
    """
    Scan text for PII and replace with reversible tokens.

    Returns a RedactionResult with redacted text, a map for unmasking,
    and a list of all PII items found.
    """
    redaction_map: dict[str, str] = {}
    pii_found: list[dict] = []
    counters: dict[str, int] = {}

    def _replace(match_text: str, pii_type: str, start: int, end: int) -> str:
        """Generate a token and record the mapping."""
        count = counters.get(pii_type, 0) + 1
        counters[pii_type] = count
        token = f"<{pii_type.upper()}_{count}>"
        redaction_map[token] = match_text
        pii_found.append({
            "type": pii_type,
            "original": match_text,
            "token": token,
            "char_start": start,
            "char_end": end,
        })
        return token

    # Process all patterns. We need to do this carefully to avoid
    # overlapping replacements. Collect all matches first, sort by position,
    # then replace from end to start.

    all_matches: list[tuple[int, int, str, str]] = []  # (start, end, original, type)

    for m in _AADHAAR_RE.finditer(text):
        all_matches.append((m.start(), m.end(), m.group(0), "aadhaar"))

    for m in _PAN_RE.finditer(text):
        all_matches.append((m.start(), m.end(), m.group(0), "pan"))

    for m in _PHONE_RE.finditer(text):
        # Phone pattern has groups — get the full match
        full_match = m.group(0)
        all_matches.append((m.start(), m.end(), full_match, "phone"))

    for m in _EMAIL_RE.finditer(text):
        all_matches.append((m.start(), m.end(), m.group(0), "email"))

    for m in _IFSC_RE.finditer(text):
        all_matches.append((m.start(), m.end(), m.group(0), "ifsc"))

    for m in _BANK_ACCOUNT_RE.finditer(text):
        all_matches.append((m.start(), m.end(), m.group(0), "bank_account"))

    # Sort by start position, then by length (longer match first)
    all_matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))

    # Remove overlapping matches (keep the first/longest one)
    filtered: list[tuple[int, int, str, str]] = []
    last_end = -1
    for start, end, original, pii_type in all_matches:
        if start >= last_end:
            filtered.append((start, end, original, pii_type))
            last_end = end

    # Replace from end to start to preserve offsets
    redacted = text
    for start, end, original, pii_type in reversed(filtered):
        token = _replace(original, pii_type, start, end)
        redacted = redacted[:start] + token + redacted[end:]

    logger.info(
        "Redacted %d PII items: %s",
        len(pii_found),
        {k: v for k, v in counters.items()},
    )

    return RedactionResult(
        redacted_text=redacted,
        redaction_map=redaction_map,
        pii_found=pii_found,
    )
