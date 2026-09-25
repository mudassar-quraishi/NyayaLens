"""
Tests for Phase 6: Obligations checklist, .ics export, and Lawyer Brief PDF.
"""

from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.agents.segmenter import _heuristic_segment
from app.agents.obligation_extractor import extract_obligations, generate_ics_calendar
from app.agents.brief_writer import generate_brief_pdf


SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"


@pytest.fixture
def rental_data():
    text = (SAMPLES_DIR / "rental_agreement.txt").read_text(encoding="utf-8")
    clauses = [
        {"ordinal": c.ordinal, "heading": c.heading, "text": c.text}
        for c in _heuristic_segment(text)
    ]
    key_facts = {
        "parties": ["Mr. Rajesh Kumar Sharma", "Ms. Priya Mehta"],
        "effective_date": "2025-01-01",
        "term": "11 months",
        "amounts": ["Rs. 25,000/- monthly rent", "Rs. 1,50,000/- security deposit"],
        "governing_law": "Transfer of Property Act, 1882",
    }
    return {"text": text, "clauses": clauses, "key_facts": key_facts}


@pytest.mark.asyncio
async def test_extract_obligations_rental(rental_data):
    """Test extracting obligations from rental agreement."""
    obs = await extract_obligations(
        doc_id="rental_1",
        clauses=rental_data["clauses"],
        doc_type="rental",
        key_facts=rental_data["key_facts"],
        content_hash="hash_rental",
    )

    assert len(obs) >= 3, "Expected at least 3 obligations extracted"

    # Check rent payment obligation
    rent_ob = next((o for o in obs if "rent" in o["action"].lower()), None)
    assert rent_ob is not None
    assert rent_ob["party"] == "you"
    assert rent_ob["due_kind"] in ("recurring", "relative")

    # Check verified quote
    assert rent_ob["verified"] is True


def test_generate_ics_calendar(rental_data):
    """Test .ics calendar generation."""
    sample_obs = [
        {
            "party": "you",
            "action": "Pay monthly rent",
            "due_kind": "recurring",
            "due_value": "5th of each month",
            "consequence_if_missed": "Late fee Rs. 500/day",
            "clause_id": 4,
        },
        {
            "party": "you",
            "action": "Provide 90 days notice before vacating",
            "due_kind": "relative",
            "due_value": "90 days written notice",
            "consequence_if_missed": "Forfeit deposit",
            "clause_id": 8,
        }
    ]

    ics_bytes = generate_ics_calendar(
        doc_title="Rental Agreement",
        obligations=sample_obs,
        effective_date_str="2025-01-01",
    )

    assert isinstance(ics_bytes, bytes)
    assert len(ics_bytes) > 100
    ics_str = ics_bytes.decode("utf-8")
    assert "BEGIN:VCALENDAR" in ics_str
    assert "BEGIN:VEVENT" in ics_str
    assert "Pay monthly rent" in ics_str
    assert "BEGIN:VALARM" in ics_str
    assert "END:VCALENDAR" in ics_str


def test_generate_brief_pdf(rental_data):
    """Test Lawyer Brief PDF generation."""
    sample_findings = [
        {
            "clause_ordinal": 3,
            "clause_type": "rent_increase",
            "what_it_means": "Landlord can increase rent by up to 20% at sole discretion.",
            "risk_level": "high",
            "evidence_quote": "increase the rent by up to 20% upon renewal ... at the Landlord's sole discretion",
        },
        {
            "clause_ordinal": 4,
            "clause_type": "security_deposit",
            "what_it_means": "No refund timeline specified for security deposit.",
            "risk_level": "high",
            "evidence_quote": "security deposit shall be refundable at the end of the tenancy period",
        },
    ]

    sample_missing = [
        {
            "name": "Deposit return timeline",
            "why_it_matters": "No deadline for landlord to refund balance deposit.",
            "severity": "high",
        }
    ]

    pdf_bytes = generate_brief_pdf(
        filename="rental_agreement.txt",
        doc_type="rental",
        key_facts=rental_data["key_facts"],
        risk_score=78,
        top_concerns=["Unilateral rent increase", "No deposit return deadline"],
        findings=sample_findings,
        missing_clauses=sample_missing,
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # PDF files start with magic bytes %PDF
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_obligations_and_brief_endpoints(rental_data):
    """Test API endpoints for obligations list, .ics download, and .pdf download."""
    from app.database import init_db
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        s_res = await client.post("/api/session", json={"language": "en", "reading_level": "standard"})
        session_id = s_res.json()["id"]

        # Upload document
        up_res = await client.post(
            "/api/documents",
            files={"file": ("rental_agreement.txt", rental_data["text"].encode("utf-8"), "text/plain")},
            data={"session_id": session_id},
        )
        assert up_res.status_code == 200
        doc_id = up_res.json()["id"]

        # 1. GET obligations
        ob_res = await client.get(f"/api/documents/{doc_id}/obligations")
        assert ob_res.status_code == 200
        data = ob_res.json()
        assert "grouped" in data
        assert "you_must" in data["grouped"]
        assert len(data["obligations"]) > 0

        # 2. GET obligations.ics
        ics_res = await client.get(f"/api/documents/{doc_id}/obligations.ics")
        assert ics_res.status_code == 200
        assert ics_res.headers["content-type"].startswith("text/calendar")
        assert b"BEGIN:VCALENDAR" in ics_res.content

        # 3. GET brief.pdf
        pdf_res = await client.get(f"/api/documents/{doc_id}/brief.pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF")
