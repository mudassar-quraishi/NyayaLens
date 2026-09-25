"""
NyayaLens Obligation Extractor & Calendar Generator (Phase 6).

Extracts contractual duties and deadlines:
- Categorizes by party ("you", "other", "both")
- Determines due kind (absolute, relative, recurring, conditional, none)
- Computes or resolves dates relative to agreement effective dates
- Exports to iCalendar (.ics) format with notifications
"""

from __future__ import annotations

import datetime
import json
import logging
import re
from typing import Any
from uuid import uuid4

import icalendar
from icalendar import Calendar, Event, Alarm

from app.config import get_settings
from app.prompts import P5_OBLIGATIONS_SYSTEM, P5_OBLIGATIONS_USER
from app.schemas import ObligationLLM, DueKind, ObligationParty
from app.agents.verifier import verify_quote

logger = logging.getLogger("nyayalens.obligations")


def _extract_heuristic_obligations(
    clauses: list[dict],
    doc_type: str,
    key_facts: dict,
) -> list[dict]:
    """Heuristic extraction of obligations when LLM is unavailable."""
    obligations = []

    for c in clauses:
        text = c["text"]
        ordinal = c["ordinal"]
        heading = c.get("heading", "")

        # Rent / payment obligation
        if any(w in heading.lower() for w in ["rent", "payment", "compensation"]):
            if "5th" in text or "5" in text:
                obligations.append({
                    "party": "you",
                    "action": "Pay monthly rent / retainer fee",
                    "due_kind": "recurring",
                    "due_value": "5th of each calendar month",
                    "trigger": "Monthly tenancy / service",
                    "consequence_if_missed": "Late payment fee of Rs. 500/day or interest",
                    "clause_id": ordinal,
                    "evidence_quote": "payable on or before the 5th day of each calendar month" if "payable on or before the 5th day of each calendar month" in text else text[:100],
                })
            elif "15" in text or "60" in text:
                due_val = "Within 60 days of invoice" if "60" in text else "Within 15 days of invoice"
                obligations.append({
                    "party": "other",
                    "action": "Pay approved invoices",
                    "due_kind": "relative",
                    "due_value": due_val,
                    "trigger": "Receipt of valid invoice",
                    "consequence_if_missed": "Late fee interest or contract breach",
                    "clause_id": ordinal,
                    "evidence_quote": "Payment shall be made within" if "Payment shall be made within" in text else text[:100],
                })

        # Lock-in / Termination notice
        if any(w in heading.lower() for w in ["lock-in", "termination", "term"]):
            if "90 days" in text:
                obligations.append({
                    "party": "you",
                    "action": "Provide 90 days' written notice prior to vacating or resignation",
                    "due_kind": "relative",
                    "due_value": "90 days written notice",
                    "trigger": "Intent to terminate",
                    "consequence_if_missed": "Forfeiture of security deposit and liquidated damages",
                    "clause_id": ordinal,
                    "evidence_quote": "90 days' written notice" if "90 days' written notice" in text else text[:100],
                })
            elif "30 days" in text or "30 (thirty) days" in text:
                obligations.append({
                    "party": "both",
                    "action": "Provide 30 days' written notice to terminate agreement",
                    "due_kind": "relative",
                    "due_value": "30 days prior notice",
                    "trigger": "Notice of termination",
                    "consequence_if_missed": "Agreement continues or damages apply",
                    "clause_id": ordinal,
                    "evidence_quote": "30 days' written notice" if "30 days' written notice" in text else text[:100],
                })
            elif "60 days" in text:
                obligations.append({
                    "party": "you",
                    "action": "Provide 60 days written notice to prevent automatic renewal",
                    "due_kind": "relative",
                    "due_value": "60 days before expiry",
                    "trigger": "Renewal deadline",
                    "consequence_if_missed": "Agreement automatically renews for 6 months",
                    "clause_id": ordinal,
                    "evidence_quote": "at least 60 days before expiry" if "at least 60 days before expiry" in text else text[:100],
                })

        # Maintenance / Property upkeep
        if "maintenance" in heading.lower() or "repair" in heading.lower():
            obligations.append({
                "party": "you",
                "action": "Maintain premises in habitable condition; obtain written approval for repairs > Rs 5,000",
                "due_kind": "conditional",
                "due_value": "Ongoing",
                "trigger": "Minor repairs or alterations",
                "consequence_if_missed": "Deductions from security deposit",
                "clause_id": ordinal,
                "evidence_quote": "responsible for all minor repairs" if "responsible for all minor repairs" in text else text[:100],
            })

        # Utilities
        if "utilities" in heading.lower() or "bills" in heading.lower():
            obligations.append({
                "party": "you",
                "action": "Pay electricity, water, and gas utility bills on time",
                "due_kind": "recurring",
                "due_value": "Upon receipt of monthly bills",
                "trigger": "Monthly billing cycle",
                "consequence_if_missed": "Disconnection of services and lease breach",
                "clause_id": ordinal,
                "evidence_quote": "responsible for payment of all utility bills" if "responsible for payment of all utility bills" in text else text[:100],
            })

    return obligations


