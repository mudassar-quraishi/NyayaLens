"""
API route for Situation Navigator (Phase 8 Stretch).
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.agents.navigator import navigate_situation

logger = logging.getLogger("nyayalens.api.navigator")

router = APIRouter(prefix="/api", tags=["navigator"])


class NavigatorRequest(BaseModel):
    user_situation: str
    doc_context: str = ""
    doc_type: str = "general"


@router.post("/navigator")
async def process_dispute_situation(
    req: NavigatorRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Intake a user dispute situation and generate an escalation ladder,
    evidence checklist, estimated time/cost ranges, and free legal aid resources.
    """
    if not req.user_situation.strip():
        raise HTTPException(400, "Situation description cannot be empty")

    result = await navigate_situation(
        user_situation=req.user_situation,
        doc_context=req.doc_context,
        doc_type=req.doc_type,
    )
    return result
