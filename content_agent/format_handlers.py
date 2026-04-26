"""
format_handlers.py
------------------
Each function receives a single Event object and returns a (system_prompt, user_prompt) tuple
tailored to that event's output_format.  All prompts enforce the instruction, example,
learning_objective, and technical_depth from the blueprint.
"""

from typing import Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEPTH_GUIDANCE = {
    "Basic": (
        "Use plain language. Avoid jargon. Focus on intuition and real-world analogies. "
        "Assume the learner has minimal background knowledge."
    ),
    "Intermediate": (
        "Use precise technical vocabulary. Provide step-by-step reasoning. "
        "Assume the learner knows Python fundamentals and basic AI concepts."
    ),
    "Advanced": (
        "Go deep. Discuss trade-offs, edge cases, and production considerations. "
        "Assume the learner can read code, evaluate architectures, and reason about design decisions."
    ),
}


def _depth(level: str) -> str:
    return DEPTH_GUIDANCE.get(level, DEPTH_GUIDANCE["Intermediate"])


# ---------------------------------------------------------------------------
# 1. hook  (event_id=1)
# ---------------------------------------------------------------------------

def build_hook_prompt(event) -> Tuple[str, str]:
    system = (
        "You are an expert instructional designer specialising in immersive course openers. "
        "Your job is to write a compelling HOOK section that pulls the learner in immediately. "
        f"Technical depth: {event.technical_depth}. {_depth(event.technical_depth)}\n\n"
        "OUTPUT RULES:\n"
        "- Open with a vivid, concrete real-world scenario (3-4 sentences).\n"
        "- Follow with a 'Why this matters' paragraph (2-3 sentences) explaining the business/human impact.\n"
        "- End with a provocative question or bold statement that frames the learning ahead.\n"
        "- Do NOT use bullet points in the scenario paragraph.\n"
        "- Total length: 200-300 words.\n"
        "- Return ONLY the hook text. No JSON wrappers."
    )
    user = (
        f"Course: {event.title}\n\n"
        f"Instruction: {event.instruction}\n\n"
        f"Grounding Example: {event.example}\n\n"
        f"Learning Objective: {event.learning_objective}\n\n"
        "Write the hook section now."
    )
    return system, user


# ---------------------------------------------------------------------------
# 2. objectives_list  (event_id=2)
# ---------------------------------------------------------------------------

def build_objectives_list_prompt(event) -> Tuple[str, str]:
    system = (
        "You are a curriculum architect writing clear, measurable learning objectives. "
        f"Technical depth: {event.technical_depth}. {_depth(event.technical_depth)}\n\n"
        "OUTPUT RULES:\n"
        "- Write a one-sentence course overview paragraph.\n"
        "- Then list exactly 5-7 learning objectives using Bloom's taxonomy action verbs "
        "(e.g., Identify, Explain, Apply, Analyse, Design, Evaluate).\n"
        "- Format each objective as: '- [Verb] [specific skill or knowledge]'\n"
        "- After the list, write a 2-sentence paragraph on how these objectives connect to real-world practice.\n"
        "- Total length: 150-250 words.\n"
        "- Return ONLY the objectives content. No JSON wrappers."
    )
    user = (
        f"Course: {event.title}\n\n"
        f"Instruction: {event.instruction}\n\n"
        f"Example context: {event.example}\n\n"
        f"Core learning objective: {event.learning_objective}\n\n"
        "Write the objectives list section now."
    )
    return system, user


# ---------------------------------------------------------------------------
# 3. quiz  (event_id=3)
# ---------------------------------------------------------------------------

