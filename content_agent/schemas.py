"""
schemas.py
----------
Pydantic models for the Content Agent API.

Input:  ContentRequest  → Blueprint → List[Event]
Output: ContentResponse → List[EventContent]
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

VALID_OUTPUT_FORMATS = {
    "hook",
    "objectives_list",
    "quiz",
    "lecture_with_formula",
    "worked_example",
    "practice_problem",
    "feedback_rubric",
    "assessment_task",
    "reflection_essay",
}

VALID_DEPTHS = {"Basic", "Intermediate", "Advanced"}


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

class Event(BaseModel):
    event_id: int = Field(..., ge=1, description="Sequential event identifier")
    title: str = Field(..., min_length=3)
    instruction: str = Field(..., min_length=10)
    example: str = Field(..., min_length=10)
    technical_depth: str = Field(..., description="Basic | Intermediate | Advanced")
    learning_objective: str = Field(..., min_length=10)
    output_format: str = Field(..., description="One of the recognised format keys")
    estimated_duration: str = Field(..., min_length=2)

    @field_validator("instruction", "example", "learning_objective")
    @classmethod
    def reject_placeholders(cls, v: str) -> str:
        if v.strip().lower() in {"string", "test", "none", "null", "", "abc", "---"}:
            raise ValueError(f"Placeholder value not allowed: '{v}'")
        return v

    @field_validator("technical_depth")
    @classmethod
    def validate_depth(cls, v: str) -> str:
        if v not in VALID_DEPTHS:
            raise ValueError(f"technical_depth must be one of {VALID_DEPTHS}, got '{v}'")
        return v

    @field_validator("output_format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in VALID_OUTPUT_FORMATS:
            # Don't hard-fail — unknown formats get the generic handler
            pass
        return v


class Blueprint(BaseModel):
    course_title: str = Field(..., min_length=3)
    prerequisites: List[str] = []
    assessment: str = ""
    events: List[Event] = Field(..., min_length=1)


class ContentRequest(BaseModel):
    blueprint: Blueprint


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class EventContent(BaseModel):
    event_id: int
    title: str
    output_format: str
    estimated_duration: str
    learning_objective: str
    content: str
    validation_warning: Optional[str] = None


class ContentResponse(BaseModel):
    course_title: str
    prerequisites: List[str] = []
    assessment: str = ""
    content: List[EventContent]
