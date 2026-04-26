"""
agent.py
--------
Content generation engine for the Content Agent.

Flow for each event:
  1. (Optional) Web-search Tavily for real-world grounding data.
  2. Build a format-specific prompt using format_handlers.py.
  3. Call Groq LLM (primary) with the enriched prompt.
  4. Validate output; if invalid, retry once then fall back gracefully.
  5. Return structured ContentResponse.
"""

import os
import json
import logging
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from groq import Groq

from content_agent.config import GROQ_API_KEY, TAVILY_API_KEY, LLM_MODEL
from content_agent.format_handlers import get_prompts_for_event
from content_agent.validator import validate_event_content

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

groq_client = Groq(api_key=GROQ_API_KEY)

# Tavily is optional – import only if key is present
_tavily_client = None
if TAVILY_API_KEY:
    try:
        from tavily import TavilyClient
        _tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
        logger.info("Tavily web-search client initialised.")
    except ImportError:
        logger.warning("tavily-python not installed – web search disabled.")

# ---------------------------------------------------------------------------
# Output-formats that benefit from a web-search enrichment pass
# ---------------------------------------------------------------------------
WEB_SEARCH_FORMATS = {
    "hook",
    "lecture_with_formula",
    "worked_example",
    "practice_problem",
    "assessment_task",
}

# ---------------------------------------------------------------------------
# Per-event generation
# ---------------------------------------------------------------------------

def _web_search(query: str, max_results: int = 3) -> str:
    """Return a brief summary from Tavily, or empty string on any failure."""
    if not _tavily_client:
        return ""
    try:
        results = _tavily_client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=True,
        )
        answer = results.get("answer", "")
        snippets = [r.get("content", "")[:300] for r in results.get("results", [])]
        combined = (answer + "\n\n" + "\n\n".join(snippets)).strip()
        return combined[:1500]  # cap to avoid token bloat
    except Exception as exc:
        logger.warning(f"Tavily search failed: {exc}")
        return ""


import time

def _call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
    """Single LLM call via Groq. Returns the raw text content. Handles rate limits with backoff."""
    for attempt in range(3):
        try:
            response = groq_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=2048,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                logger.warning(f"Rate limit hit. Sleeping for 4s... (Attempt {attempt+1}/3)")
                time.sleep(4)
                continue
            raise e
    
    return ""


def _generate_for_event(event, course_title: str) -> dict:
    """
    Full generation pipeline for a single Event object.
    Returns {"event_id": int, "title": str, "output_format": str, "content": str}
    """
    event_id = event.event_id
    output_format = event.output_format

    logger.info(f"[Event {event_id}] Generating – format={output_format}, depth={event.technical_depth}")

    # ── 1. Optional web-search enrichment ─────────────────────────────────
    web_context = ""
    if output_format in WEB_SEARCH_FORMATS and _tavily_client:
        search_query = (
            f"{course_title} {event.title} technical depth {event.technical_depth} real-world application"
        )
        web_context = _web_search(search_query)
        if web_context:
            logger.info(f"[Event {event_id}] Web context retrieved ({len(web_context)} chars)")

    # ── 2. Build format-specific prompts ──────────────────────────────────
    system_prompt, user_prompt = get_prompts_for_event(event)

    # Inject web context into user prompt if available
    if web_context:
        user_prompt = (
            f"[REAL-WORLD CONTEXT FROM WEB SEARCH – use to ground your content]\n"
            f"{web_context}\n\n"
            "---\n\n"
            + user_prompt
        )

    # ── 3. Primary LLM call ───────────────────────────────────────────────
    content = ""
    try:
        content = _call_llm(system_prompt, user_prompt, temperature=0.4)
    except Exception as exc:
        logger.error(f"[Event {event_id}] Primary LLM call failed: {exc}")

    # ── 4. Validate; retry once with higher temperature if needed ─────────
    if not validate_event_content(content, output_format):
        logger.warning(f"[Event {event_id}] Validation failed – retrying…")
        try:
            content = _call_llm(system_prompt, user_prompt, temperature=0.7)
        except Exception as exc:
            logger.error(f"[Event {event_id}] Retry LLM call failed: {exc}")
            content = _fallback_content(event)

    # Final safety net
    if not content or len(content.strip()) < 50:
        content = _fallback_content(event)

    logger.info(f"[Event {event_id}] Done – {len(content.split())} words")

    return {
        "event_id": event_id,
        "title": event.title,
        "output_format": output_format,
        "estimated_duration": event.estimated_duration,
        "learning_objective": event.learning_objective,
        "content": content.strip(),
    }


def _fallback_content(event) -> str:
    """Minimal graceful fallback when LLM fails entirely."""
    return (
        f"**{event.title}**\n\n"
        f"*Instruction:* {event.instruction}\n\n"
        f"*Example:* {event.example}\n\n"
        f"*Learning Objective:* {event.learning_objective}\n\n"
        "_(Content generation encountered an error. Please retry.)_"
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_content(blueprint) -> dict:
    """
    Generate content for all events in the blueprint.

    Events are processed in parallel (up to 4 workers) to reduce latency.
    Results are reassembled in event_id order.

    Args:
        blueprint: A Blueprint Pydantic model instance.

    Returns:
        dict with keys: course_title, prerequisites, assessment, content (list)
    """
    course_title = blueprint.course_title
    events = blueprint.events

    logger.info(
        f"Content generation started – course='{course_title}', "
        f"events={len(events)}, model={LLM_MODEL}"
    )

    results: List[dict] = []

    # Parallel generation — up to 2 concurrent event generations to respect TPM limits
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_event = {
            executor.submit(_generate_for_event, event, course_title): event
            for event in events
        }
        for future in as_completed(future_to_event):
            event = future_to_event[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                logger.error(f"[Event {event.event_id}] Unhandled error: {exc}")
                results.append({
                    "event_id": event.event_id,
                    "title": event.title,
                    "output_format": event.output_format,
                    "estimated_duration": event.estimated_duration,
                    "learning_objective": event.learning_objective,
                    "content": _fallback_content(event),
                })

    # Sort by event_id to restore blueprint order
    results.sort(key=lambda r: r["event_id"])

    logger.info(f"Content generation complete – {len(results)} events produced.")

    return {
        "course_title": course_title,
        "prerequisites": blueprint.prerequisites,
        "assessment": blueprint.assessment,
        "content": results,
    }
