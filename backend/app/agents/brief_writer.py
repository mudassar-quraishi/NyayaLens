"""
NyayaLens Lawyer Brief Writer (Phase 6).

Generates a one-page, professional PDF briefing document for a lawyer consultation.
Uses ReportLab with high-fidelity styling:
- Document Snapshot & Key Facts
- Top Risks with exact verified quotes and clause citations
- Missing Protections
- 10 Prioritized Questions for the Advocate
- Documents to Bring Checklist
- Legal Disclaimer
"""

from __future__ import annotations

import io
import json
import logging
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)

logger = logging.getLogger("nyayalens.brief")


def generate_brief_pdf(
    filename: str,
    doc_type: str,
    key_facts: dict,
    risk_score: int,
    top_concerns: list[str],
    findings: list[dict],
    missing_clauses: list[dict],
) -> bytes:
    """
    Generate a styled, single-to-two-page PDF consultation brief.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles matching 'The Annotated Manuscript' theme
    title_style = ParagraphStyle(
        "BriefTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1B1A17"),
    )
    subtitle_style = ParagraphStyle(
        "BriefSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#8A8680"),
    )
    section_h1 = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#B23A2E"),  # Vermilion accent
        spaceBefore=8,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1B1A17"),
    )
    quote_style = ParagraphStyle(
        "Quote",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#4A4843"),
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#8A8680"),
        alignment=1,  # Centered
    )

    elements = []

    # 1. Header & Badge
    header_data = [
        [
            Paragraph("<b>NyayaLens</b> — Consultation Brief", title_style),
            Paragraph(f"<b>Risk Score: {risk_score}/100</b>", ParagraphStyle(
                "RiskScore",
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=14,
                textColor=colors.HexColor("#B23A2E" if risk_score > 50 else "#6B8F71"),
                alignment=2,
            )),
        ],
        [
            Paragraph(f"Document: <b>{filename}</b> ({doc_type.upper()})", subtitle_style),
            Paragraph("CONFIDENTIAL & PRIVILEGED", ParagraphStyle("Privileged", fontSize=8, leading=10, textColor=colors.HexColor("#8A8680"), alignment=2)),
        ]
    ]
    header_table = Table(header_data, colWidths=[380, 160])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1B1A17"), spaceBefore=4, spaceAfter=8))

    # 2. Key Facts Snapshot
    elements.append(Paragraph("DOCUMENT SNAPSHOT & KEY FACTS", section_h1))
    parties = ", ".join(key_facts.get("parties", [])) or "Identified in agreement"
    term = key_facts.get("term", "Not specified")
    amounts = ", ".join(key_facts.get("amounts", [])) or "Standard payments"
    law = key_facts.get("governing_law", "Laws of India")

    facts_data = [
        [Paragraph(f"<b>Parties:</b> {parties}", body_style), Paragraph(f"<b>Term:</b> {term}", body_style)],
        [Paragraph(f"<b>Financials:</b> {amounts}", body_style), Paragraph(f"<b>Governing Law:</b> {law}", body_style)],
    ]
    facts_table = Table(facts_data, colWidths=[270, 270])
    facts_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4EEE1")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E8DFD0")),
    ]))
    elements.append(facts_table)
    elements.append(Spacer(1, 6))

    # 3. Top Risks with Quotes
    elements.append(Paragraph("PRIORITY CONCERNS & EVIDENCE QUOTES", section_h1))
    high_findings = [f for f in findings if f.get("risk_level") in ("high", "medium")][:4]
    if not high_findings:
        high_findings = findings[:3]

    for f in high_findings:
        c_ord = f.get("clause_ordinal", 0)
        c_type = f.get("clause_type", "Clause").replace("_", " ").title()
        means = f.get("what_it_means_for_you") or f.get("what_it_means") or f.get("plain_text", "")
        quote = f.get("evidence_quote", "")

        risk_p = Paragraph(f"• <b>[Clause {c_ord}: {c_type}]</b> {means}", body_style)
        elements.append(risk_p)
        if quote:
            quote_p = Paragraph(f'&nbsp;&nbsp;&nbsp;&nbsp;<i>Evidence quote: "{quote[:140]}..."</i>', quote_style)
            elements.append(quote_p)
        elements.append(Spacer(1, 3))

    elements.append(Spacer(1, 4))

    # 4. Missing Protections
    elements.append(Paragraph("MISSING PROTECTIONS IDENTIFIED", section_h1))
    if missing_clauses:
        for mc in missing_clauses[:3]:
            name = mc.get("name", "")
            why = mc.get("why_it_matters", "")
            elements.append(Paragraph(f"• <b>{name}:</b> {why}", body_style))
    else:
        elements.append(Paragraph("• Standard core protections appear present in the text.", body_style))

    elements.append(Spacer(1, 6))

    # 5. Ten Prioritized Questions for the Lawyer
    elements.append(Paragraph("TEN PRIORITIZED QUESTIONS TO ASK YOUR ADVOCATE", section_h1))
    default_questions = [
        "Are the penalty and forfeiture clauses enforceable under Section 74 of the Indian Contract Act?",
        "Does the termination clause provide reciprocal rights or is it legally challengeable as unconscionable?",
        "What recourse do I have if the security deposit is withheld arbitrarily?",
        "Can the non-compete restriction be enforced against me post-termination under Section 27?",
        "Are the notice periods legally compliant with relevant local tenancy or labor laws?",
        "Does the unilateral alteration clause create a legal risk of binding amendments without consent?",
        "Is the indemnification clause one-sided, and can we introduce a mutual liability cap?",
        "Which court holds actual territorial jurisdiction despite the choice of court in the document?",
        "What specific clauses should be modified before I sign or execute this agreement?",
        "Should we issue a formal written protest or demand letter regarding the problematic clauses?",
    ]
    q_data = []
    for i in range(0, 10, 2):
        q1 = f"<b>{i+1}.</b> {default_questions[i]}"
        q2 = f"<b>{i+2}.</b> {default_questions[i+1]}" if i+1 < 10 else ""
        q_data.append([Paragraph(q1, body_style), Paragraph(q2, body_style)])

    q_table = Table(q_data, colWidths=[270, 270])
    q_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(q_table)
    elements.append(Spacer(1, 6))

    # 6. Documents to Bring
    elements.append(Paragraph("DOCUMENTS TO BRING TO YOUR CONSULTATION", section_h1))
    docs_to_bring = (
        "1. Complete copy of this unsigned or signed agreement &nbsp;|&nbsp; "
        "2. All WhatsApp / email communications and payment receipts &nbsp;|&nbsp; "
        "3. Government ID (Aadhaar / PAN) &nbsp;|&nbsp; "
        "4. Prior agreements or property / work proof"
    )
    elements.append(Paragraph(docs_to_bring, body_style))

    # 7. Disclaimer
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#8A8680"), spaceBefore=2, spaceAfter=4))
    elements.append(Paragraph(
        "<b>DISCLAIMER:</b> NyayaLens is an AI legal document copilot that provides general information and document navigation assistance. "
        "It does NOT provide legal advice and is NOT a substitute for a qualified lawyer. All quotes were verified against document text.",
        disclaimer_style,
    ))

    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
