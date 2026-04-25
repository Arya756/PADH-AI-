"""
agent.py
--------
Core engine for the Student Agent.

Pipeline for each event:
  1. Student LLM reads the event content and attempts the exercise.
  2. Evaluator LLM scores the attempt, identifies concept gaps.
  3. If failed: Content Refiner LLM rewrites the event targeting the gaps.
  4. Aggregate results into a FailureLog + EvaluationResponse.
"""

import os
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

from groq import Groq
from dotenv import load_dotenv

from student_agent.prompts import (
    STUDENT_SYSTEM_PROMPT,
    STUDENT_USER_PROMPT_TEMPLATE,
    STUDENT_TASK_INSTRUCTIONS,
    DEFAULT_TASK_INSTRUCTION,
    EVALUATOR_SYSTEM_PROMPT,
    EVALUATOR_USER_PROMPT_TEMPLATE,
    REFINEMENT_SYSTEM_PROMPT,
    REFINEMENT_USER_PROMPT_TEMPLATE,
)
from student_agent.schemas import (
    EventAttempt,
    ConceptGap,
    FailureLog,
    RefinedEvent,
    EvaluationResponse,
)

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM client  (Groq, same stack as the other agents)
# ---------------------------------------------------------------------------

_GROQ_KEY = os.getenv("GROQ_API_KEY")
_MODEL    = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile").strip()

# Use a lighter/faster model for the student persona to keep latency down
_STUDENT_MODEL   = os.getenv("STUDENT_MODEL", "llama-3.1-8b-instant").strip()
_EVALUATOR_MODEL = os.getenv("EVALUATOR_MODEL", _MODEL).strip()
_REFINER_MODEL   = os.getenv("REFINER_MODEL",   _MODEL).strip()

groq_client = Groq(api_key=_GROQ_KEY)

