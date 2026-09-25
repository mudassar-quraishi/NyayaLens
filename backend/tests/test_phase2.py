"""
Tests for Phase 2: Redaction, verification, analyzer.
Includes the round-trip redaction test per amendment #2.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agents.redactor import redact_pii
from app.agents.verifier import verify_quote, verify_finding, _extract_numerics


SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"


def _load_sample(name: str) -> str:
    return (SAMPLES_DIR / name).read_text(encoding="utf-8")


# ── Redaction Tests ───────────────────────────────────────────────

class TestRedaction:
    def test_redacts_aadhaar(self):
        text = "Aadhaar No.: 1234-5678-9012"
        result = redact_pii(text)
        assert "1234-5678-9012" not in result.redacted_text
        assert "<AADHAAR_1>" in result.redacted_text
        assert result.redaction_map["<AADHAAR_1>"] == "1234-5678-9012"

    def test_redacts_pan(self):
        text = "PAN: ABCDE1234F"
        result = redact_pii(text)
        assert "ABCDE1234F" not in result.redacted_text
        assert "<PAN_1>" in result.redacted_text

    def test_redacts_email(self):
        text = "Email: priya.mehta@email.com"
        result = redact_pii(text)
        assert "priya.mehta@email.com" not in result.redacted_text
        assert "<EMAIL_1>" in result.redacted_text

    def test_redacts_phone(self):
        text = "Phone: +91 98765 43210"
        result = redact_pii(text)
        assert "98765 43210" not in result.redacted_text
        found_types = [p["type"] for p in result.pii_found]
        assert "phone" in found_types

    def test_redacts_ifsc(self):
        text = "IFSC: SBIN0001234"
        result = redact_pii(text)
        assert "SBIN0001234" not in result.redacted_text
        assert "<IFSC_1>" in result.redacted_text

    def test_round_trip(self):
        """Amendment #2: Redact then unmask must give back original text."""
        text = _load_sample("rental_agreement.txt")
        result = redact_pii(text)

        # Redacted text should not contain original PII
        for item in result.pii_found:
            assert item["original"] not in result.redacted_text, \
                f"PII not redacted: {item['type']} = {item['original'][:20]}..."

        # Unmasking should restore the original text
        restored = result.unmask(result.redacted_text)
        assert restored == text, "Round-trip redaction failed: unmasked text differs from original"

    def test_round_trip_employment(self):
        """Round-trip test on employment offer."""
        text = _load_sample("employment_offer.txt")
        result = redact_pii(text)
        restored = result.unmask(result.redacted_text)
        assert restored == text

    def test_rental_pii_count(self):
        """Golden file expects specific PII counts for rental agreement."""
        text = _load_sample("rental_agreement.txt")
        result = redact_pii(text)
        types = [p["type"] for p in result.pii_found]

        assert types.count("aadhaar") == 2
        assert types.count("pan") == 2
        assert types.count("email") >= 1

    def test_employment_pii_count(self):
        """Golden file expects specific PII counts for employment offer."""
        text = _load_sample("employment_offer.txt")
        result = redact_pii(text)
        types = [p["type"] for p in result.pii_found]

        assert types.count("aadhaar") >= 1
        assert types.count("pan") >= 1
        assert types.count("email") >= 1


# ── Verifier Tests ────────────────────────────────────────────────

class TestVerifier:
    def test_exact_match(self):
        source = "The tenant shall pay a security deposit of Rs. 1,50,000/-"
        quote = "pay a security deposit of Rs. 1,50,000/-"
        verified, method, score = verify_quote(quote, source)
        assert verified
        assert method == "exact"

    def test_case_insensitive_match(self):
        source = "The LANDLORD may terminate this Agreement"
        quote = "the landlord may terminate this agreement"
        verified, method, score = verify_quote(quote, source)
        assert verified
        assert method == "exact"

    def test_whitespace_normalized_match(self):
        source = "The  tenant   shall   pay"
        quote = "The tenant shall pay"
        verified, method, score = verify_quote(quote, source)
        assert verified
        assert method == "exact"

    def test_fuzzy_match(self):
        source = "The tenant shall be responsible for all minor repairs and maintenance"
        # Slightly different quote (missing "all")
        quote = "The tenant shall be responsible for minor repairs and maintenance"
        verified, method, score = verify_quote(quote, source)
        assert verified
        assert method == "fuzzy"
        assert score >= 92

    def test_numeric_mismatch_fails(self):
        """Amendment #1: Numbers must match exactly even in fuzzy match."""
        source = "payment within 15 days of receipt"
        quote = "payment within 30 days of receipt"  # Wrong number!
        verified, method, score = verify_quote(quote, source)
        assert not verified

    def test_amount_mismatch_fails(self):
        source = "a penalty equal to Rs. 25,000/- per month"
        quote = "a penalty equal to Rs. 50,000/- per month"
        verified, method, score = verify_quote(quote, source)
        assert not verified

    def test_no_match(self):
        source = "The landlord shall maintain the property"
        quote = "The tenant has unlimited liability for all damages"
        verified, method, score = verify_quote(quote, source)
        assert not verified
        assert method == "failed"

    def test_empty_quote(self):
        verified, method, score = verify_quote("", "some source text")
        assert not verified

    def test_verify_on_redacted_first(self):
        """Amendment #2: Verification should work on redacted text the LLM saw."""
        original = "Phone: +91 98765 43210, deposit of Rs. 1,50,000/-"
        redacted = "Phone: <PHONE_1>, deposit of Rs. 1,50,000/-"
        quote = "deposit of Rs. 1,50,000/-"

        # Should verify against redacted text first
        verified, method, score = verify_finding(quote, original, redacted)
        assert verified


# ── Numeric Extraction Tests ──────────────────────────────────────

class TestNumericExtraction:
    def test_extract_numbers(self):
        nums = _extract_numerics("payment of Rs. 25,000/- within 15 days")
        assert any("25,000" in n for n in nums)
        assert any("15" in n for n in nums)

    def test_extract_duration(self):
        nums = _extract_numerics("lock-in period of 6 months and 90 days notice")
        assert any("6 months" in n for n in nums)
        assert any("90 days" in n for n in nums)

    def test_extract_dates(self):
        nums = _extract_numerics("commencing from 1st January 2025")
        assert any("1st january 2025" in n for n in nums)


# ── Risk Score Tests ──────────────────────────────────────────────

class TestRiskScore:
    def test_score_range(self):
        from app.agents.aggregator import compute_risk_score
        findings = [
            {"risk_level": "high", "favors": "party_a"},
            {"risk_level": "medium", "favors": "party_a"},
            {"risk_level": "low", "favors": "balanced"},
        ]
        missing = [{"severity": "high"}]
        score, breakdown = compute_risk_score(findings, missing, [])
        assert 0 <= score <= 100
        assert "clause_risk" in breakdown
        assert "missing_protections" in breakdown

    def test_no_findings_zero_score(self):
        from app.agents.aggregator import compute_risk_score
        score, _ = compute_risk_score([], [], [])
        assert score == 0

    def test_all_high_risk(self):
        from app.agents.aggregator import compute_risk_score
        findings = [{"risk_level": "high", "favors": "party_a"} for _ in range(10)]
        missing = [{"severity": "high"} for _ in range(5)]
        inconsistencies = [{"desc": "x"} for _ in range(3)]
        score, _ = compute_risk_score(findings, missing, inconsistencies)
        assert score >= 70
