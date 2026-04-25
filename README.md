# 🎓 PADH AI — Adaptive Course Generator

> **An end-to-end, multi-agent AI pipeline that generates, evaluates, and self-improves educational course content — automatically.**

PADH AI is an AI-powered course generation system built around three cooperative LLM agents. Given a topic or raw learning material, the system:
1. **Architects** a structured, pedagogically-grounded course blueprint
2. **Generates** rich, format-specific content for every learning event
3. **Simulates** a struggling student attempting the course and **rewrites** any confusing sections — automatically

---

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [The Three Agents](#the-three-agents)
  - [1. Architect Agent](#1-architect-agent)
  - [2. Content Agent](#2-content-agent)
  - [3. Student Agent](#3-student-agent)
- [Full Pipeline Flow](#full-pipeline-flow)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [UI Walkthrough](#ui-walkthrough)
- [Pedagogical Foundation](#pedagogical-foundation)

---

## Overview

Most AI course generators produce generic content. PADH AI is different: it uses a **self-improving feedback loop** where a simulated "weakest student" actively attempts the generated exercises. Any content that the simulated student fails to understand is automatically flagged, its concept gaps are identified, and the Content Agent rewrites it — all in a single pipeline run.

This means every course produced by PADH AI has been stress-tested against a struggling learner before it ever reaches a real student.

---

## System Architecture

```
User Input (Topic / Raw Content)
          │
          ▼
┌─────────────────────────┐
│    FastAPI Backend       │   (architect_agent/app/main.py)
│  + CORS Middleware       │
│  + Static UI Server      │
└─────────────────────────┘
          │
    ┌─────┴──────────────────────────────┐
    │                                    │
    ▼                                    ▼
┌──────────────────┐          ┌──────────────────────┐
│  Architect Agent │          │    Content Agent      │
│  POST /generate- │──────►  │  POST /generate-      │
│     blueprint    │          │      content          │
└──────────────────┘          └──────────────────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │    Student Agent      │
                              │  POST /evaluate-and-  │
                              │       refine          │
                              └──────────────────────┘
                                         │
                              ┌──────────┴──────────┐
                              ▼                     ▼
                         Pass ✅            Fail ⚠️ → Refine ✨
```

---

## The Three Agents

### 1. Architect Agent

**Location:** `architect_agent/`

The Architect Agent is the course designer. It takes a raw topic or description and produces a complete **course blueprint** structured around **Gagné's Nine Events of Instruction** — a research-backed pedagogical framework used in professional instructional design.

#### How it works

**Step 1 — Prompt Refinement & Classification**
Before generating any blueprint, the agent runs the input through a lightweight LLM (`llama-3.1-8b-instant`) acting as a "CS Instructional Gatekeeper". This step:
- **Rejects** non-CS topics (cooking, history, etc.) with a friendly message
- **Classifies** valid CS topics into one of three categories:
  - `CODE` — programming languages, frameworks, libraries
  - `MATH` — algorithms, complexity, formal methods
  - `CONCEPT` — architecture, methodologies, soft skills

**Step 2 — Web Grounding (via Tavily)**
The agent optionally queries the Tavily Search API to retrieve real-world, up-to-date documentation and examples for the topic. This grounds the blueprint in actual current practice rather than the LLM's training data alone.

**Step 3 — Blueprint Generation**
A domain-specific system prompt is assembled by combining:
- The base `ARCHITECT_SYSTEM_PROMPT` (strict nine-event rules)
- A topic-type **adaptation block** (`STEM_ADAPTATION`, `CODE_ADAPTATION`, or `CONCEPT_ADAPTATION`)
- The fetched web context

The final LLM call (`llama-3.1-8b-instant`, `temperature=0.1`) produces a **strict JSON blueprint** with 9 events. The low temperature enforces deterministic, rule-following output.

#### Gagné's Nine Events mapping

| Event | Name | Output Format | Duration |
|-------|------|---------------|----------|
| 1 | Gain Attention | `hook` | 5 min |
| 2 | Inform Learners of Objectives | `objectives_list` | 5 min |
| 3 | Stimulate Recall of Prior Learning | `quiz` | 10 min |
| 4 | Present the Content | `lecture_with_formula` | 20 min |
| 5 | Provide Learning Guidance | `worked_example` | 15 min |
| 6 | Elicit Performance | `practice_problem` | 15 min |
| 7 | Provide Feedback | `feedback_rubric` | 10 min |
| 8 | Assess Performance | `assessment_task` | 30 min |
| 9 | Enhance Retention & Transfer | `reflection_essay` | 20 min |

Each event in the blueprint contains: `event_id`, `title`, `instruction`, `example`, `technical_depth` (Basic/Intermediate/Advanced), `learning_objective`, `output_format`, and `estimated_duration`.

---

### 2. Content Agent

**Location:** `content_agent/`

The Content Agent takes the blueprint and generates **rich, format-specific educational content** for every event. It runs all 9 events in **parallel** (up to 4 concurrent workers) for fast generation.

#### Generation pipeline per event

```
Event Blueprint
      │
      ├─► (Optional) Tavily Web Search  ← grounding context
      │
      ├─► Format-Specific Prompt Builder
      │         (format_handlers.py)
      │
      ├─► Primary LLM Call  (temperature=0.4)
      │         groq: llama-3.3-70b-versatile
      │
      ├─► Content Validator
      │         (validator.py)
      │
      ├─► Retry if invalid  (temperature=0.7)
      │
      └─► Graceful Fallback if all else fails
```

#### Format handlers

Each of the 9 output formats has a dedicated prompt builder in `format_handlers.py`:

| Format | What it generates |
|--------|-------------------|
| `hook` | Vivid real-world scenario + provocative question (200–300 words) |
| `objectives_list` | 5–7 Bloom's taxonomy measurable outcomes |
| `quiz` | 5 multiple-choice diagnostic questions with answers |
| `lecture_with_formula` | Structured lecture with concept overview, components, formula/framework |
| `worked_example` | Step-by-step case study with scenario, requirements, and expected outcome |
| `practice_problem` | New scenario with tasks, constraints, deliverables, and optional hints |
| `feedback_rubric` | Ideal solution walkthrough + grading rubric table + common pitfalls |
| `assessment_task` | Complex multi-stakeholder case study with evaluation criteria |
| `reflection_essay` | Personal application prompts with reflection questions and example opener |

#### Web-enriched formats
The following formats receive Tavily search context to ensure real-world accuracy:
`hook`, `lecture_with_formula`, `worked_example`, `practice_problem`, `assessment_task`

---

### 3. Student Agent

**Location:** `student_agent/`

The Student Agent is the most novel component. It simulates **ALEX** — a persona modelling the weakest student in the class: easily confused by jargon, prone to misreading instructions, and needing everything anchored in concrete examples.

#### The three-stage loop

```
For each event (parallel, 3 workers):

Stage 1 — STUDENT ATTEMPT
  llama-3.1-8b-instant @ temperature=0.75
  Persona: Confused, earnest, conversational
  Output: Student answer + "What I understood" + "What confused me"
        + confidence level
        
Stage 2 — EVALUATOR SCORING
  llama-3.3-70b-versatile @ temperature=0.1
  Scores comprehension 0.0 → 1.0
  Identifies specific concept gaps with:
    - concept name
    - reason for confusion
    - verbatim excerpt from the student's answer
  Writes tutor feedback
  
Stage 3 — CONTENT REFINEMENT (only if score < 0.6)
  llama-3.3-70b-versatile @ temperature=0.3
  Rewrites the event content addressing each gap directly:
    - Replaces jargon with plain English
    - Adds concrete everyday analogies
    - Breaks steps into smaller sub-steps
    - Adds "PLAIN ENGLISH SUMMARY" box
    - Adds "COMMON CONFUSION" callouts for each identified gap
```

#### Scoring thresholds

| Score | Meaning | Action |
|-------|---------|--------|
| 0.0 – 0.59 | Student failed to understand | Content rewritten |
| 0.6 – 0.79 | Adequate but gaps remain | Passed (minor notes) |
| 0.8 – 1.0 | Strong understanding | Passed, no action |

**Course-level pass threshold:** If fewer than 70% of events pass, the course is flagged as needing refinement. Refined events are returned alongside the originals for comparison.

---

## Full Pipeline Flow

```
User types topic
       │
       ▼
POST /generate-blueprint
  ├── Refine & classify prompt
  ├── Fetch web context (Tavily)
  ├── Generate 9-event JSON blueprint
  └── Validate (must have exactly 9 events)
       │
       ▼
POST /generate-content
  ├── Validate blueprint fields
  ├── For each event (parallel, 4 workers):
  │     ├── Web search enrichment (selected formats)
  │     ├── Format-specific prompt → LLM
  │     ├── Validate output
  │     └── Retry / fallback if needed
  └── Sort & return all 9 event contents
       │
       ▼
POST /evaluate-and-refine
  ├── For each event (parallel, 3 workers):
  │     ├── Student LLM attempts exercise
  │     ├── Evaluator LLM scores attempt + identifies gaps
  │     └── If failed → Refiner LLM rewrites content targeting gaps
  ├── Build failure log (pass rate, concept gaps, summary)
  └── Return: attempts + failure log + refined events
       │
       ▼
UI renders:
  ├── Course Blueprint (9 event chips)
  ├── Generated Content (collapsible cards)
  ├── Student Evaluation (score badges + gap analysis)
  └── ✨ Refined Content (only if refinement triggered)
```

---

## API Reference

All endpoints are served at `http://127.0.0.1:8000`.

### `POST /generate-blueprint`

Generates a 9-event course blueprint from raw input text.

**Request body:**
```json
{
  "content": "I want to build a course on LangChain for intermediate Python developers."
}
```

**Response:**
```json
{
  "blueprint": {
    "course_title": "Building Conversational AI with LangChain",
    "prerequisites": ["Python fundamentals", "Basic AI/ML concepts"],
    "assessment": "Build a multi-turn chatbot with memory and tools.",
    "events": [
      {
        "event_id": 1,
        "title": "The Chatbot That Forgot Everything",
        "instruction": "...",
        "example": "...",
        "technical_depth": "Intermediate",
        "learning_objective": "The learner will be able to...",
        "output_format": "hook",
        "estimated_duration": "5 minutes"
      }
      // ... 8 more events
    ]
  }
}
```

---

### `POST /generate-content`

Generates full content for each event in the blueprint.

**Request body:**
```json
{
  "blueprint": { ... }  // Full blueprint object from /generate-blueprint
}
```

**Response:**
```json
{
  "course_title": "Building Conversational AI with LangChain",
  "prerequisites": [...],
  "assessment": "...",
  "content": [
    {
      "event_id": 1,
      "title": "The Chatbot That Forgot Everything",
      "output_format": "hook",
      "estimated_duration": "5 minutes",
      "learning_objective": "...",
      "content": "Imagine you build a customer support chatbot...",
      "validation_warning": null
    }
    // ... 8 more events
  ]
}
```

---

### `POST /evaluate-and-refine`

Runs the Student Agent against the generated course content.

**Request body:**
```json
{
  "course_content": { ... }  // Full response from /generate-content
}
```

**Response:**
```json
{
  "course_title": "...",
  "failure_log": {
    "total_events": 9,
    "passed_events": 6,
    "failed_events": 3,
    "pass_rate": 0.667,
    "overall_passed": false,
    "failed_attempts": [...],
    "summary": "The student struggled most with: memory management, prompt chaining..."
  },
  "attempts": [
    {
      "event_id": 1,
      "title": "...",
      "output_format": "hook",
      "passed": true,
      "comprehension_score": 0.82,
      "student_answer": "I think this course is about...",
      "concept_gaps": [],
      "feedback": "Great job identifying the core problem!"
    }
    // ... 8 more
  ],
  "refined_events": [
    {
      "event_id": 4,
      "title": "...",
      "content": "...rewritten, clearer version...",
      "original_content": "...original...",
      "refinement_notes": "Rewritten to address 2 concept gaps: memory management, state persistence."
    }
  ],
  "final_pass_rate": 0.667,
  "message": "⚠️ Course failed the student test. 3 event(s) have been automatically rewritten."
}
```

---

## Project Structure

```
AI Hackathon/
│
├── architect_agent/              # Course Blueprint Generator
│   ├── __init__.py
│   └── app/
│       ├── main.py               # FastAPI app entry point + all routers
│       ├── agent.py              # Blueprint generation logic
│       ├── prompts.py            # System prompts (base + 3 adaptation blocks + refiner)
│       ├── schema.py             # Pydantic models: Event, Blueprint
│       └── utils.py
│
├── content_agent/                # Per-Event Content Generator
│   ├── __init__.py
│   ├── agent.py                  # Parallel content generation engine
│   ├── config.py                 # Env var loading
│   ├── format_handlers.py        # 9 format-specific prompt builders
│   ├── main.py                   # FastAPI router: POST /generate-content
│   ├── prompt_builder.py
│   ├── schemas.py                # Pydantic models: ContentRequest, ContentResponse
│   └── validator.py              # Output quality validation
│
├── student_agent/                # Simulated Student + Refinement Engine
│   ├── __init__.py
│   ├── agent.py                  # 3-stage pipeline: attempt → evaluate → refine
│   ├── main.py                   # FastAPI router: POST /evaluate-and-refine
│   ├── prompts.py                # Student persona, evaluator, refiner prompts
│   └── schemas.py                # Pydantic models: EvaluationRequest/Response, FailureLog, etc.
│
├── ui/
│   └── index.html                # Single-file frontend (HTML + CSS + JS)
│
├── .gitignore                    # Excludes .env, __pycache__, etc.
├── README.md
└── requirements.txt
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) |
| **LLM Provider** | [Groq](https://groq.com/) — ultra-fast inference |
| **Primary LLM** | `llama-3.3-70b-versatile` (content + evaluation) |
| **Fast LLM** | `llama-3.1-8b-instant` (student persona + blueprint classification) |
| **Web Search** | [Tavily](https://tavily.com/) (optional grounding) |
| **Data Validation** | [Pydantic v2](https://docs.pydantic.dev/) |
| **Frontend** | Vanilla HTML + CSS + JavaScript (no framework) |
| **Concurrency** | Python `ThreadPoolExecutor` (parallel event generation) |

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- A [Groq API key](https://console.groq.com/) (free tier available)
- A [Tavily API key](https://tavily.com/) (optional, enables web grounding)

### 1. Clone the repository

```bash
git clone https://github.com/Arya756/PADH-AI-.git
cd PADH-AI-
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate          # Windows
```

### 3. Install dependencies

```bash
pip install fastapi uvicorn groq openai tavily-python pydantic python-dotenv sentence-transformers faiss-cpu httpx
```

Or if a `requirements.txt` with all dependencies is present:

```bash
pip install -r requirements.txt
pip install fastapi uvicorn groq python-dotenv
```

### 4. Create the `.env` file

Create a file named `.env` in the project root (**never commit this file**):

```env
GROQ_API_KEY=your_groq_api_key_here
MODEL_NAME=llama-3.3-70b-versatile
TAVILY_API_KEY=your_tavily_api_key_here   # optional

# Optional overrides for Student Agent
STUDENT_MODEL=llama-3.1-8b-instant
EVALUATOR_MODEL=llama-3.3-70b-versatile
REFINER_MODEL=llama-3.3-70b-versatile
STUDENT_PASS_THRESHOLD=0.6
STUDENT_COURSE_PASS_THRESHOLD=0.7
STUDENT_MAX_WORKERS=3
```

---

## Configuration

All configuration is driven by environment variables (loaded from `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | *(required)* | Groq API key for all LLM calls |
| `MODEL_NAME` | `llama-3.3-70b-versatile` | Primary LLM for content and evaluation |
| `TAVILY_API_KEY` | *(optional)* | Enables real-world web grounding |
| `STUDENT_MODEL` | `llama-3.1-8b-instant` | LLM for the student persona |
| `EVALUATOR_MODEL` | same as `MODEL_NAME` | LLM for scoring student attempts |
| `REFINER_MODEL` | same as `MODEL_NAME` | LLM for rewriting failing content |
| `STUDENT_PASS_THRESHOLD` | `0.6` | Minimum comprehension score to pass an event |
| `STUDENT_COURSE_PASS_THRESHOLD` | `0.7` | Minimum event pass-rate to pass the course |
| `STUDENT_MAX_WORKERS` | `3` | Parallel workers for student evaluation |

---

## Running the Application

```bash
uvicorn architect_agent.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open your browser at: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

The interactive API documentation (Swagger UI) is available at: **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

## UI Walkthrough

The frontend is a single-page application (`ui/index.html`) with a dark-mode premium design.

**Pipeline Status Bar** — A 4-step progress tracker at the top shows real-time status for each agent:
- 📝 Architecture Agent
- 🔨 Content Agent
- 📚 Course Ready
- 🎓 Student Agent

**Course Blueprint** — Once the Architect Agent completes, the blueprint appears as a grid of event chips, each showing the event title, format type (color-coded pill), and estimated duration.

**Generated Course Content** — Collapsible cards for all 9 events, each showing the format icon, duration, and the full generated content. The first card auto-expands.

**Student Agent Evaluation** — After evaluation completes:
- Summary stats: events passed, events failed, overall pass rate
- A plain-language summary of what the student struggled with most
- Collapsible per-event attempt cards showing:
  - 🟢/🔴 Score badge (percentage)
  - Student's raw answer
  - Tutor feedback
  - Identified concept gaps with supporting quotes from the student's answer

**✨ Refined Content** — Only appears when events were rewritten. Shows the improved content alongside refinement notes explaining what was changed and why.

---

## Pedagogical Foundation

PADH AI is built on **Gagné's Nine Events of Instruction** (Robert M. Gagné, 1965/1985), a systematic instructional design model widely used in educational psychology and corporate training.

The model ensures every course naturally progresses through:

1. **Attention** → Motivation to engage
2. **Objectives** → Clear expectations
3. **Prior Knowledge** → Connecting new to known
4. **Content Presentation** → Core concept delivery
5. **Guided Practice** → Scaffolded application
6. **Performance** → Independent practice
7. **Feedback** → Error correction and reinforcement
8. **Assessment** → Mastery verification
9. **Retention & Transfer** → Real-world application

The Student Agent's feedback loop takes this a step further by empirically testing whether the content actually achieves its pedagogical goals for the **hardest-to-reach learner** — not just the average one.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## License

This project was built for an AI Hackathon. Feel free to use and adapt it.

---

*Built with ❤️ using Groq, FastAPI, and Gagné's Nine Events of Instruction.*