def build_quiz_prompt(event) -> Tuple[str, str]:
    system = (
        "You are an expert assessment designer creating a prerequisite knowledge check. "
        f"Technical depth: {event.technical_depth}. {_depth(event.technical_depth)}\n\n"
        "OUTPUT RULES:\n"
        "Generate exactly 5 multiple-choice questions. For each question use this format:\n\n"
        "Q[N]. [Question text]\n"
        "   A) [Option A]\n"
        "   B) [Option B]\n"
        "   C) [Option C]\n"
        "   D) [Option D]\n"
        "Correct Answer: [Letter]) [Brief explanation – 1-2 sentences]\n\n"
        "CRITICAL INSTRUCTION: The questions MUST test the underlying PREREQUISITES and fundamental concepts needed to understand the course topic, NOT the course topic itself. Do not teach or test the core subject of the course. Test only what the student should already know before taking this course.\n"
        "Questions must progress from recall → understanding → simple application.\n"
        "Return ONLY the quiz. No intro paragraph. No JSON wrappers."
    )
    user = (
        f"Course Topic: {event.title} (Do NOT test this topic directly! Test its prerequisites)\n\n"
        f"Instruction (Focus on these fundamentals): {event.instruction}\n\n"
        f"Example prerequisite topics: {event.example}\n\n"
        f"Learning Objective: {event.learning_objective}\n\n"
        "Generate the 5-question prerequisite diagnostic quiz now."
    )
    return system, user


# ---------------------------------------------------------------------------
# 4. lecture_with_formula  (event_id=4)
# ---------------------------------------------------------------------------

def build_lecture_with_formula_prompt(event) -> Tuple[str, str]:
    system = (
        "You are a senior technical instructor delivering a lecture on the core framework or concept. "
        f"Technical depth: {event.technical_depth}. {_depth(event.technical_depth)}\n\n"
        "OUTPUT RULES:\n"
        "Structure the lecture EXACTLY as follows:\n\n"
        "## Concept Overview\n"
        "[2-3 paragraph explanation of the core concept]\n\n"
        "## Core Components\n"
        "[Explain each component or step relevant to this event. "
        "Use sub-bullets for properties/use-cases]\n\n"
        "## The Framework Formula\n"
        "[Describe the end-to-end development workflow as a numbered sequence. "
        "Include a conceptual pseudo-code block (``` fenced) showing the component interactions]\n\n"
        "## Key Takeaways\n"
        "[3-5 bullet points summarising the lecture]\n\n"
        "Total length: 400-600 words.\n"
        "Return ONLY the lecture. No JSON wrappers."
    )
    user = (
        f"Course: {event.title}\n\n"
        f"Instruction: {event.instruction}\n\n"
        f"Grounding Example: {event.example}\n\n"
        f"Learning Objective: {event.learning_objective}\n\n"
        "Write the full lecture section now."
    )
    return system, user


# ---------------------------------------------------------------------------
# 5. worked_example  (event_id=5)
# ---------------------------------------------------------------------------

def build_worked_example_prompt(event) -> Tuple[str, str]:
    system = (
        "You are an expert instructor guiding learners through a complete case study step by step. "
        f"Technical depth: {event.technical_depth}. {_depth(event.technical_depth)}\n\n"
        "OUTPUT RULES:\n"
        "Structure the worked example EXACTLY as follows:\n\n"
        "## Scenario\n"
        "[Describe the real-world problem in 2-3 sentences based on the grounding example]\n\n"
        "## Requirements Analysis\n"
        "[List 4-5 functional and non-functional requirements]\n\n"
        "## Step-by-Step Design\n"
        "Walk through each step with:\n"
        "  **Step N: [Step Title]**\n"
        "  [Explanation + rationale for this design choice]\n"
        "  [Pseudo-code or configuration snippet in a ``` block]\n\n"
        "Cover at minimum: defining the LLM, building the prompt template, "
        "creating the chain, adding memory, and testing the interaction.\n\n"
        "## Expected Outcome\n"
        "[Describe what a successful implementation looks like in 2-3 sentences]\n\n"
        "Total length: 500-700 words.\n"
        "Return ONLY the worked example. No JSON wrappers."
    )
    user = (
        f"Course: {event.title}\n\n"
        f"Instruction: {event.instruction}\n\n"
        f"Grounding Example: {event.example}\n\n"
        f"Learning Objective: {event.learning_objective}\n\n"
        "Write the full guided case study now."
    )
    return system, user