# Pass rate threshold (0.6 = 60 %) — events below this score are flagged
PASS_THRESHOLD           = float(os.getenv("STUDENT_PASS_THRESHOLD", "0.6"))
# If overall course pass-rate below this, trigger full refinement
COURSE_PASS_THRESHOLD    = float(os.getenv("STUDENT_COURSE_PASS_THRESHOLD", "0.7"))
# Max parallel workers for event processing
MAX_WORKERS              = int(os.getenv("STUDENT_MAX_WORKERS", "3"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _llm(
    system: str,
    user: str,
    model: str = _MODEL,
    temperature: float = 0.5,
    max_tokens: int = 1024,
) -> str:
    """Single LLM call, returns raw content string."""
    response = groq_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def _extract_json(text: str) -> dict:
    """
    Robustly extract a JSON object from an LLM response that may contain
    markdown fences, leading prose, or trailing commentary.
    """
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("```").strip()

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find the outermost { ... } block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning(f"[StudentAgent] Could not parse JSON from: {text[:200]}")
    return {}


# ---------------------------------------------------------------------------
# Step 1 — Student attempt
# ---------------------------------------------------------------------------

def _student_attempt(event_content) -> str:
    """
    Make the 'struggling student' LLM attempt the exercise for a single event.
    Returns raw text (the student's response).
    """
    task_instruction = STUDENT_TASK_INSTRUCTIONS.get(
        event_content.output_format, DEFAULT_TASK_INSTRUCTION
    )

    user_prompt = STUDENT_USER_PROMPT_TEMPLATE.format(
        event_id     = event_content.event_id,
        title        = event_content.title,
        content      = event_content.content,
        output_format= event_content.output_format,
        task_instruction = task_instruction,
        learning_objective = event_content.learning_objective,
    )

    logger.info(f"[StudentAgent] Event {event_content.event_id} – generating student attempt …")
    return _llm(
        system      = STUDENT_SYSTEM_PROMPT,
        user        = user_prompt,
        model       = _STUDENT_MODEL,
        temperature = 0.75,   # Higher temperature → more natural student confusion
        max_tokens  = 800,
    )


# ---------------------------------------------------------------------------
# Step 2 — Evaluator scores the attempt
# ---------------------------------------------------------------------------

def _evaluate_attempt(event_content, student_answer: str) -> dict:
    """
    Evaluator LLM reads the event content + student answer and returns a
    JSON dict with: passed, comprehension_score, concept_gaps, feedback.
    """
    user_prompt = EVALUATOR_USER_PROMPT_TEMPLATE.format(
        title              = event_content.title,
        output_format      = event_content.output_format,
        learning_objective = event_content.learning_objective,
        content            = event_content.content,
        student_attempt    = student_answer,
    )

    logger.info(f"[StudentAgent] Event {event_content.event_id} – evaluating attempt …")
    raw = _llm(
        system      = EVALUATOR_SYSTEM_PROMPT,
        user        = user_prompt,
        model       = _EVALUATOR_MODEL,
        temperature = 0.1,   # Low temperature → deterministic scoring
        max_tokens  = 600,
    )
    return _extract_json(raw)


# ---------------------------------------------------------------------------
# Step 3 — Content Refiner rewrites the event targeting identified gaps
# ---------------------------------------------------------------------------

def _refine_event(event_content, attempt: EventAttempt) -> RefinedEvent:
    """
    Rewrite a failing event's content so that the specific concept gaps
    identified by the evaluator are addressed head-on.
    """
    gaps_text = "\n".join(
        f"  GAP {i+1}: Concept='{g.concept}' | Reason='{g.reason}' | Quote='{g.excerpt}'"
        for i, g in enumerate(attempt.concept_gaps)
    ) or "  (No specific gaps captured — general comprehension was very low; simplify everything.)"

    user_prompt = REFINEMENT_USER_PROMPT_TEMPLATE.format(
        title               = event_content.title,
        output_format       = event_content.output_format,
        learning_objective  = event_content.learning_objective,
        original_content    = event_content.content,
        comprehension_score = attempt.comprehension_score,
        student_answer      = attempt.student_answer[:500],  # cap for token budget
        concept_gaps_text   = gaps_text,
    )

    logger.info(f"[StudentAgent] Event {event_content.event_id} – refining content …")
    refined_text = _llm(
        system      = REFINEMENT_SYSTEM_PROMPT,
        user        = user_prompt,
        model       = _REFINER_MODEL,
        temperature = 0.3,
        max_tokens  = 2048,
    )

    # Build refinement notes
    gap_names = [g.concept for g in attempt.concept_gaps]
    notes = (
        f"Rewritten to address {len(attempt.concept_gaps)} concept gap(s): "
        + (", ".join(gap_names) if gap_names else "general clarity")
        + f". Student scored {attempt.comprehension_score:.0%} before refinement."
    )

    return RefinedEvent(
        event_id         = event_content.event_id,
        title            = event_content.title,
        output_format    = event_content.output_format,
        estimated_duration = event_content.estimated_duration,
        learning_objective = event_content.learning_objective,
        content          = refined_text.strip(),
        original_content = event_content.content,
        refinement_notes = notes,
    )


# ---------------------------------------------------------------------------
# Per-event pipeline  (attempt → evaluate → optionally refine)
# ---------------------------------------------------------------------------

def _process_event(event_content) -> Tuple[EventAttempt, RefinedEvent | None]:
    """
    Full pipeline for a single event. Returns (attempt, refined_event_or_None).
    refined_event is None when the student passed.
    """
    event_id = event_content.event_id

    # ── Step 1: Student attempt ───────────────────────────────────────────
    try:
        student_answer = _student_attempt(event_content)
    except Exception as exc:
        logger.error(f"[StudentAgent] Event {event_id} student attempt failed: {exc}")
        student_answer = "(Student attempt generation failed — treating as total confusion)"

    # ── Step 2: Evaluate ──────────────────────────────────────────────────
    eval_result = {}
    try:
        eval_result = _evaluate_attempt(event_content, student_answer)
    except Exception as exc:
        logger.error(f"[StudentAgent] Event {event_id} evaluation failed: {exc}")

    # Parse eval result safely
    passed             = bool(eval_result.get("passed", False))
    comprehension_score= float(eval_result.get("comprehension_score", 0.3))
    raw_gaps           = eval_result.get("concept_gaps", [])
    feedback           = str(eval_result.get("feedback", "Could not evaluate this attempt."))

    # Override: if score < threshold, force fail
    if comprehension_score < PASS_THRESHOLD:
        passed = False
    elif comprehension_score >= PASS_THRESHOLD:
        passed = True

    # Build ConceptGap objects
    concept_gaps: List[ConceptGap] = []
    for g in raw_gaps if isinstance(raw_gaps, list) else []:
        try:
            concept_gaps.append(ConceptGap(
                concept = str(g.get("concept", "Unknown concept")),
                reason  = str(g.get("reason",  "Not specified")),
                excerpt = str(g.get("excerpt", "")),
            ))
        except Exception:
            pass

    attempt = EventAttempt(
        event_id            = event_id,
        title               = event_content.title,
        output_format       = event_content.output_format,
        passed              = passed,
        comprehension_score = comprehension_score,
        student_answer      = student_answer,
        concept_gaps        = concept_gaps,
        feedback            = feedback,
    )

    logger.info(
        f"[StudentAgent] Event {event_id} – passed={passed}, "
        f"score={comprehension_score:.2f}, gaps={len(concept_gaps)}"
    )

    # ── Step 3: Refine if failed ──────────────────────────────────────────
    refined_event = None
    if not passed:
        try:
            refined_event = _refine_event(event_content, attempt)
            logger.info(f"[StudentAgent] Event {event_id} – refinement complete.")
        except Exception as exc:
            logger.error(f"[StudentAgent] Event {event_id} refinement failed: {exc}")

    return attempt, refined_event


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def evaluate_and_refine(course_content) -> EvaluationResponse:
    """
    Run the full Student Agent pipeline over all events.

    Args:
        course_content: A CourseContent Pydantic model instance
                        (the output of the Content Agent).

    Returns:
        EvaluationResponse with attempts, failure log, and any refined events.
    """
    events = course_content.content
    course_title = course_content.course_title

    logger.info(
        f"[StudentAgent] Starting evaluation – course='{course_title}', "
        f"events={len(events)}, model={_STUDENT_MODEL}"
    )

    all_attempts: List[EventAttempt]  = []
    refined_events: List[RefinedEvent] = []

    # Process events in parallel (capped at MAX_WORKERS to avoid rate limits)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_process_event, event): event
            for event in events
        }
        for future in as_completed(futures):
            event = futures[future]
            try:
                attempt, refined = future.result()
                all_attempts.append(attempt)
                if refined is not None:
                    refined_events.append(refined)
            except Exception as exc:
                logger.error(f"[StudentAgent] Unhandled error for event {event.event_id}: {exc}")
                # Graceful fallback attempt
                all_attempts.append(EventAttempt(
                    event_id            = event.event_id,
                    title               = event.title,
                    output_format       = event.output_format,
                    passed              = False,
                    comprehension_score = 0.0,
                    student_answer      = "(Processing error)",
                    concept_gaps        = [],
                    feedback            = "This event could not be evaluated due to a processing error.",
                ))

    # Sort results by event_id to restore order
    all_attempts.sort(key=lambda a: a.event_id)
    refined_events.sort(key=lambda r: r.event_id)

    # ── Build failure log ─────────────────────────────────────────────────
    n_total  = len(all_attempts)
    n_passed = sum(1 for a in all_attempts if a.passed)
    n_failed = n_total - n_passed
    pass_rate = n_passed / n_total if n_total else 0.0
    overall_passed = pass_rate >= COURSE_PASS_THRESHOLD

    failed_attempts = [a for a in all_attempts if not a.passed]

    # Produce a plain-language summary of the hardest struggle areas
    if failed_attempts:
        all_gap_concepts = [
            g.concept
            for a in failed_attempts
            for g in a.concept_gaps
        ]
        unique_concepts = list(dict.fromkeys(all_gap_concepts))  # preserve order, dedupe
        concept_summary = (
            f"The student struggled most with: {', '.join(unique_concepts[:5])}. "
            if unique_concepts else ""
        )
        summary = (
            f"The student passed {n_passed}/{n_total} events ({pass_rate:.0%}). "
            f"{concept_summary}"
            f"{'Content refinement was triggered for all failing events.' if refined_events else ''}"
        )
    else:
        summary = (
            f"Excellent! The student passed all {n_total} events ({pass_rate:.0%}). "
            "No refinement needed — the course is already accessible to struggling learners."
        )

    failure_log = FailureLog(
        total_events    = n_total,
        passed_events   = n_passed,
        failed_events   = n_failed,
        pass_rate       = pass_rate,
        overall_passed  = overall_passed,
        failed_attempts = failed_attempts,
        summary         = summary,
    )

    # ── Final message ──────────────────────────────────────────────────────
    if overall_passed:
        message = (
            f"✅ Course passed the student test! Pass rate: {pass_rate:.0%}. "
            "The content is accessible to struggling learners."
        )
    else:
        message = (
            f"⚠️ Course failed the student test. Pass rate: {pass_rate:.0%} "
            f"(threshold: {COURSE_PASS_THRESHOLD:.0%}). "
            f"{len(refined_events)} event(s) have been automatically rewritten."
        )

    logger.info(f"[StudentAgent] Evaluation complete. {message}")

    return EvaluationResponse(
        course_title    = course_title,
        failure_log     = failure_log,
        attempts        = all_attempts,
        refined_events  = refined_events,
        final_pass_rate = pass_rate,
        message         = message,
    )
