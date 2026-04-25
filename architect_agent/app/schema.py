from pydantic import BaseModel
from typing import List, Optional


class Event(BaseModel):
    event_id: int
    title: str
    instruction: str
    example: str
    technical_depth: str
    learning_objective: str
    output_format: str
    estimated_duration: str


class Blueprint(BaseModel):
    course_title: str
    prerequisites: List[str]
    assessment: str
    events: List[Event]