"""
main.py
-------
FastAPI router for the Student Agent.

POST /evaluate-and-refine
  Body:    EvaluationRequest  (full ContentResponse from the Content Agent)
  Returns: EvaluationResponse (attempts, failure log, refined content)
"""

import logging
from fastapi import APIRouter, HTTPException

from student_agent.schemas import EvaluationRequest, EvaluationResponse
from student_agent.agent import evaluate_and_refine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Student Agent"])


@router.post("/evaluate-and-refine", response_model=EvaluationResponse)
def evaluate_course(request: EvaluationRequest):
    """
    Run the Simulated Student Agent over the generated course content.

    The agent:
    1. Reads each event as the 'weakest student in class'.
    2. Attempts the exercises/comprehension tasks.
    3. An evaluator LLM scores each attempt and identifies concept gaps.
    4. Failing events are automatically rewritten by a Refinement LLM
       that directly addresses each identified gap.

    Returns a full evaluation report including:
    - Per-event attempt details and comprehension scores
    - Aggregated failure log with concept gap analysis
    - Rewritten versions of any failing events
    """
    course_content = request.course_content

    if not course_content.content:
        raise HTTPException(
            status_code=400,
            detail="course_content.content must contain at least one event."
        )

    if not course_content.course_title or len(course_content.course_title.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="course_content.course_title is missing or invalid."
        )

    logger.info(
        f"[/evaluate-and-refine] Received request – "
        f"course='{course_content.course_title}', events={len(course_content.content)}"
    )

    try:
        result = evaluate_and_refine(course_content)
    except Exception as exc:
        logger.exception("Student Agent evaluation failed unexpectedly.")
        raise HTTPException(
            status_code=500,
            detail=f"Student Agent failed: {str(exc)}"
        )

    return result
