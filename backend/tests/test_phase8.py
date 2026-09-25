"""
Tests for Phase 8: Situation Navigator.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.agents.navigator import navigate_situation


@pytest.mark.asyncio
async def test_navigate_deposit_dispute():
    """Test intake of security deposit dispute."""
    result = await navigate_situation(
        user_situation="My landlord has not returned my security deposit of Rs 1,50,000 for 2 months after vacating.",
        doc_type="rental",
    )

    assert "escalation_ladder" in result
    assert len(result["escalation_ladder"]) >= 3
    assert "evidence_to_gather" in result
    assert len(result["evidence_to_gather"]) > 0
    assert "legal_aid_resources" in result
    assert len(result["legal_aid_resources"]) >= 2
    assert any("NALSA" in r["name"] for r in result["legal_aid_resources"])


@pytest.mark.asyncio
async def test_navigator_api_endpoint():
    """Test POST /api/navigator endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/navigator",
            json={
                "user_situation": "Client is refusing to pay 3 months of approved invoices totaling Rs 2,25,000.",
                "doc_type": "freelance",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "escalation_ladder" in data
        assert any("notice" in step["action"].lower() for step in data["escalation_ladder"])
