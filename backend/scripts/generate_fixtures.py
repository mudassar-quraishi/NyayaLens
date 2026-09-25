"""
Generate comprehensive DEMO_MODE fixtures for all bundled sample documents.
Ensures offline demos and evaluation harness run deterministically without external LLM dependencies.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.segmenter import _heuristic_segment
from app.llm import compute_content_hash, _fixture_key


def generate_all_fixtures():
    fixtures_dir = Path(__file__).resolve().parent.parent / "app" / "fixtures"
    samples_dir = Path(__file__).resolve().parent.parent.parent / "samples"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────────────────────────────
    # 1. RENTAL AGREEMENT
    # ─────────────────────────────────────────────────────────────────
    rental_text = (samples_dir / "rental_agreement.txt").read_text(encoding="utf-8")
    rental_hash = compute_content_hash(rental_text)
    rental_clauses = _heuristic_segment(rental_text)

    # doc_type
    doc_type_data = {
        "doc_type": "rental",
        "user_role": "tenant",
        "confidence": 0.98,
    }
    (fixtures_dir / f"{rental_hash}__doc_type.json").write_text(json.dumps(doc_type_data, indent=2), encoding="utf-8")

    # key_facts
    key_facts_data = {
        "parties": ["Mr. Rajesh Kumar Sharma (Landlord)", "Ms. Priya Mehta (Tenant)"],
        "effective_date": "2025-01-01",
        "term": "11 months (ending 30th November 2025)",
        "amounts": ["Rs. 25,000/- monthly rent", "Rs. 1,50,000/- security deposit"],
        "governing_law": "Transfer of Property Act, 1882 & Haryana rent control legislation",
        "jurisdiction": "New Delhi",
        "notice_periods": ["30 days (Landlord)", "90 days (Tenant after lock-in)"],
    }
    (fixtures_dir / f"{rental_hash}__key_facts.json").write_text(json.dumps(key_facts_data, indent=2), encoding="utf-8")

    # missing_clauses
    missing_clauses_data = {
        "missing_clauses": [
            {
                "name": "Deposit Return Timeline",
                "why_it_matters": "No timeframe specified for the landlord to refund the balance security deposit after vacating.",
                "severity": "high",
            },
            {
                "name": "Notice Before Landlord Inspection",
                "why_it_matters": "No requirement for advance notice (e.g. 24 hours) before landlord entry, compromising privacy.",
                "severity": "high",
            },
            {
                "name": "Landlord Repair Timelines",
                "why_it_matters": "No specific deadline for landlord to complete major structural or plumbing repairs.",
                "severity": "medium",
            }
        ],
        "inconsistencies": [
            {
                "clause_a_id": 8,
                "clause_b_id": 11,
                "quote_a": "90 days' written notice to vacate",
                "quote_b": "providing 30 days' written notice to the Tenant",
                "description": "Contradictory notice periods: Tenant must give 90 days notice, whereas Landlord can terminate with only 30 days notice.",
            }
        ]
    }
    (fixtures_dir / f"{rental_hash}__missing_clauses.json").write_text(json.dumps(missing_clauses_data, indent=2), encoding="utf-8")

    # glossary
    (fixtures_dir / f"{rental_hash}__glossary.json").write_text(json.dumps({
        "entries": [
            {"term": "Liquidated Damages", "definition": "A predetermined sum agreed in advance to be paid as compensation if a breach occurs."},
            {"term": "Lock-in Period", "definition": "A minimum duration during which neither party may exit the agreement without penalty."},
            {"term": "Sole Discretion", "definition": "One party holds unilateral decision-making power without needing the other's agreement."},
            {"term": "Indemnify", "definition": "To compensate or secure against legal harm or financial loss."},
        ]
    }, indent=2), encoding="utf-8")

    for c in rental_clauses:
        ord_num = c.ordinal
        h = c.heading
        text = c.text

        risk_level = "low"
        risk_reasons = []
        what_it_means = f"Standard provision regarding {h.lower()}."
        plain_english = text[:200]
        favors = "balanced"
        questions = []
        needs_review = False
        evidence_quote = ""

        # Exact quote picking from text
        if ord_num == 4 or "RENT AND PAYMENT" in h:
            risk_level = "high"
            favors = "party_a"
            needs_review = True
            risk_reasons = [
                "Unilateral rent increase up to 20% upon renewal at landlord's sole discretion without tenant's consent.",
                "A late payment fee of Rs. 500/- per day is charged for delays.",
            ]
            what_it_means = "The landlord can unilaterally hike rent by up to 20% on renewal at sole discretion."
            evidence_quote = "increase the rent by up to 20% upon renewal of this Agreement, at the Landlord's sole discretion, without requiring the Tenant's consent."
            questions = ["Can we cap renewal rent increase to 5-10% based on market rate?"]

        elif ord_num == 5 or "SECURITY DEPOSIT" in h:
            risk_level = "high"
            favors = "party_a"
            needs_review = True
            risk_reasons = [
                "Deposit deductions are made at the landlord's sole discretion without third-party inspection.",
                "No deposit return timeline is specified, creating risk of indefinite retention of funds.",
            ]
            what_it_means = "No deposit return timeline specified; deductions for damages are at landlord's sole discretion."
            evidence_quote = "The Landlord shall determine the condition of the Premises and the amount of deductions at his sole discretion."
            questions = ["Will the landlord agree to refund the deposit within 15–30 days of handover?"]

        elif ord_num == 8 or "LOCK-IN" in h:
            risk_level = "high"
            favors = "party_a"
            needs_review = True
            risk_reasons = [
                "Severe penalty: Tenant shall forfeit entire deposit as liquidated damages and additionally pay 3 months' rent.",
                "Imposes 90 days written notice to vacate after lock-in period.",
            ]
            what_it_means = "Early exit forces you to forfeit entire deposit plus 3 months rent as penalty."
            evidence_quote = "the Tenant shall forfeit the entire security deposit as liquidated damages and shall additionally pay a penalty equal to 3 (three) months' rent."
            questions = ["Can early termination penalty be capped at 1 month's rent?"]

        elif ord_num == 9 or "RIGHT OF ACCESS" in h:
            risk_level = "high"
            favors = "party_a"
            needs_review = True
            risk_reasons = [
                "Landlord or representative may enter at any time without prior notice, infringing tenant privacy.",
            ]
            what_it_means = "Landlord can enter the premises at any time without prior notice."
            evidence_quote = "with or without prior notice to the Tenant, for the purpose of inspection, repairs, or showing the Premises"
            questions = ["Can we require at least 24 hours prior written notice before entry?"]

        elif ord_num == 11 or "TERMINATION BY LANDLORD" in h:
            risk_level = "high"
            favors = "party_a"
            needs_review = True
            risk_reasons = [
                "Landlord may terminate by providing 30 days written notice, while tenant must provide 90 days notice in clause 7.",
            ]
            what_it_means = "Contradictory and unbalanced termination notice: Landlord 30 days vs Tenant 90 days."
            evidence_quote = "The Landlord may terminate this Agreement at any time by providing 30 days' written notice to the Tenant."
            questions = ["Can termination notice periods be made reciprocal (e.g. 30 days for both)?"]

        elif ord_num == 12 or "DISPUTE RESOLUTION" in h:
            risk_level = "medium"
            favors = "party_a"
            needs_review = True
            risk_reasons = [
                "Tenant agrees to bear all legal costs and attorney fees incurred by the landlord.",
            ]
            what_it_means = "Tenant bears all landlord's legal costs and attorney fees."
            evidence_quote = "The Tenant agrees to bear all legal costs and attorney fees incurred by the Landlord in enforcing this Agreement."
            questions = ["Can attorney fee clause be made mutual or removed?"]

        else:
            # Pick first complete sentence as valid evidence quote
            sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 15]
            evidence_quote = sentences[0] if sentences else text[:80]

        fixture_data = {
            "clause_type": h.lower().replace(" ", "_"),
            "plain_english": plain_english,
            "what_it_means_for_you": what_it_means,
            "risk_level": risk_level,
            "risk_reasons": risk_reasons or ["Standard operational term."],
            "favors": favors,
            "questions_to_ask": questions,
            "needs_lawyer_review": needs_review,
            "confidence": 0.95,
            "evidence_quote": evidence_quote,
        }
        (fixtures_dir / f"{rental_hash}__clause_{ord_num}.json").write_text(json.dumps(fixture_data, indent=2), encoding="utf-8")
        (fixtures_dir / f"{rental_hash}__clause_analysis_{ord_num}.json").write_text(json.dumps(fixture_data, indent=2), encoding="utf-8")

    # ─────────────────────────────────────────────────────────────────
    # 2. EMPLOYMENT OFFER
    # ─────────────────────────────────────────────────────────────────
    emp_text = (samples_dir / "employment_offer.txt").read_text(encoding="utf-8")
    emp_hash = compute_content_hash(emp_text)
    emp_clauses = _heuristic_segment(emp_text)

    (fixtures_dir / f"{emp_hash}__doc_type.json").write_text(json.dumps({
        "doc_type": "employment",
        "user_role": "employee",
        "confidence": 0.98,
    }, indent=2), encoding="utf-8")

    (fixtures_dir / f"{emp_hash}__key_facts.json").write_text(json.dumps({
        "parties": ["TechNova Solutions Private Limited", "Mr. Arjun Desai"],
        "effective_date": "2025-04-01",
        "term": "Permanent (subject to 6-month probation)",
        "amounts": ["Rs. 18,00,000/- CTC per annum", "Rs. 25,00,000/- liquidated damages"],
        "governing_law": "Laws of India",
        "jurisdiction": "Bangalore, Karnataka",
        "notice_periods": ["90 days (standard)", "15 days (probation clause 2)", "30 days (probation clause 12)"],
    }, indent=2), encoding="utf-8")

    (fixtures_dir / f"{emp_hash}__missing_clauses.json").write_text(json.dumps({
        "missing_clauses": [
            {
                "name": "Overtime Policy for Extra Hours",
                "why_it_matters": "Requires 6 days/week work with no compensation for additional overtime hours.",
                "severity": "medium",
            },
            {
                "name": "Work from Home / Remote Policy",
                "why_it_matters": "Agreement does not specify remote or hybrid working conditions.",
                "severity": "low",
            }
        ],
        "inconsistencies": [
            {
                "clause_a_id": 3,
                "clause_b_id": 16,
                "quote_a": "15 days' written notice",
                "quote_b": "notice period shall be 30 days from either side",
                "description": "Contradictory probation notice periods: Clause 2 states 15 days notice, while Clause 12 states 30 days notice.",
            }
        ]
    }, indent=2), encoding="utf-8")

    (fixtures_dir / f"{emp_hash}__glossary.json").write_text(json.dumps({
        "entries": [
            {"term": "Non-Compete", "definition": "A restriction preventing an employee from working with competitors after leaving."},
            {"term": "Clawback", "definition": "A requirement to repay money or benefits received if you leave before a certain date."},
            {"term": "Probation", "definition": "A trial period at the start of employment with easier termination rules."},
        ]
    }, indent=2), encoding="utf-8")

    for c in emp_clauses:
        ord_num = c.ordinal
        h = c.heading
        text = c.text

        risk_level = "low"
        risk_reasons = []
        what_it_means = f"Details regarding {h.lower()}."
        plain_english = text[:200]
        favors = "balanced"
        questions = []
        needs_review = False
        evidence_quote = ""

        if "WORKING HOURS" in h or ord_num == 5:
            risk_level = "medium"
            favors = "party_a"
            risk_reasons = ["No overtime compensation for Saturday work and extra hours beyond 9 hours per day."]
            what_it_means = "Requires Monday through Saturday work with no compensation for extra hours."
            evidence_quote = "no overtime compensation shall be payable."
            questions = ["Can working hours be limited to Monday through Friday?"]

        elif "NOTICE PERIOD AND TERMINATION" in h or ord_num == 6:
            risk_level = "high"
            favors = "party_a"
            needs_review = True
            risk_reasons = [
                "90 days notice period with mandatory service during projects.",
                "Clawback: Employee must repay training costs, relocation assistance, and joining bonus from preceding 24 months.",
            ]
            what_it_means = "90-day notice period with clawback of training costs and bonuses for 24 months."
            evidence_quote = "repay any training costs, relocation assistance, joining bonus, or other investments made by the Company in the employee during the preceding 24 months on a pro-rata basis."
            questions = ["Can clawback be limited to 6–12 months and pro-rated?"]

        elif "NON-COMPETE" in h or ord_num == 7:
            risk_level = "high"
            favors = "party_a"
            needs_review = True
            risk_reasons = [
                "Post-employment non-compete for 24 months (void and unenforceable under Indian Contract Act Section 27).",
                "Liquidated damages penalty of Rs 25,00,000 for non-compete violation.",
            ]
            what_it_means = "Post-employment non-compete for 24 months with Rs 25 lakhs liquidated damages (unenforceable under Indian Contract Act S.27)."
            evidence_quote = "paying liquidated damages of Rs. 25,00,000/- (Rupees Twenty-Five Lakhs Only) to the Company"
            questions = ["Can the post-employment non-compete be struck out as unenforceable under S.27?"]

        elif "INTELLECTUAL PROPERTY" in h or ord_num == 11:
            risk_level = "high"
            favors = "party_a"
            needs_review = True
            risk_reasons = [
                "IP assignment covering personal projects on personal time and personal devices.",
            ]
            what_it_means = "IP assignment claims ownership of your personal projects created in personal time on personal devices."
            evidence_quote = "work created in your personal time, on personal devices, that relates to or could relate to the Company's current or future business interests."
            questions = ["Can personal side projects on personal devices be excluded from company IP?"]

        elif "PROBATION" in h and ord_num > 10 or ord_num == 16:
            risk_level = "high"
            favors = "unclear"
            risk_reasons = [
                "Contradictory probation notice periods: clause 2 says 15 days, clause 12 says 30 days.",
            ]
            what_it_means = "Contradictory notice period: says 30 days probation notice here, but clause 2 stated 15 days."
            evidence_quote = "During the probation period, the notice period shall be 30 days from either side."

        elif ord_num == 3 or "COMMENCEMENT DATE AND PROBATION" in h:
            risk_level = "medium"
            favors = "party_a"
            risk_reasons = ["15 days probation notice specified here contradicts clause 12."]
            what_it_means = "15 days notice during probation period."
            evidence_quote = "terminate the employment with 15 days' written notice."

        else:
            sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 15]
            evidence_quote = sentences[0] if sentences else text[:80]

        fixture_data = {
            "clause_type": h.lower().replace(" ", "_"),
            "plain_english": plain_english,
            "what_it_means_for_you": what_it_means,
            "risk_level": risk_level,
            "risk_reasons": risk_reasons or ["Standard employment term."],
            "favors": favors,
            "questions_to_ask": questions,
            "needs_lawyer_review": needs_review,
            "confidence": 0.95,
            "evidence_quote": evidence_quote,
        }
        (fixtures_dir / f"{emp_hash}__clause_{ord_num}.json").write_text(json.dumps(fixture_data, indent=2), encoding="utf-8")
        (fixtures_dir / f"{emp_hash}__clause_analysis_{ord_num}.json").write_text(json.dumps(fixture_data, indent=2), encoding="utf-8")

    print(f"Generated comprehensive fixtures in {fixtures_dir}")


if __name__ == "__main__":
    generate_all_fixtures()
