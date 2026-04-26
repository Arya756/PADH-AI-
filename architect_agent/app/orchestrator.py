import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
import os

from content_agent.schemas import Blueprint
from content_agent.agent import _generate_for_event, _fallback_content
from student_agent.agent import _process_event, COURSE_PASS_THRESHOLD
from student_agent.schemas import EventContent, EvaluationResponse, FailureLog, EventAttempt, RefinedEvent, CourseContent

logger = logging.getLogger(__name__)
MAX_WORKERS = int(os.getenv("STUDENT_MAX_WORKERS", "3"))

def process_single_event_pipeline(event_blueprint, course_title) -> tuple[EventContent, EventAttempt, RefinedEvent | None]:
    """Drafts an event, then instantly enters the Student Agent loop for that specific event."""
    # 1. Draft
    try:
        draft_dict = _generate_for_event(event_blueprint, course_title)
    except Exception as exc:
        logger.error(f"[EndToEnd] Event {event_blueprint.event_id} draft failed: {exc}")
        draft_dict = {
            "event_id": event_blueprint.event_id,
            "title": event_blueprint.title,
            "output_format": event_blueprint.output_format,
            "estimated_duration": event_blueprint.estimated_duration,
            "learning_objective": event_blueprint.learning_objective,
            "content": _fallback_content(event_blueprint),
        }
    
    event_content = EventContent(**draft_dict)
    
    # 2. Iterate Student Loop
    MAX_ITERATIONS = 1
    final_attempt = None
    final_refined = None
    
    for _ in range(MAX_ITERATIONS):
        attempt, refined = _process_event(event_content)
        final_attempt = attempt
        if attempt.passed:
            break
        if refined is not None:
            final_refined = refined
            event_content.content = refined.content
            
    # If it failed and we somehow got no attempt (crashed), create a dummy
    if not final_attempt:
        final_attempt = EventAttempt(
            event_id=event_blueprint.event_id, title=event_blueprint.title,
            output_format=event_blueprint.output_format, passed=False,
            comprehension_score=0.0, student_answer="Error", concept_gaps=[], feedback="Error"
        )
        
    return event_content, final_attempt, final_refined

def run_end_to_end_pipeline(blueprint: Blueprint) -> EvaluationResponse:
    events = blueprint.events
    course_title = blueprint.course_title
    
    final_events_map = {}
    attempts_map = {}
    refined_map = {}
    
    logger.info(f"[EndToEnd] Starting Pipelined Generation & Evaluation for {len(events)} events.")
    
    # Run all events concurrently
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_single_event_pipeline, ev, course_title): ev
            for ev in events
        }
        for future in as_completed(futures):
            ev = futures[future]
            try:
                final_ev, attempt, refined = future.result()
                final_events_map[ev.event_id] = final_ev
                attempts_map[ev.event_id] = attempt
                if refined:
                    refined_map[ev.event_id] = refined
            except Exception as exc:
                logger.error(f"[EndToEnd] Fatal error in pipeline for event {ev.event_id}: {exc}")
                
    # Reassemble in order
    final_events = [final_events_map[e.event_id] for e in events if e.event_id in final_events_map]
    all_attempts = [attempts_map[e.event_id] for e in events if e.event_id in attempts_map]
    refined_events = [refined_map[e.event_id] for e in events if e.event_id in refined_map]
    
    # Stats
    n_total = len(all_attempts)
    n_passed = sum(1 for a in all_attempts if a.passed)
    n_failed = n_total - n_passed
    pass_rate = n_passed / n_total if n_total else 0.0
    overall_passed = pass_rate >= COURSE_PASS_THRESHOLD

    failed_attempts = [a for a in all_attempts if not a.passed]
    if failed_attempts:
        unique_concepts = list(dict.fromkeys([g.concept for a in failed_attempts for g in a.concept_gaps]))
        summary = f"Pipelined generation complete. Passed {n_passed}/{n_total} events ({pass_rate:.0%}). Hardest concepts: {', '.join(unique_concepts[:5])}."
    else:
        summary = f"Pipelined generation complete! Passed {n_passed}/{n_total} events ({pass_rate:.0%})."

    failure_log = FailureLog(
        total_events=n_total, passed_events=n_passed, failed_events=n_failed,
        pass_rate=pass_rate, overall_passed=overall_passed,
        failed_attempts=failed_attempts, summary=summary,
    )
    
    course_content_obj = CourseContent(
        course_title=course_title,
        prerequisites=blueprint.prerequisites,
        assessment=blueprint.assessment,
        content=final_events
    )

    return EvaluationResponse(
        course_title=course_title,
        failure_log=failure_log,
        attempts=all_attempts,
        refined_events=refined_events,
        final_pass_rate=pass_rate,
        message="Pipelined generation finished.",
        final_course_content=course_content_obj,
    )
