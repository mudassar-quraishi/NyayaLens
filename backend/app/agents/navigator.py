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
    """Generate structured escalation pathway matching frontend NavigatorView."""
    sit_lower = situation.lower()

    if any(k in sit_lower for k in ["deposit", "security", "landlord", "rent", "tenant", "apartment"]):
        category = "Tenancy & Security Deposit Recovery"
        summary = "Dispute regarding unlawful withholding or deduction from tenant security deposit under Indian Tenancy Laws."
        steps = [
            {
                "step_number": 1,
                "title": "Written Demand & Deduction Accounting",
                "timeframe": "7–10 days",
                "cost_estimate": "₹0 (Direct communication)",
                "action_description": "Send a formal written demand via registered email and WhatsApp requesting immediate refund and an itemized breakdown of any alleged deductions with original receipts.",
                "tips": [
                    "Attach photos and move-in inspection proof showing the condition of the premises.",
                    "Provide your bank account details and set a strict 7-day cure window.",
                ],
            },
            {
                "step_number": 2,
                "title": "Advocate Legal Notice",
                "timeframe": "15 days notice",
                "cost_estimate": "₹2,500 – ₹5,000",
                "action_description": "Have an advocate issue a formal legal notice demanding refund with 18% per annum interest for unauthorized retention under the Indian Contract Act.",
                "tips": [
                    "Send via Speed Post with Acknowledgment Due (RPAD) and keep the postal tracking receipt.",
                    "State that legal costs and interest will be claimed if not resolved within 15 days.",
                ],
            },
            {
                "step_number": 3,
                "title": "Rent Authority / Consumer Forum",
                "timeframe": "1–3 months",
                "cost_estimate": "₹500 – ₹1,500 filing fee",
                "action_description": "File a petition before the local Rent Authority (under the State Tenancy Act) or file an online complaint on e-Daakhil for deficiency in service (if rented via broker/platform).",
                "tips": [
                    "Tenancy authorities have statutory mandates for expedited hearings without cumbersome procedural delays.",
                    "File on e-Daakhil (edaakhil.nic.in) directly without needing an expensive attorney.",
                ],
            },
            {
                "step_number": 4,
                "title": "Summary Suit for Money Recovery",
                "timeframe": "6–12 months",
                "cost_estimate": "Ad-valorem court fees + counsel charges",
                "action_description": "File a Summary Suit under Order 37 of the Code of Civil Procedure (CPC) in the competent civil court for debt recovery based on the written lease deed.",
                "tips": [
                    "Under Order 37, the landlord cannot defend without proving a genuine defense, leading to swift decree.",
                ],
            },
        ]
        evidence = [
            "Original signed rental agreement and extension addendums",
            "Bank transaction proofs, UTR numbers, or receipts for deposit transfer",
            "Photographs and videos of the premises taken at move-in and key handover",
            "Written correspondence (WhatsApp chats and emails) regarding vacating and deposit return",
            "Handover key receipt or written acknowledgment from the landlord",
        ]
        urgent_triggers = [
            "Landlord threatens physical force, intimidation, or illegal lockout",
            "Unlawful retention of personal belongings or vehicle on premises",
        ]

    elif any(k in sit_lower for k in ["salary", "bonus", "pip", "deduction", "relieving", "resignation", "notice period", "employment", "employee"]):
        category = "Employment & Notice Buyout Dispute"
        summary = "Dispute regarding withheld salary, disputed notice buyout, or refusal to issue relieving letters."
        steps = [
            {
                "step_number": 1,
                "title": "HR Representation & Formal Resignation Record",
                "timeframe": "5–7 days",
                "cost_estimate": "₹0",
                "action_description": "Submit a formal written representation to HR and Management documenting medical/hardship grounds, work handover progress, and citing Section 27 of the Indian Contract Act regarding unreasonable restraints.",
                "tips": [
                    "Document that all company assets and project handovers have been completed.",
                    "Request immediate release of Full & Final (F&F) settlement statement.",
                ],
            },
            {
                "step_number": 2,
                "title": "Advocate Legal Demand Notice",
                "timeframe": "15 days",
                "cost_estimate": "₹3,000 – ₹6,000",
                "action_description": "Serve an advocate legal notice highlighting that relieving letters and service certificates cannot be held hostage for disputed financial claims.",
                "tips": [
                    "High Courts in India have repeatedly held that withholding relieving documents impairs livelihood under Article 21.",
                    "Demand issuance of Form 16, PF transfer clearance, and experience certificate.",
                ],
            },
            {
                "step_number": 3,
                "title": "Labour Commissioner Grievance",
                "timeframe": "1–2 months",
                "cost_estimate": "₹0",
                "action_description": "File a formal grievance before the Deputy Labour Commissioner or on the Ministry of Labour SAMADHAN portal.",
                "tips": [
                    "Conciliation proceedings before Labour Officers often prompt quick corporate compliance to avoid audit inspections.",
                ],
            },
            {
                "step_number": 4,
                "title": "Labour Court / Payment of Wages Claim",
                "timeframe": "4–8 months",
                "cost_estimate": "Nominal",
                "action_description": "Initiate proceedings under the Payment of Wages Act or Industrial Disputes Act for recovery of withheld wages and statutory compensation.",
                "tips": [
                    "Claim damages for lost career opportunities due to delayed documentation.",
                ],
            },
        ]
        evidence = [
            "Employment offer letter, employment agreement, and HR policies",
            "Resignation email and written handover acknowledgment documents",
            "Medical certificates or hardship proofs submitted to employer",
            "Bank statements showing monthly salary credits and unpaid months",
            "Written correspondence demanding relieving documents and settlement",
        ]
        urgent_triggers = [
            "Company threatens to blacklist or communicate false claims to prospective employers",
            "Pending job offer expiring within days due to missing relieving letter",
        ]

    elif any(k in sit_lower for k in ["unpaid", "invoice", "freelance", "client", "payment", "milestone", "consultant"]):
        category = "Freelancer Debt Recovery & Breach of Contract"
        summary = "Dispute regarding approved deliverables, unpaid invoices, or client non-responsiveness."
        steps = [
            {
                "step_number": 1,
                "title": "Statement of Account & Final Invoice Demand",
                "timeframe": "5–7 days",
                "cost_estimate": "₹0",
                "action_description": "Send a formal Statement of Account detailing invoice numbers, delivery dates, client approval confirmations, and contractual interest accrual.",
                "tips": [
                    "Remind the client that continued commercial use of deliverables without full payment infringes copyright.",
                    "Give a 7-day cure deadline before commercial escalation.",
                ],
            },
            {
                "step_number": 2,
                "title": "Advocate Legal Demand Notice",
                "timeframe": "15 days",
                "cost_estimate": "₹2,500 – ₹6,000",
                "action_description": "Serve a formal legal notice demanding principal amount plus commercial interest (e.g. 18% p.a.) under the Indian Contract Act and MSMED Act.",
                "tips": [
                    "Send via registered Speed Post and email to key executives.",
                    "Notice creates an irrefutable legal foundation for summary proceedings.",
                ],
            },
            {
                "step_number": 3,
                "title": "MSME Samadhaan Filing (If Registered)",
                "timeframe": "60–90 days",
                "cost_estimate": "₹0 (Online government portal)",
                "action_description": "If registered under Udyam / MSME, file a delayed payment complaint on the MSME Samadhaan portal. The statutory council mandates compound interest at 3x the RBI bank rate.",
                "tips": [
                    "Any freelancer or small business with an Udyam certificate can file for free.",
                    "Council decisions carry the force of an arbitral award.",
                ],
            },
            {
                "step_number": 4,
                "title": "Commercial Court / Summary Suit",
                "timeframe": "6–12 months",
                "cost_estimate": "Ad-valorem court fees + legal representation",
                "action_description": "File a Summary Suit under Order 37 CPC or commercial suit in the Commercial Division of the District Court for debt recovery based on written contract and accepted deliverables.",
                "tips": [
                    "Attach email approvals as unequivocal admissions of debt.",
                ],
            },
        ]
        evidence = [
            "Signed freelance contract or written statement of work (SOW)",
            "Submitted invoices, tax declarations, and delivery receipts",
            "Client acknowledgments, email sign-offs, or git commit acceptance",
            "Bank statement confirming non-receipt of payment",
            "Follow-up emails and WhatsApp logs",
        ]
        urgent_triggers = [
            "Client actively deploying deliverables into production while refusing payment",
            "Counterparty initiating company dissolution or insolvency",
        ]

    else:
        category = "Commercial & Contractual Dispute"
        summary = "General contractual grievance or breach of contractual obligations."
        steps = [
            {
                "step_number": 1,
                "title": "Direct Dialogue & Written Breach Notice",
                "timeframe": "7–14 days",
                "cost_estimate": "₹0",
                "action_description": "Establish a clear written record of grievances, specific clause breaches, and proposed remedial cure.",
                "tips": [
                    "Cite specific clause numbers and agreed performance standards.",
                ],
            },
            {
                "step_number": 2,
                "title": "Advocate Legal Notice",
                "timeframe": "15–30 days",
                "cost_estimate": "₹3,000 – ₹7,000",
                "action_description": "Issue an advocate legal notice articulating breach of contract and demanding specific performance or damages.",
                "tips": [
                    "Keep full postal tracking proofs and email transmission receipts.",
                ],
            },
            {
                "step_number": 3,
                "title": "Mediation & Dispute Conciliation",
                "timeframe": "1–3 months",
                "cost_estimate": "Mediation center fee",
                "action_description": "Invoke the contractual dispute resolution clause to refer the matter to formal mediation or conciliation.",
                "tips": [
                    "Pre-litigation mediation under the Mediation Act 2023 offers confidential and enforceable settlement.",
                ],
            },
            {
                "step_number": 4,
                "title": "Court or Arbitral Proceedings",
                "timeframe": "6–18 months",
                "cost_estimate": "Court fees + advocate fees",
                "action_description": "Initiate proceedings before the competent Civil Court, Commercial Court, or Arbitral Tribunal.",
                "tips": [
                    "Seek interim injunctions under Section 9 of Arbitration Act or Order 39 CPC if urgent protection is needed.",
                ],
            },
        ]
        evidence = [
            "Original executed agreement and all annexures",
            "Written correspondence, notices, and payment proofs",
            "Chronological timeline of events with dates and names",
        ]
        urgent_triggers = [
            "Imminent threat to property, personal liberty, or confidential assets",
            "Counterparty taking irreversible action without contractual notice",
        ]

    ladder = [
        {
            "step": s["step_number"],
            "stage": s["title"],
            "action": s["action_description"],
            "expected_timeline": s["timeframe"],
            "rough_cost": s["cost_estimate"],
        }
        for s in steps
    ]

    return {
        "situation_summary": summary,
        "dispute_category": category,
        "urgent_lawyer_needed": len(urgent_triggers) > 0,
        "urgent_reasons": urgent_triggers,
        "steps": steps,
        "evidence_needed": evidence,
        "free_legal_aid": LEGAL_AID_DIRECTORY,
        # Legacy backwards compatibility keys
        "escalation_ladder": ladder,
        "evidence_to_gather": evidence,
        "rough_cost_time": "Timeframes and expenses are calibrated estimates for India.",
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
    settings = get_settings()

    # In DEMO_MODE, return curated, instantaneous expert pathways for standard scenarios
    if settings.demo_mode:
        sit_lower = user_situation.lower()
        if any(k in sit_lower for k in ["deposit", "security", "unpaid", "invoice", "freelance", "salary", "bonus", "pip", "deduction", "landlord", "rent", "tenant"]):
            logger.info("DEMO_MODE: serving curated situation navigation")
            return _heuristic_navigation(user_situation, doc_type)

    import asyncio
    from app.llm import generate_json
    from app.schemas import NavigatorResponseLLM
    from app.prompts import P7_NAVIGATOR_SYSTEM, P7_NAVIGATOR_USER

    try:
        jurisdiction_hints = _load_jurisdiction_hints(doc_type)

        user_prompt = P7_NAVIGATOR_USER.format(
            user_situation=user_situation,
            doc_context=doc_context[:3000] if doc_context else "None provided",
            jurisdiction_hints=jurisdiction_hints,
        )

        result: NavigatorResponseLLM = await asyncio.wait_for(
            generate_json(
                schema=NavigatorResponseLLM,
                system=P7_NAVIGATOR_SYSTEM,
                user=user_prompt,
                prompt_name="navigator",
            ),
            timeout=15.0,
        )
        res_dict = result.model_dump()
        if not res_dict.get("free_legal_aid"):
            res_dict["free_legal_aid"] = LEGAL_AID_DIRECTORY
        if not res_dict.get("dispute_category"):
            res_dict["dispute_category"] = "General Contract Dispute"
        if "urgent_lawyer_needed" not in res_dict:
            res_dict["urgent_lawyer_needed"] = len(res_dict.get("urgent_reasons", [])) > 0
        if not res_dict.get("steps") and res_dict.get("escalation_ladder"):
            res_dict["steps"] = [
                {
                    "step_number": s.get("step", idx + 1),
                    "title": s.get("stage", f"Step {idx + 1}"),
                    "timeframe": s.get("expected_timeline", "Varies"),
                    "cost_estimate": s.get("rough_cost", "Varies"),
                    "action_description": s.get("action", ""),
                    "tips": [],
                }
                for idx, s in enumerate(res_dict["escalation_ladder"])
            ]
        if not res_dict.get("evidence_needed") and res_dict.get("evidence_to_gather"):
            res_dict["evidence_needed"] = res_dict["evidence_to_gather"]

        # Backwards compatibility keys
        res_dict["escalation_ladder"] = [
            {
                "step": s["step_number"],
                "stage": s["title"],
                "action": s["action_description"],
                "expected_timeline": s["timeframe"],
                "rough_cost": s["cost_estimate"],
            }
            for s in res_dict.get("steps", [])
        ]
        res_dict["evidence_to_gather"] = res_dict.get("evidence_needed", [])
        res_dict["urgent_lawyer_triggers"] = res_dict.get("urgent_reasons", [])
        res_dict["legal_aid_resources"] = res_dict.get("free_legal_aid", LEGAL_AID_DIRECTORY)
        return res_dict
    except Exception as e:
        logger.warning("Falling back to heuristic situation navigator: %s", e)
        return _heuristic_navigation(user_situation, doc_type)
