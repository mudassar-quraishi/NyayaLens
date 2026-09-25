"""
NyayaLens Situation Navigator Agent (Phase 8 Stretch).

Guided dispute intake and resolution pathways:
- Escalation ladder (Dialogue -> Written Notice -> Mediation/Ombudsman -> Consumer Forum/Tribunal -> Court)
- Essential evidence checklists
- Realistic rough time and cost ranges
- Urgent triggers for immediate lawyer consultation
- Free legal aid resources (NALSA, Tele-Law, DLSA) from curated jurisdiction pack
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import get_settings
from app.prompts import P7_NAVIGATOR_SYSTEM, P7_NAVIGATOR_USER
from app.agents.analyzer import _load_jurisdiction_hints

logger = logging.getLogger("nyayalens.navigator")


# Curated Legal Aid Resources in India
LEGAL_AID_DIRECTORY = [
    {
        "name": "NALSA (National Legal Services Authority)",
        "description": "Free legal aid for eligible citizens including women, children, workers, and indigent persons.",
        "contact": "Toll-Free National Helpline: 15100 | Website: https://nalsa.gov.in",
    },
    {
        "name": "Tele-Law (Department of Justice)",
        "description": "Video/telephonic legal consultation with panel advocates via Common Service Centres.",
        "contact": "Website: https://tele-law.in | Mobile App: Tele-Law (Android)",
    },
    {
        "name": "State & District Legal Services Authorities (SLSA / DLSA)",
        "description": "Front offices at every District Court complex offering free legal counsel.",
        "contact": "Visit the nearest District Court complex Legal Aid Clinic",
    },
    {
        "name": "National Consumer Helpline (NCH)",
        "description": "Grievance redressal against service providers and unfair trade practices.",
        "contact": "Toll-Free: 1915 | Website: https://consumerhelpline.gov.in",
    },
]


def _heuristic_navigation(situation: str, doc_type: str = "rental") -> dict:
    """Generate structured escalation pathway when LLM is unavailable."""
    sit_lower = situation.lower()

    if any(k in sit_lower for k in ["deposit", "security", "landlord", "rent"]):
        summary = "Dispute regarding withholding or deduction from security deposit."
        ladder = [
            {
                "step": 1,
                "stage": "Written Request & Accounting",
                "action": "Send written request via WhatsApp/Email demanding itemized deductions and invoice receipts.",
                "expected_timeline": "7–14 days",
                "rough_cost": "Nil (Direct communication)",
            },
            {
                "step": 2,
                "stage": "Formal Legal Notice",
                "action": "Have an advocate issue a formal legal notice demanding refund with interest for unauthorized retention.",
                "expected_timeline": "15–30 days response period",
                "rough_cost": "Rs. 2,000 – Rs. 5,000 (Advocate fee)",
            },
            {
                "step": 3,
                "stage": "Mediation or Rent Authority",
                "action": "File grievance with the local Rent Authority (under state tenancy rules) or apply for pre-litigation mediation.",
                "expected_timeline": "1–3 months",
                "rough_cost": "Nominal government/mediation fee",
            },
            {
                "step": 4,
                "stage": "Consumer Forum / Civil Court",
                "action": "File consumer complaint for deficiency in service (if through agency/managed platform) or civil summary suit for recovery of money.",
                "expected_timeline": "6–18 months",
                "rough_cost": "Court fees + advocate fees (varies)",
            },
        ]
        evidence = [
            "Original signed rental agreement",
            "Bank transaction proofs / receipts for deposit payment",
            "Photographs/videos of premises taken at move-in and handover",
            "Written communications (WhatsApp / Emails) regarding vacating and deposit return",
            "Handover key receipt / inspection clearance message",
        ]
        urgent_triggers = [
            "Landlord threatens physical force, harassment, or unlawful entry",
            "Unlawful retention of personal belongings left in the premises",
        ]

    elif any(k in sit_lower for k in ["unpaid", "invoice", "freelance", "client", "payment"]):
        summary = "Dispute regarding unpaid freelancer invoices or withheld payment."
        ladder = [
            {
                "step": 1,
                "stage": "Statement of Account",
                "action": "Issue formal Statement of Account highlighting overdue invoices, contractual payment terms, and delivery proof.",
                "expected_timeline": "7–10 days",
                "rough_cost": "Nil",
            },
            {
                "step": 2,
                "stage": "Formal Legal Notice",
                "action": "Issue a legal notice demanding outstanding dues with contractual late interest (e.g. 1.5%/month).",
                "expected_timeline": "15 days notice",
                "rough_cost": "Rs. 2,500 – Rs. 6,000",
            },
            {
                "step": 3,
                "stage": "MSME Samadhaan (if registered) / Commercial Mediation",
                "action": "If registered under MSME/Udyam, file case on MSME Samadhaan portal for delayed payment under MSMED Act (automatic compound interest).",
                "expected_timeline": "90 days statutory target",
                "rough_cost": "Nil for registration",
            },
            {
                "step": 4,
                "stage": "Summary Suit / Commercial Court",
                "action": "File summary suit under Order 37 CPC for debt recovery based on written contract and accepted deliverables.",
                "expected_timeline": "6–12 months",
                "rough_cost": "Ad-valorem court fees + legal representation",
            },
        ]
        evidence = [
            "Signed freelance contract or written statement of work",
            "Sent invoices and delivery receipts / email submissions of work",
            "Client acknowledgments or written acceptance of deliverables",
            "Bank statement confirming non-receipt of payment",
        ]
        urgent_triggers = [
            "Client threatens to use deliverables commercially while refusing payment",
            "Statute of limitations approaching (3 years for debt recovery)",
        ]

    else:
        summary = "General contractual or legal dispute."
        ladder = [
            {
                "step": 1,
                "stage": "Direct Dialogue & Written Record",
                "action": "Establish clear written record of grievances and proposed resolution.",
                "expected_timeline": "7–14 days",
                "rough_cost": "Nil",
            },
            {
                "step": 2,
                "stage": "Formal Notice",
                "action": "Issue formal notice stating breach and giving 15–30 days cure period.",
                "expected_timeline": "15–30 days",
                "rough_cost": "Rs. 2,000 – Rs. 5,000",
            },
            {
                "step": 3,
                "stage": "Alternative Dispute Resolution",
                "action": "Invoke contractual dispute resolution clause (Mediation or Arbitration).",
                "expected_timeline": "2–6 months",
                "rough_cost": "Arbitrator / mediator charges",
            },
            {
                "step": 4,
                "stage": "Court / Tribunal",
                "action": "Initiate appropriate judicial proceedings in competent court.",
                "expected_timeline": "12+ months",
                "rough_cost": "Court fees + advocate fees",
            },
        ]
        evidence = [
            "Copy of the contract or agreement",
            "Written correspondence, notices, and payment receipts",
            "Timeline of events with dates and names",
        ]
        urgent_triggers = [
            "Imminent threat to property or personal safety",
            "Irreversible action being taken by counterparty without notice",
        ]

    return {
        "situation_summary": summary,
        "escalation_ladder": ladder,
        "evidence_to_gather": evidence,
        "rough_cost_time": "Timeframes and expenses are general estimates for India and vary by state and case complexity.",
        "urgent_lawyer_triggers": urgent_triggers,
        "legal_aid_resources": LEGAL_AID_DIRECTORY,
    }


async def navigate_situation(
    user_situation: str,
    doc_context: str = "",
    doc_type: str = "general",
) -> dict:
    """
    Process user dispute scenario and generate escalation roadmap.
    """
    from app.llm import generate_json
    try:
        from app.prompts import P7_NAVIGATOR_SYSTEM, P7_NAVIGATOR_USER
        jurisdiction_hints = _load_jurisdiction_hints(doc_type)

        user_prompt = P7_NAVIGATOR_USER.format(
            user_situation=user_situation,
            doc_context=doc_context[:3000] if doc_context else "None provided",
            jurisdiction_hints=jurisdiction_hints,
        )

        class NavigatorResponse(dict):
            pass

        # Call LLM or fallback
        result = await generate_json(
            schema=None,  # dynamic json
            system=P7_NAVIGATOR_SYSTEM,
            user=user_prompt,
            prompt_name="navigator",
        )
        return result
    except Exception as e:
        logger.info("Using heuristic situation navigator: %s", e)
        return _heuristic_navigation(user_situation, doc_type)
