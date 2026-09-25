"""
Tests for Phase 5: Compare Mode.
Verifies:
1. Semantic clause alignment between versions.
2. All 10 planted changes in freelance v1 -> v2 are detected.
3. Bottom-line summary contains 5 prioritized bullets.
4. API endpoints POST /api/compare and GET /api/compare/{id}.
"""

import json
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.agents.segmenter import _heuristic_segment
from app.agents.comparator import compare_documents, align_clauses


SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"
EVAL_DIR = Path(__file__).resolve().parent.parent.parent / "eval"


@pytest.fixture
def golden_data():
    golden_path = EVAL_DIR / "golden.json"
    with open(golden_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def freelance_docs():
    text_v1 = (SAMPLES_DIR / "freelance_v1.txt").read_text(encoding="utf-8")
    text_v2 = (SAMPLES_DIR / "freelance_v2.txt").read_text(encoding="utf-8")

    clauses_v1 = [
        {
            "id": f"v1_{c.ordinal}",
            "ordinal": c.ordinal,
            "heading": c.heading,
            "text": c.text,
            "char_start": c.char_start,
            "char_end": c.char_end,
        }
        for c in _heuristic_segment(text_v1)
    ]

    clauses_v2 = [
        {
            "id": f"v2_{c.ordinal}",
            "ordinal": c.ordinal,
            "heading": c.heading,
            "text": c.text,
            "char_start": c.char_start,
            "char_end": c.char_end,
        }
        for c in _heuristic_segment(text_v2)
    ]

    return {
        "text_v1": text_v1,
        "text_v2": text_v2,
        "clauses_v1": clauses_v1,
        "clauses_v2": clauses_v2,
    }


@pytest.mark.asyncio
async def test_alignment_covers_all_clauses(freelance_docs):
    """Test that all clauses from both documents are aligned."""
    v1 = freelance_docs["clauses_v1"]
    v2 = freelance_docs["clauses_v2"]

    aligned = align_clauses(v1, v2)
    assert len(aligned) >= len(v1)

    # Check non-compete is recognized as an added clause in v2
    added_in_b = [cb for ca, cb in aligned if ca is None and cb is not None]
    assert any("NON-COMPETE" in cb["heading"].upper() for cb in added_in_b)


@pytest.mark.asyncio
async def test_all_10_planted_changes_detected(freelance_docs, golden_data):
    """
    Acceptance Criteria for Phase 5:
    All 10 planted changes in freelance v1 -> v2 MUST be detected.
    """
    v1 = freelance_docs["clauses_v1"]
    v2 = freelance_docs["clauses_v2"]
    planted = golden_data["freelance_comparison"]["planted_changes"]
    assert len(planted) == 10

    result = await compare_documents(
        doc_a_id="v1",
        doc_b_id="v2",
        clauses_a=v1,
        clauses_b=v2,
        doc_a_text=freelance_docs["text_v1"],
        doc_b_text=freelance_docs["text_v2"],
        user_role="freelancer",
        content_hash_a="hash_v1",
        content_hash_b="hash_v2",
    )

    assert len(result.pairs) > 0
    assert len(result.bottom_line) == 5

    # Check detection for each of the 10 planted changes
    detected_count = 0
    for issue in planted:
        issue_id = issue["id"]
        keywords = [kw.lower() for kw in issue["keywords"]]

        # Find a pair that matches the keywords in what_changed or quote_b or clause text
        matched = False
        for pair in result.pairs:
            searchable = (
                f"{pair.what_changed} {pair.quote_a or ''} {pair.quote_b or ''}"
            ).lower()

            # Check if any keyword matches
            if any(kw in searchable for kw in keywords):
                assert pair.risk_delta == "worse" or pair.change_type in ("added", "modified")
                matched = True
                break

        assert matched, f"Planted change {issue_id} ({issue['description']}) was not detected in compare result!"
        detected_count += 1

    assert detected_count == 10, f"Expected 10/10 planted changes detected, got {detected_count}"


@pytest.mark.asyncio
async def test_compare_api_endpoints(freelance_docs):
    """Test POST /api/compare and GET /api/compare/{id}."""
    from app.database import init_db
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        s_res = await client.post("/api/session", json={"language": "en", "reading_level": "standard"})
        session_id = s_res.json()["id"]

        # Upload Doc A (v1)
        up_a = await client.post(
            "/api/documents",
            files={"file": ("freelance_v1.txt", freelance_docs["text_v1"].encode("utf-8"), "text/plain")},
            data={"session_id": session_id},
        )
        doc_a_id = up_a.json()["id"]

        # Upload Doc B (v2)
        up_b = await client.post(
            "/api/documents",
            files={"file": ("freelance_v2.txt", freelance_docs["text_v2"].encode("utf-8"), "text/plain")},
            data={"session_id": session_id},
        )
        doc_b_id = up_b.json()["id"]

        # Trigger comparison
        comp_res = await client.post(
            "/api/compare",
            json={"doc_a": doc_a_id, "doc_b": doc_b_id},
        )
        assert comp_res.status_code == 200
        comp_data = comp_res.json()
        comp_id = comp_data["id"]
        assert len(comp_data["result"]["pairs"]) > 0
        assert len(comp_data["result"]["bottom_line"]) == 5

        # Fetch comparison by id
        get_res = await client.get(f"/api/compare/{comp_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == comp_id
