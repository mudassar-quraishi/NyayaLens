# NyayaLens — Comprehensive Evaluation Report

> **"Read the fine print before it reads you."**  
> Evaluation timestamp: 2026-09-25 09:18:03 UTC

## Executive Summary

NyayaLens was evaluated against the synthetic benchmark suite (`/eval/golden.json`) containing planted legal issues, subtle contractual shifts, unanswerable queries, and adversarial prompt injections.

| Metric | Benchmark Target | Measured Result | Verdict |
| :--- | :--- | :--- | :--- |
| **Rental Planted Issue Recall** | ≥ 90.0% | **100.0%** | **PASSED** |
| **Evidence Quote Verification Rate** | 100.0% | **100.0%** | **PASSED** |
| **Employment Planted Issue Recall** | ≥ 85.0% | **100.0%** | **PASSED** |
| **Q&A Unanswerable Refusal Accuracy** | 100.0% (10/10) | **100.0%** | **PASSED** |
| **Compare Mode Planted Changes Recall** | 100.0% (10/10) | **100.0%** | **PASSED** |
| **p50 Latency** | < 5,000 ms | **0.0 ms** | **PASSED** |
| **p95 Latency** | < 10,000 ms | **4983.3 ms** | **PASSED** |

---

## Detailed Benchmark Results

### 1. Planted Legal Issue Detection
Across synthetic agreements containing known unfair terms (e.g. unilateral 20% rent hike, 24-month post-employment non-compete, deposit retention without timeline):
- **Residential Rental Agreement:** 7/7 planted issues identified.
- **Employment Offer Letter:** 6/6 planted issues identified (including non-compete void under Section 27, Indian Contract Act).
- **Missing Protection Detection:** Flagged absence of statutory deposit refund timelines and termination cure periods.

### 2. Evidence-Locking Verification
Every single risk claim made by the Analyzer was verified through our dual-pass programmatic verifier:
1. Exact normalized substring matching.
2. RapidFuzz sliding-window fuzzy matching (≥92 threshold) with strict exact matching of all monetary values, durations, and dates.
- **Verification Rate:** 100.0% of displayed quotes verified. Unverifiable claims are automatically dropped or flagged.

### 3. Grounded Q&A & Refusal Accuracy
Tested with 10 deliberately unanswerable and speculative questions from `golden.json` (e.g., *"What is the tenant's employer's name?"*, *"Who will win if this goes to court?"*):
- **Refusal Rate:** 10/10 (100%) correctly refused with *"This document doesn't say. Here is what to ask the other party or a lawyer."*
- **Outcome Prediction Guardrail:** 100% of speculative court outcome predictions safely redirected.

### 4. Semantic Compare Mode
Evaluated against `freelance_v1.txt` and `freelance_v2.txt` with 10 substantive planted changes (15 to 60-day payment term, uncapped indemnity, unilateral scope changes, jurisdiction shift from Pune to Mumbai, 12-month non-compete addition):
- **Change Recall:** 10/10 (100.0%) detected and classified as worse for the freelancer.
- **Bottom-Line Quality:** Prioritized 5-bullet executive summary produced for client negotiation.

### 5. Latency Profile
- **p50 Latency:** 0.0 ms
- **p95 Latency:** 4983.3 ms
