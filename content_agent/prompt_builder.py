"""
prompt_builder.py
-----------------
Legacy compatibility shim.

The prompt-building logic has been moved to format_handlers.py which
provides per-format specialised prompts.  This module re-exports the
dispatcher so any external code that imports build_prompt() still works.
"""

from content_agent.format_handlers import get_prompts_for_event


def build_prompt(blueprint):
    """
    Legacy function — builds a combined prompt for the first event only.
    Prefer calling get_prompts_for_event(event) directly per event.
    """
    if not blueprint.events:
        return "", ""
    return get_prompts_for_event(blueprint.events[0])