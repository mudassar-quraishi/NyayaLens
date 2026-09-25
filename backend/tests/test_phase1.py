"""
Tests for Phase 1: Ingest, segmentation, and core infrastructure.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.database import init_db, engine, Base
from app.agents.segmenter import _heuristic_segment, segment_document
from app.llm import compute_content_hash, repair_json


# ── Fixtures ──────────────────────────────────────────────────────

SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"


@pytest_asyncio.fixture
async def client():
    """Async test client with fresh DB."""
    # Use in-memory SQLite for tests
    os.environ["DATABASE_URL"] = "sqlite:///./test_nyayalens.db"
    os.environ["DEMO_MODE"] = "0"
    os.environ.setdefault("GEMINI_API_KEY", "test-key")

    from app.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Clean up test DB file
    try:
        os.remove("test_nyayalens.db")
    except FileNotFoundError:
        pass


def _load_sample(name: str) -> str:
    return (SAMPLES_DIR / name).read_text(encoding="utf-8")


# ── Health Check ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    data = resp.json()
    assert data["name"] == "NyayaLens"
    assert "tagline" in data


# ── Session CRUD ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_and_delete_session(client):
    # Create
    resp = await client.post("/api/session", json={"language": "en", "reading_level": "standard"})
    assert resp.status_code == 200
    session = resp.json()
    assert "id" in session
    assert session["language"] == "en"

    # Delete
    resp = await client.delete(f"/api/session/{session['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


# ── Segmentation Tests ───────────────────────────────────────────

def test_heuristic_segment_rental():
    """Heuristic segmenter should find all major sections in the rental agreement."""
    text = _load_sample("rental_agreement.txt")
    clauses = _heuristic_segment(text)

    # Should find multiple clauses (the rental doc has 13 numbered sections + preamble)
    assert len(clauses) >= 10, f"Expected >= 10 clauses, got {len(clauses)}"

    # Ordinals should be sequential
    ordinals = [c.ordinal for c in clauses]
    assert ordinals == list(range(1, len(clauses) + 1))

    # All clauses should have non-empty text
    for c in clauses:
        assert len(c.text.strip()) > 0, f"Clause {c.ordinal} is empty"

    # Char offsets should be valid
    for c in clauses:
        assert c.char_start >= 0
        assert c.char_end > c.char_start
        assert c.char_end <= len(text) + 1

    # Content hash should be computed
    for c in clauses:
        assert len(c.content_hash) > 0


def test_heuristic_segment_employment():
    """Employment offer has clear numbered sections."""
    text = _load_sample("employment_offer.txt")
    clauses = _heuristic_segment(text)
    assert len(clauses) >= 10, f"Expected >= 10 clauses, got {len(clauses)}"


def test_heuristic_segment_freelance():
    """Freelance agreement should segment cleanly."""
    text = _load_sample("freelance_v1.txt")
    clauses = _heuristic_segment(text)
    assert len(clauses) >= 8, f"Expected >= 8 clauses, got {len(clauses)}"


def test_heuristic_segment_prompt_injection():
    """Prompt injection test document should also segment properly."""
    text = _load_sample("prompt_injection_test.txt")
    clauses = _heuristic_segment(text)
    assert len(clauses) >= 5, f"Expected >= 5 clauses, got {len(clauses)}"


# ── Content Hash ──────────────────────────────────────────────────

def test_content_hash_deterministic():
    """Same text should always produce the same hash."""
    text = "Hello, this is a test document."
    h1 = compute_content_hash(text)
    h2 = compute_content_hash(text)
    assert h1 == h2


def test_content_hash_normalized():
    """Whitespace differences should produce the same hash."""
    h1 = compute_content_hash("Hello   world  test")
    h2 = compute_content_hash("Hello world test")
    assert h1 == h2


# ── JSON Repair ───────────────────────────────────────────────────

def test_repair_json_clean():
    assert json.loads(repair_json('{"key": "value"}')) == {"key": "value"}


def test_repair_json_markdown_fences():
    raw = '```json\n{"key": "value"}\n```'
    assert json.loads(repair_json(raw)) == {"key": "value"}


def test_repair_json_with_preamble():
    raw = 'Here is the result:\n{"key": "value"}\nDone.'
    assert json.loads(repair_json(raw)) == {"key": "value"}


# ── Document Upload Integration ───────────────────────────────────

@pytest.mark.asyncio
async def test_upload_text_document(client):
    """Upload a plain text document and verify clauses are created."""
    # Create session
    resp = await client.post("/api/session", json={"language": "en", "reading_level": "standard"})
    session_id = resp.json()["id"]

    # Upload document
    text = _load_sample("rental_agreement.txt")
    resp = await client.post(
        "/api/documents",
        data={"session_id": session_id},
        files={"file": ("rental_agreement.txt", text.encode(), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["clause_count"] >= 10
    assert data["status"] == "segmented"
    doc_id = data["id"]

    # Get clauses
    resp = await client.get(f"/api/documents/{doc_id}/clauses")
    assert resp.status_code == 200
    clauses = resp.json()
    assert len(clauses) >= 10

    # Get document
    resp = await client.get(f"/api/documents/{doc_id}")
    assert resp.status_code == 200
    assert resp.json()["filename"] == "rental_agreement.txt"


# ── Golden File Validation ────────────────────────────────────────

def test_golden_file_structure():
    """Verify the golden.json file is well-formed."""
    golden_path = Path(__file__).resolve().parent.parent.parent / "eval" / "golden.json"
    assert golden_path.exists(), "golden.json not found"

    golden = json.loads(golden_path.read_text(encoding="utf-8"))

    # Check structure
    assert "rental_agreement" in golden
    assert "employment_offer" in golden
    assert "freelance_comparison" in golden
    assert "prompt_injection_test" in golden
    assert "unanswerable_questions" in golden

    # Rental should have planted issues
    rental = golden["rental_agreement"]
    assert len(rental["planted_issues"]) >= 5

    # Employment should have planted issues
    employment = golden["employment_offer"]
    assert len(employment["planted_issues"]) >= 5

    # Freelance comparison should have planted changes
    freelance = golden["freelance_comparison"]
    assert len(freelance["planted_changes"]) >= 5

    # Should have 10 unanswerable questions
    assert len(golden["unanswerable_questions"]) == 10


# ── Sample Files Exist ────────────────────────────────────────────

def test_all_sample_files_exist():
    """Verify all expected sample files exist."""
    expected = [
        "rental_agreement.txt",
        "employment_offer.txt",
        "freelance_v1.txt",
        "freelance_v2.txt",
        "prompt_injection_test.txt",
    ]
    for name in expected:
        path = SAMPLES_DIR / name
        assert path.exists(), f"Sample file not found: {name}"
        assert len(path.read_text(encoding="utf-8").strip()) > 100, f"Sample file too short: {name}"