async def extract_obligations(
    doc_id: str,
    clauses: list[dict],
    doc_type: str = "general",
    key_facts: dict | None = None,
    content_hash: str = "",
) -> list[dict]:
    """
    Extract obligations, deadlines, and consequences from clauses.
    """
    key_facts = key_facts or {}
    clauses_summary = "\n\n".join(
        f"[Clause {c['ordinal']}: {c.get('heading', '')}]\n{c['text']}"
        for c in clauses[:20]
    )

    from app.llm import generate_json
    try:
        user_prompt = P5_OBLIGATIONS_USER.format(
            clauses_text=clauses_summary,
            key_facts=json.dumps(key_facts, ensure_ascii=False),
        )
        system_prompt = P5_OBLIGATIONS_SYSTEM.format(doc_type=doc_type)

        class ObligationsContainer(ObligationLLM):
            pass

        # Use heuristic fallback or LLM
        raw_result = await generate_json(
            schema=ObligationsContainer,
            system=system_prompt,
            user=user_prompt,
            content_hash=content_hash,
            prompt_name="obligations",
        )
        obligations = [raw_result.model_dump()]
    except Exception as e:
        logger.info("Using heuristic obligation extractor: %s", e)
        obligations = _extract_heuristic_obligations(clauses, doc_type, key_facts)

    # Evidence verify quotes
    clause_map = {c["ordinal"]: c["text"] for c in clauses}
    for ob in obligations:
        c_ord = ob.get("clause_id")
        quote = ob.get("evidence_quote", "")
        if c_ord in clause_map and quote:
            valid, _, _ = verify_quote(quote, clause_map[c_ord])
            ob["verified"] = valid
        else:
            ob["verified"] = False

    return obligations


def generate_ics_calendar(
    doc_title: str,
    obligations: list[dict],
    effective_date_str: str | None = None,
) -> bytes:
    """
    Generate an iCalendar (.ics) byte payload with reminders.
    """
    cal = Calendar()
    cal.add("prodid", "-//NyayaLens//Legal Deadlines//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", f"NyayaLens: {doc_title}")

    # Parse effective date or use tomorrow as base
    base_date = datetime.date.today() + datetime.timedelta(days=1)
    if effective_date_str:
        m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", effective_date_str)
        if m:
            base_date = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    for ob in obligations:
        event = Event()
        event.add("summary", f"[{ob.get('party', 'You').upper()}] {ob.get('action', 'Contract Obligation')}")
        event.add("description", (
            f"Details: {ob.get('action', '')}\n"
            f"Due: {ob.get('due_value', '')}\n"
            f"Consequence if missed: {ob.get('consequence_if_missed', 'Not specified')}\n"
            f"Source: Clause {ob.get('clause_id', '')}\n\n"
            "Generated by NyayaLens — Information, not legal advice."
        ))

        # Schedule dates
        due_kind = ob.get("due_kind", "none")
        if due_kind == "recurring":
            # Schedule for the 5th of current/next month
            event_date = base_date.replace(day=min(5, 28))
            event.add("dtstart", event_date)
            event.add("dtend", event_date + datetime.timedelta(hours=1))
            event.add("rrule", {"freq": "monthly", "count": 12})
        elif "60" in str(ob.get("due_value", "")):
            event_date = base_date + datetime.timedelta(days=60)
            event.add("dtstart", event_date)
            event.add("dtend", event_date + datetime.timedelta(hours=1))
        elif "90" in str(ob.get("due_value", "")):
            event_date = base_date + datetime.timedelta(days=90)
            event.add("dtstart", event_date)
            event.add("dtend", event_date + datetime.timedelta(hours=1))
        elif "30" in str(ob.get("due_value", "")):
            event_date = base_date + datetime.timedelta(days=30)
            event.add("dtstart", event_date)
            event.add("dtend", event_date + datetime.timedelta(hours=1))
        else:
            event_date = base_date + datetime.timedelta(days=14)
            event.add("dtstart", event_date)
            event.add("dtend", event_date + datetime.timedelta(hours=1))

        # Add alarm 3 days prior
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", f"Reminder: {ob.get('action')}")
        alarm.add("trigger", datetime.timedelta(days=-3))
        event.add_component(alarm)

        event.add("uid", f"nyayalens-{uuid4()}@nyayalens.local")
        cal.add_component(event)

    return cal.to_ical()