# ---------------------------------------------------------------------------
# 6. practice_problem  (event_id=6)
# ---------------------------------------------------------------------------

def build_practice_problem_prompt(event) -> Tuple[str, str]:
    system = (
        "You are an expert instructional designer creating a hands-on practice scenario. "
        f"Technical depth: {event.technical_depth}. {_depth(event.technical_depth)}\n\n"
        "OUTPUT RULES:\n"
        "Structure the practice problem EXACTLY as follows:\n\n"
        "## Scenario\n"
        "[New real-world scenario derived from the grounding example, 3-4 sentences]\n\n"
        "## Your Task\n"
        "[Clear numbered list of 4-6 tasks the learner must complete]\n\n"
        "## Constraints & Requirements\n"
        "[3-5 specific technical constraints that make this challenging]\n\n"
        "## Deliverables\n"
        "[What the learner must submit/produce: architecture diagram description, "
        "pseudo-code, configuration decisions, etc.]\n\n"
        "## Hints (Optional)\n"
        "[2-3 non-spoiler hints pointing to relevant concepts]\n\n"
        "Total length: 300-450 words.\n"
        "Return ONLY the practice problem. No JSON wrappers."
    )
    user = (
        f"Course: {event.title}\n\n"
        f"Instruction: {event.instruction}\n\n"
        f"Grounding Example: {event.example}\n\n"
        f"Learning Objective: {event.learning_objective}\n\n"
        "Write the practice problem now."
    )
    return system, user


# ---------------------------------------------------------------------------
# 7. feedback_rubric  (event_id=7)
# ---------------------------------------------------------------------------

def build_feedback_rubric_prompt(event) -> Tuple[str, str]:
    system = (
        "You are a senior instructor providing model reasoning and a grading rubric. "
        f"Technical depth: {event.technical_depth}. {_depth(event.technical_depth)}\n\n"
        "OUTPUT RULES:\n"
        "Structure the feedback rubric EXACTLY as follows:\n\n"
        "## Ideal Solution Walkthrough\n"
        "[Walk through the correct approach for the previous practice problem step by step]\n\n"
        "## Common Pitfalls & Misconceptions\n"
        "[List 4-5 common mistakes learners make, each with a brief explanation of WHY it is wrong "
        "and what the correct approach is]\n\n"
        "## Grading Rubric\n"
        "| Criterion | Excellent (4) | Good (3) | Needs Work (2) | Incomplete (1) |\n"
        "|-----------|--------------|----------|----------------|----------------|\n"
        "[Fill in 4-5 rows covering key aspects: architecture, component selection, "
        "memory/context handling, scalability, documentation]\n\n"
        "## What to Do if You Struggled\n"
        "[2-3 specific next steps for learners who found this difficult]\n\n"
        "Total length: 400-550 words.\n"
        "Return ONLY the feedback rubric. No JSON wrappers."
    )
    user = (
        f"Course: {event.title}\n\n"
        f"Instruction: {event.instruction}\n\n"
        f"Grounding Example: {event.example}\n\n"
        f"Learning Objective: {event.learning_objective}\n\n"
        "Write the model reasoning and feedback rubric now."
    )
    return system, user


# ---------------------------------------------------------------------------
# 8. assessment_task  (event_id=8)
# ---------------------------------------------------------------------------

