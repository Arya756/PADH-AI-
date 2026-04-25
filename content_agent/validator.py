"""
validator.py
------------
Format-aware content validation for the Content Agent.

Each output_format has its own minimum requirements.
"""

# ---------------------------------------------------------------------------
# Format-specific validation rules
# ---------------------------------------------------------------------------

# (min_words, required_keywords)
FORMAT_RULES = {
    "hook": (
        150,
        [],  # free-form narrative; just check word count
    ),
    "objectives_list": (
        100,
        ["•"],  # must contain bullet points
    ),
    "quiz": (
        150,
        ["Q1.", "Q2.", "Q3.", "Correct Answer"],  # must have multiple questions
    ),
    "lecture_with_formula": (
        300,
        ["##", "```"],  # must have headers and a code/pseudo-code block
    ),
    "worked_example": (
        350,
        ["## Scenario", "## Step"],  # must follow the stepped structure
    ),
    "practice_problem": (
        200,
        ["## Scenario", "## Your Task"],
    ),
    "feedback_rubric": (
        250,
        ["## ", "Pitfall", "|"],  # must have a table
    ),
    "assessment_task": (
        350,
        ["## ", "Stakeholder", "|"],
    ),
    "reflection_essay": (
        200,
        ["1.", "2.", "3."],  # must have numbered prompts
    ),
}

GENERIC_MIN_WORDS = 100


def validate_event_content(text: str, output_format: str = "") -> bool:
    """
    Returns True if the generated content meets the minimum requirements
    for its output_format.
    """
    if not text or not text.strip():
        return False

    word_count = len(text.split())
    min_words, required_keywords = FORMAT_RULES.get(
        output_format, (GENERIC_MIN_WORDS, [])
    )

    # Word count gate
    if word_count < min_words:
        return False

    # Keyword presence gate
    for kw in required_keywords:
        if kw not in text:
            return False

    return True


def validate_full_response(content_list: list, events: list = None) -> list:
    """
    Validates a list of generated event content dicts.
    Items that fail validation are flagged but kept (content is marked as unavailable
    so the caller can decide what to do).
    """
    validated = []

    for item in content_list:
        event_id = item.get("event_id")
        output_format = item.get("output_format", "")
        content = item.get("content", "")

        if validate_event_content(content, output_format):
            validated.append(item)
        else:
            # Keep the item but flag it
            validated.append({
                **item,
                "content": content or "content unavailable",
                "validation_warning": (
                    f"Content for event {event_id} did not meet quality thresholds "
                    f"for format '{output_format}'."
                ),
            })

    return validated