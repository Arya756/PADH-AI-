"""
main.py
-------
FastAPI router for the Content Agent.

POST /generate-content
  Body:  ContentRequest  (blueprint from the Architecture Agent)
  Returns: ContentResponse (per-event generated content)
"""

import logging
from fastapi import APIRouter, HTTPException

from .schemas import ContentRequest, ContentResponse
from .agent import generate_content

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLACEHOLDER_VALUES = {"string", "null", "none", "test", "abc", "---", ""}


def _is_placeholder(text: str) -> bool:
    return not text or text.strip().lower() in _PLACEHOLDER_VALUES


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/generate-content", response_model=ContentResponse)
def generate_content_api(request: ContentRequest):
    """
    Accept an Architecture Agent blueprint and return fully generated
    course content for every event, respecting each event's output_format,
    instruction, example, and technical_depth.
    """
    blueprint = request.blueprint

    # ── Validate course title ─────────────────────────────────────────────
    if _is_placeholder(blueprint.course_title):
        raise HTTPException(status_code=400, detail="Invalid or missing course_title.")

    # ── Validate each event ───────────────────────────────────────────────
    for event in blueprint.events:
        if _is_placeholder(event.instruction):
            raise HTTPException(
                status_code=400,
                detail=f"Event {event.event_id}: instruction is empty or a placeholder.",
            )
        if _is_placeholder(event.example):
            raise HTTPException(
                status_code=400,
                detail=f"Event {event.event_id}: example is empty or a placeholder.",
            )
        if _is_placeholder(event.output_format):
            raise HTTPException(
                status_code=400,
                detail=f"Event {event.event_id}: output_format is required.",
            )

    logger.info(
        f"Received content generation request – "
        f"course='{blueprint.course_title}', events={len(blueprint.events)}"
    )

    # ── Generate ──────────────────────────────────────────────────────────
    try:
        result = generate_content(blueprint)
    except Exception as exc:
        logger.exception("Content generation failed unexpectedly.")
        raise HTTPException(
            status_code=500,
            detail=f"Content generation failed: {str(exc)}",
        )

    return result