def build_assessment_task_prompt(event) -> Tuple[str, str]:
    system = (
        "You are designing a comprehensive final assessment for an advanced technical course. "
        f"Technical depth: {event.technical_depth}. {_depth(event.technical_depth)}\n\n"
        "OUTPUT RULES:\n"
        "Structure the assessment EXACTLY as follows:\n\n"
        "## Case Study: Complex Real-World Challenge\n"
        "[Describe a detailed scenario with CONFLICTING requirements – "
        "e.g., cost vs. quality, speed vs. accuracy. 4-5 sentences]\n\n"
        "## Stakeholder Requirements\n"
        "[Present 3 different stakeholder perspectives (e.g., CTO, Customer Support Lead, "
        "Data Privacy Officer) each with 2-3 conflicting demands]\n\n"
        "## Assessment Tasks\n"
        "[Numbered list of 5-7 concrete tasks the learner must complete]\n\n"
        "## Evaluation Criteria\n"
        "| Dimension | Weight | Description |\n"
        "|-----------|--------|-------------|\n"
        "[5-6 rows covering: technical correctness, design justification, "
        "conflict resolution, scalability, documentation]\n\n"
        "## Submission Instructions\n"
        "[Clear instructions on what to submit and in what format]\n\n"
        "Total length: 500-700 words.\n"
        "Return ONLY the assessment task. No JSON wrappers."
    )
    user = (
        f"Course: {event.title}\n\n"
        f"Instruction: {event.instruction}\n\n"
        f"Grounding Example: {event.example}\n\n"
        f"Learning Objective: {event.learning_objective}\n\n"
        "Write the comprehensive assessment task now."
    )
    return system, user


# ---------------------------------------------------------------------------
# 9. reflection_essay  (event_id=9)
# ---------------------------------------------------------------------------

def build_reflection_essay_prompt(event) -> Tuple[str, str]:
    system = (
        "You are an instructional coach guiding learners to connect course knowledge to their real life. "
        f"Technical depth: {event.technical_depth}. {_depth(event.technical_depth)}\n\n"
        "OUTPUT RULES:\n"
        "Structure the reflection essay prompt EXACTLY as follows:\n\n"
        "## Personal Application Challenge\n"
        "[2-3 sentence framing of the challenge: apply the concepts to their own organisation/context]\n\n"
        "## Reflection Prompts\n"
        "Provide 5 open-ended reflection questions that guide the essay:\n"
        "1. [Question about identifying a real problem]\n"
        "2. [Question about which specific components or techniques they would use and why]\n"
        "3. [Question about challenges and how they would overcome them]\n"
        "4. [Question about measuring success/impact]\n"
        "5. [Question about what they learned about themselves as a builder]\n\n"
        "## Essay Guidelines\n"
        "[Word count target, structure expectations, and what distinguishes a great reflection]\n\n"
        "## Example Starter\n"
        "[A 3-4 sentence example opening that models good reflective writing tone]\n\n"
        "Total length: 300-450 words.\n"
        "Return ONLY the reflection essay prompt. No JSON wrappers."
    )
    user = (
        f"Course: {event.title}\n\n"
        f"Instruction: {event.instruction}\n\n"
        f"Grounding Example: {event.example}\n\n"
        f"Learning Objective: {event.learning_objective}\n\n"
        "Write the personal application reflection prompt now."
    )
    return system, user


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

FORMAT_HANDLERS = {
    "hook": build_hook_prompt,
    "objectives_list": build_objectives_list_prompt,
    "quiz": build_quiz_prompt,
    "lecture_with_formula": build_lecture_with_formula_prompt,
    "worked_example": build_worked_example_prompt,
    "practice_problem": build_practice_problem_prompt,
    "feedback_rubric": build_feedback_rubric_prompt,
    "assessment_task": build_assessment_task_prompt,
    "reflection_essay": build_reflection_essay_prompt,
}


def get_prompts_for_event(event) -> Tuple[str, str]:
    """
    Dispatches to the correct format handler based on event.output_format.
    Falls back to a generic prompt if the format is unrecognised.
    """
    handler = FORMAT_HANDLERS.get(event.output_format)
    if handler:
        return handler(event)

    # Generic fallback
    system = (
        f"You are an expert instructor. Technical depth: {event.technical_depth}. "
        f"{_depth(event.technical_depth)}\n"
        "Write a clear, structured educational section (200-400 words) for the topic below. "
        "Return ONLY the content text."
    )
    user = (
        f"Title: {event.title}\n"
        f"Instruction: {event.instruction}\n"
        f"Example: {event.example}\n"
        f"Learning Objective: {event.learning_objective}\n"
        "Write the content now."
    )
    return system, user
