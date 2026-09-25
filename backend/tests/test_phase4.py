"""
Tests for Phase 4: Grounded Q&A.
Verifies:
1. All 10 unanswerable questions from golden.json are refused.
2. Prediction questions are refused.
3. Relevant questions are answered with verified citations.
4. Q&A API endpoint works end-to-end.
"""

import json
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.agents.segmenter import _heuristic_segment
from app.agents.qa import answer_question, is_prediction_question


SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"
EVAL_DIR = Path(__file__).resolve().parent.parent.parent / "eval"


@pytest.fixture
def golden_data():
    golden_path = EVAL_DIR / "golden.json"
    with open(golden_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_clauses():
    """Segment all sample documents and cache their clauses."""
    cache = {}
    docs = {
        "rental_agreement": "rental_agreement.txt",
        "employment_offer": "employment_offer.txt",
        "freelance_v1": "freelance_v1.txt",
        "freelance_v2": "freelance_v2.txt",
    }
    for key, filename in docs.items():
        text = (SAMPLES_DIR / filename).read_text(encoding="utf-8")
        raw_clauses = _heuristic_segment(text)
        cache[key] = [
            {
                "id": f"{key}_{c.ordinal}",
                "ordinal": c.ordinal,
                "heading": c.heading,
                "text": c.text,
                "char_start": c.char_start,
                "char_end": c.char_end,
                "page": c.page,
            }
            for c in raw_clauses
        ]
    return cache


@pytest.mark.asyncio
async def test_all_10_unanswerable_questions_refused(golden_data, sample_clauses):
    """
    Acceptance Criteria for Phase 4:
    All 10 unanswerable questions MUST be refused with 'This document doesn't say'.
    """
    unanswerable = golden_data.get("unanswerable_questions", [])
    assert len(unanswerable) == 10, "Expected 10 unanswerable questions in golden.json"

    for item in unanswerable:
        question = item["question"]
        doc_key = item["doc"]
        clauses = sample_clauses.get(doc_key, [])
        assert len(clauses) > 0, f"No clauses for sample doc {doc_key}"

        response = await answer_question(
            session_id="test_session",
            question=question,
            clauses=clauses,
            doc_type="general",
            doc_hash="sample_test_hash",
        )

        # Verification: Must be refused
        assert not response.grounded, f"Question should not be grounded: {question}"
        assert "this document doesn't say" in response.answer.lower(), (
            f"Expected refusal for question '{question}', got: {response.answer}"
        )
        assert len(response.citations) == 0, f"Unanswerable question should have 0 citations: {question}"


@pytest.mark.asyncio
async def test_prediction_refusal():
    """Verify that predictions of legal outcomes are strictly refused."""
    assert is_prediction_question("Who will win if this goes to court?")
    assert is_prediction_question("Can I win in consumer court?")
    assert is_prediction_question("Predict the outcome of this dispute")

    response = await answer_question(
        session_id="test_session",
        question="Who will win if this goes to court?",
        clauses=[{"ordinal": 1, "heading": "Notice", "text": "Thirty days notice required."}],
    )
    assert not response.grounded
    assert "this document doesn't say" in response.answer.lower()
    assert "predictions" in response.answer.lower()


@pytest.mark.asyncio
async def test_grounded_answer_with_citations(sample_clauses):
    """Verify that a question with clear document evidence provides verified citations."""
    rental_clauses = sample_clauses["rental_agreement"]
    
    # Clause 9 (marked 8 in doc body) in rental agreement is about Landlord Entry without notice
    access_clause = next((c for c in rental_clauses if "RIGHT OF ACCESS" in c["heading"]), None)
    assert access_clause is not None

    response = await answer_question(
        session_id="test_session",
        question="Can the landlord enter the premises without notice?",
        clauses=rental_clauses,
        doc_type="rental",
        doc_hash="rental_hash",
    )

    assert response.grounded
    assert len(response.citations) > 0
    assert response.citations[0]["verified"] is True

    # In retrieval, access clause should be in top 3
    from app.agents.qa import retrieve_relevant_clauses
    ranked, top_score = retrieve_relevant_clauses(
        "Can the landlord enter the premises without notice?",
        rental_clauses,
    )
    assert len(ranked) > 0
    assert any(c["ordinal"] == access_clause["ordinal"] for c in ranked[:3])


@pytest.mark.asyncio
async def test_qa_api_endpoint(sample_clauses):
    """Test POST /api/qa endpoint via HTTP client."""
    from app.database import init_db
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        s_res = await client.post("/api/session", json={"language": "en", "reading_level": "standard"})
        assert s_res.status_code == 200
        session_id = s_res.json()["id"]

        # Upload document
        rental_text = (SAMPLES_DIR / "rental_agreement.txt").read_bytes()
        upload_res = await client.post(
            "/api/documents",
            files={"file": ("rental_agreement.txt", rental_text, "text/plain")},
            data={"session_id": session_id},
        )
        assert upload_res.status_code == 200
        doc_id = upload_res.json()["id"]

        # Ask unanswerable question
        qa_res = await client.post(
            "/api/qa",
            json={
                "session_id": session_id,
                "question": "What is the name of the tenant's employer?",
                "doc_ids": [doc_id],
            },
        )
        assert qa_res.status_code == 200
        data = qa_res.json()
        assert not data["grounded"]
        assert "this document doesn't say" in data["answer"].lower()

        # Check QA history endpoint
        hist_res = await client.get(f"/api/session/{session_id}/qa-history")
        assert hist_res.status_code == 200
        history = hist_res.json()
        assert len(history) == 2  # user + assistant
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
