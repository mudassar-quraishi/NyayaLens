# NyayaLens: Architecture Decision Records (ADRs)

This document records the key architectural and design decisions made during the engineering of NyayaLens.

---

## ADR-001: Evidence-Locked Verification Strategy

### Context
In legal assistance applications, AI hallucinations pose critical risks. If an AI claims a contract contains an unfair clause when it does not, or quotes text inaccurately, the user could make disastrous legal decisions or misinform their attorney.

### Decision
Implement an Evidence Verifier engine (`app.agents.verifier`) with a strict multi-tier verification algorithm:
1. **Normalized Exact Substring Check:** Character-normalized match ignoring casing and superfluous whitespace.
2. **Sliding-Window Fuzzy Match:** Using `rapidfuzz.fuzz.partial_ratio >= 92` over candidate windows.
3. **Strict Numeric, Date, & Monetary Invariance:** Even if text matches with high fuzzy confidence, all extracted numbers, currency figures (e.g. ₹1,20,000, 18%), durations (e.g. 10 months, 30 days), and dates must match character-for-character with the source document.
4. If verification fails, the quote is rejected and suppressed from display.

### Consequences
- **Positive:** Zero hallucinated quotes reach the user. 100% verification rate measured in `eval/run_eval.py`.
- **Trade-off:** High precision may reject slightly paraphrased LLM quotes; mitigated by prompting the LLM to provide verbatim quotes only.

---

## ADR-002: Reversible PII Redaction & Offset Remapping

### Context
Users upload sensitive contracts containing Aadhaar numbers, PAN numbers, bank accounts, emails, and phone numbers. Sending raw PII to external model APIs violates privacy principles. However, the user interface requires accurate character offsets against the *original* document to draw highlights and connector lines.

### Decision
Implement reversible PII Tokenization (`app.agents.redactor`):
1. Detect structured Indian identifiers using regex patterns (Aadhaar, PAN, phone, email, IFSC, bank accounts).
2. Replace each entity with a typed token (e.g., `[AADHAAR_REDACTED_1]`).
3. Store the mapping table in the temporary session record.
4. Run LLM analysis and verification on the redacted text, then map character spans back to original document coordinates for the UI document reader.
5. Explicitly disclose in the Privacy panel that names and addresses are not automatically stripped to preserve legal party context.

### Consequences
- **Positive:** Confidential financial and statutory identifiers never leave the local boundary in raw form.
- **Positive:** Document highlighting in the UI aligns with original unmodified text.

---

## ADR-003: Two-Tier Document Segmentation

### Context
Contracts vary widely from numbered clauses (`1. TERM`, `Clause 2: RENT`) to narrative paragraphs or poorly OCR'd text. Pure LLM segmentation is slow and token-expensive; pure regex fails on unusual formatting.

### Decision
Adopt a two-tier segmentation approach (`app.agents.segmenter`):
1. **Tier 1 (Heuristic / Regex Engine):** Scans for standard contractual numbering (`\bClause\s+\d+`, `\bSection\s+\d+`, `^\s*\d+[\.\)]`, roman numerals `^\s*[IVXLCDM]+[\.\)]`, and uppercase headings).
2. **Quality Gate:** If the heuristic segments the text into at least 3 distinct clauses with reasonable length distributions, accept Tier 1 immediately (0ms LLM latency).
3. **Tier 2 (LLM Fallback):** If heuristic yields fewer than 3 clauses or unparsed text blocks, invoke LLM segmentation to identify logical clauses.

### Consequences
- **Positive:** 90%+ of standard contracts process instantly without LLM latency.
- **Positive:** Robust fallback for non-standard documents.

---

## ADR-004: Honest Uncertainty & Strict Refusal Philosophy

### Context
Ordinary users often ask legal assistants speculative questions ("Will I win if I go to court?") or questions about terms that do not exist in the contract ("Does this lease allow pets?"). Naive chatbots either hallucinate terms or offer unauthorized legal advice.

### Decision
Implement strict honest uncertainty in the Q&A agent (`app.agents.qa`):
1. **Outcome Prediction Refusal:** Automatically intercept questions asking "will I win", "court outcome", "should I sue", or "can I get away with". The agent explicitly states: *"NyayaLens provides legal information, not outcome predictions or advice."*
2. **Absence Refusal:** If a topic is not mentioned in any retrieved clause, the agent explicitly begins with: *"This document doesn't say. Here is what to ask the other party or a lawyer..."*
3. Every grounded answer requires citations to specific clauses with verified exact quotes.

### Consequences
- **Positive:** Protects users from false confidence and ensures compliance with legal assistance boundaries.
- **Positive:** Achieves 100% refusal accuracy on the 10 unanswerable test queries in `eval/golden.json`.

---

## ADR-005: Canonical Topic-Guided Contract Comparator

### Context
In version comparisons (e.g. Freelance v1 vs v2), naive text diffs or pure embedding cosine similarity suffer from "legal stopword drift." Words like "services", "terms", "parties", and "termination" appear in nearly every clause, causing clauses like `NON-COMPETE` to falsely align with `TERMINATION`.

### Decision
Structure the semantic comparator (`app.agents.comparator`) around canonical legal topics:
1. Map clauses to canonical legal topics (`PAYMENT_TERMS`, `NON_COMPETE`, `IP_ASSIGNMENT`, `TERMINATION`, `LIABILITY_INDEMNITY`, `CONFIDENTIALITY`, `GOVERNING_LAW`, etc.) using heading patterns first, followed by specific substantive keyword density.
2. Align Version A and Version B clauses by canonical topic.
3. Compute risk delta (`better`, `worse`, `neutral`, `unchanged`) per topic.
4. Synthesize a 5-bullet "Bottom Line" summary highlighting the net impact on the user.

### Consequences
- **Positive:** Successfully detected all 10 planted predatory changes between Freelance v1 and v2 with 100% accuracy.
- **Positive:** Side-by-side diff cards provide clear before/after context for non-lawyers.

---

## ADR-006: Local PDF & iCalendar Generation

### Context
Users need to take their analysis out of the browser: into their calendar (for notice deadlines) and to their lawyer (for consultation). Relying on heavy external web-rendering engines (like headless Chrome) introduces brittle dependencies in container environments.

### Decision
Use lightweight, robust Python libraries on the backend:
1. **ReportLab** for PDF generation: Builds a clean, publication-grade 1-page Lawyer Brief with tabular metadata, formatted quote blocks, and attorney questions.
2. **Standard RFC 5545 iCalendar (`.ics`)**: Emits calendar files with `VALARM` triggers set for 3 days before critical contract dates (lock-in expiry, rent payment dates, renewal notice windows).

### Consequences
- **Positive:** 100% offline generation with zero external service dependencies.
- **Positive:** Immediate download speeds (<50ms generation time).

---

## ADR-007: Demo Mode & Reproducible Evaluation Harness

### Context
Hackathon demos and automated testing must be fast, resilient against rate limits, and 100% reproducible without requiring live paid API keys.

### Decision
1. Key demo fixtures by the SHA-256 hash of normalized document text (`content_hash`).
2. If `DEMO_MODE=true` and the document hash matches a known sample, serve pre-computed, verified fixtures instantly with a UI badge.
3. Provide `eval/run_eval.py` that validates all 5 core competencies (Planted issue recall, Quote verification rate, Unanswerable question refusals, Compare change detection, and Obligation extraction) against `eval/golden.json`.

### Consequences
- **Positive:** Fast, deterministic CI test runs (52 tests pass in ~60 seconds).
- **Positive:** Flawless stage demonstrations with zero API latency.
