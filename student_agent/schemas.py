"""
schemas.py
----------
Pydantic models for the Student Agent API.

Flow:
  Input:  EvaluationRequest   (full ContentResponse from the Content Agent)
  Output: EvaluationResponse  (attempt results, failure log, refined content if needed)
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# ---------------------------------------------------------------------------
# Input models  (mirrors ContentResponse from content_agent.schemas)
# ---------------------------------------------------------------------------

class EventContent(BaseModel):
    """A single generated event as returned by the Content Agent."""
    event_id: int
    title: str
    output_format: str
    estimated_duration: str
    learning_objective: str
    content: str
    validation_warning: Optional[str] = None


class CourseContent(BaseModel):
    """The full output from the Content Agent – input to the Student Agent."""
    course_title: str
    prerequisites: List[str] = []
    assessment: str = ""
    content: List[EventContent]


class EvaluationRequest(BaseModel):
    """Top-level request body sent to POST /evaluate-and-refine."""
    course_content: CourseContent


# ---------------------------------------------------------------------------
# Per-event attempt models
# ---------------------------------------------------------------------------

class ConceptGap(BaseModel):
    """A single concept the student failed to understand."""
    concept: str = Field(..., description="The specific concept the student struggled with")
    reason: str = Field(..., description="Why the student found this confusing")
    excerpt: str = Field(..., description="Verbatim short excerpt from the content that caused confusion")


class EventAttempt(BaseModel):
    """The student's attempt at a single learning event."""
    event_id: int
    title: str
    output_format: str
    passed: bool = Field(..., description="True if the student demonstrated adequate understanding")
    comprehension_score: float = Field(..., ge=0.0, le=1.0,
                                       description="0.0 = total confusion, 1.0 = perfect understanding")
    student_answer: str = Field(..., description="The student's actual response / attempted exercise")
    concept_gaps: List[ConceptGap] = Field(default_factory=list,
                                           description="Specific gaps identified when passed=False")
    feedback: str = Field(..., description="Tutor-style feedback on the student's attempt")


# ---------------------------------------------------------------------------
# Failure log & refinement models
# ---------------------------------------------------------------------------

class FailureLog(BaseModel):
    """Aggregated failure log produced after the student attempts all events."""
    total_events: int
    passed_events: int
    failed_events: int
    pass_rate: float
    overall_passed: bool = Field(..., description="True if pass_rate >= 0.7")
    failed_attempts: List[EventAttempt] = Field(
        default_factory=list,
        description="All events where passed=False"
    )
    summary: str = Field(..., description="Plain-language summary of what the student struggled with most")


class RefinedEvent(BaseModel):
    """An event that has been rewritten by the Content Agent after review of the failure log."""
    event_id: int
    title: str
    output_format: str
    estimated_duration: str
    learning_objective: str
    content: str                     # ← the IMPROVED content
    original_content: str            # ← preserved for comparison
    refinement_notes: str = Field(..., description="What was changed and why")


# ---------------------------------------------------------------------------
# Top-level response model
# ---------------------------------------------------------------------------

class EvaluationResponse(BaseModel):
    """Full response from POST /evaluate-and-refine."""
    course_title: str
    failure_log: FailureLog
    attempts: List[EventAttempt]
    refined_events: List[RefinedEvent] = Field(
        default_factory=list,
        description="Non-empty only when overall_passed=False; contains rewritten events."
    )
    final_pass_rate: float = Field(
        ...,
        description="Pass rate after optional refinement (same as original if no refinement needed)"
    )
    message: str = Field(..., description="Human-readable summary of the evaluation outcome")
    final_course_content: CourseContent = Field(
        ...,
        description="The completely refined and polished course content to be shown to the user."
    )
