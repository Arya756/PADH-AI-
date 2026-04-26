# PADH AI — Adaptive Course Generator

> **An end-to-end, multi-agent AI pipeline that generates, evaluates, and self-improves educational course content — automatically.**

PADH AI is an AI-powered course generation system built around three cooperative LLM agents. Given a topic or raw learning material, the system:
1. **Architects** a structured, pedagogically-grounded course blueprint.
2. **Generates** rich, format-specific content for every learning event with real-world grounding.
3. **Simulates** a struggling student attempting the course and **rewrites** any confusing sections — automatically.

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [The Three Agents](#the-three-agents)
  - [1. Architect Agent](#1-architect-agent)
  - [2. Content Agent](#2-content-agent)
  - [3. Student Agent](#3-student-agent)
- [Full Pipeline Flow](#full-pipeline-flow)
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
│  (Blueprint Gen) │──────►  │  (Content Drafting)   │
└──────────────────┘          └──────────────────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │    Student Agent      │
                              │  (Eval & Refine)     │
                              └──────────────────────┘
                                         │
                              ┌──────────┴──────────┐
                              ▼                     ▼
                             Pass             Fail -> Refine
```

---

## The Three Agents

### 1. Architect Agent

**Location:** `architect_agent/`

The Architect Agent is the course designer. It takes a raw topic or description and produces a complete **course blueprint** structured around **Gagné's Nine Events of Instruction** — a research-backed pedagogical framework used in professional instructional design.

#### How it works

**Step 1 — Prompt Refinement & Classification**
The agent runs the input through a lightweight LLM acting as a "CS Instructional Gatekeeper". This step:
- **Rejects** non-CS topics (cooking, history, etc.) with a friendly message.
- **Classifies** valid CS topics into `CODE`, `MATH`, or `CONCEPT`.

**Step 2 — Web Grounding (via Tavily)**
The agent optionally queries the Tavily Search API to retrieve real-world, up-to-date documentation and examples. This grounds the blueprint in actual current practice.

**Step 3 — Blueprint Generation**
The final LLM call produces a **strict JSON blueprint** with 9 events. The agent specifically configures Event 3 (Quiz) to focus on **prerequisite fundamentals** needed for the topic, ensuring a proper knowledge baseline.

---

### 2. Content Agent

**Location:** `content_agent/`

The Content Agent takes the blueprint and generates **rich, format-specific educational content** for every event. It runs all 9 events in **parallel** for fast generation.

#### Features

- **Interactive Quizzes:** Generates MCQs with a specific syntax that is parsed into an interactive UI block where students can click options and receive immediate feedback.
- **Markdown Rendering:** All technical content is rendered with full markdown support, including code blocks, tables, and lists.
- **Tavily Enrichment:** Key formats (Lecture, Worked Example, Assessment) are enriched with live search context for maximum accuracy.

| Format | What it generates |
|--------|-------------------|
| `hook` | Vivid real-world scenario + provocative question. |
| `objectives_list` | 5–7 Bloom's taxonomy measurable outcomes. |
| `quiz` | 5 interactive MCQ diagnostic questions testing prerequisites. |
| `lecture_with_formula` | Structured lecture with concept overview and technical frameworks. |
| `worked_example` | Step-by-step case study with scenario and requirements. |
| `practice_problem` | Hands-on scenario with specific tasks and deliverables. |
| `feedback_rubric` | Ideal solution walkthrough + grading rubric table. |
| `assessment_task` | Complex multi-stakeholder case study for mastery check. |
| `reflection_essay` | Personal application prompts and reflection questions. |

---

### 3. Student Agent

**Location:** `student_agent/`

The Student Agent models the "weakest student" — modelled as a learner who is easily confused by jargon and needs concrete analogies.

#### The Evaluation Loop

1. **Attempt:** The student persona attempts to explain the concept in their own words.
2. **Score:** An Evaluator LLM scores the comprehension (0.0 to 1.0) and identifies specific concept gaps.
3. **Refine:** If the score is below the threshold, the Refiner LLM rewrites the original content to address those specific gaps (adding analogies, simplifying language, etc.).

---

## Full Pipeline Flow

1. **Blueprint Phase:** User input is processed into a 9-event pedagogical roadmap.
2. **Drafting Phase:** Content for all events is generated in parallel.
3. **Evaluation Phase:** The Student Agent loops through the content to find confusing sections.
4. **Refinement Phase:** Confusing sections are automatically rewritten and added to the final course.
5. **UI Rendering:** The entire journey is displayed in a premium vertical timeline.

---

## Project Structure

```
AI Hackathon/
│
├── architect_agent/              # Course Blueprint Generator
│   └── app/
│       ├── main.py               # FastAPI entry point
│       ├── agent.py              # Blueprint logic
│       └── prompts.py            # Pedagogical prompts
│
├── content_agent/                # Per-Event Content Generator
│   ├── agent.py                  # Parallel engine
│   ├── format_handlers.py        # Format prompt builders
│   └── validator.py              # Quality validation
│
├── student_agent/                # Student Persona + Refiner
│   ├── agent.py                  # Evaluation pipeline
│   └── prompts.py                # Student persona & tutor prompts
│
├── ui/
│   └── index.html                # Premium UI (Beige/Gold theme)
│
├── .env                          # API keys & Configuration
└── requirements.txt              # Dependencies
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI |
| **LLM Provider** | Groq (Llama 3.1 & 3.3) |
| **Web Search** | Tavily API |
| **Rendering** | Marked.js (Markdown) |
| **Export** | html2pdf.js (PDF Generation) |
| **Styling** | Vanilla CSS (Premium Dark/Light Beige) |

---

## Setup & Installation

1. **Clone & Navigate:**
   ```bash
   git clone https://github.com/Arya756/PADH-AI-.git
   cd PADH-AI-
   ```

2. **Environment Setup:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   Create a `.env` file with your `GROQ_API_KEY` and `TAVILY_API_KEY`.

---

## Running the Application

```bash
uvicorn architect_agent.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## UI Walkthrough

- **Interactive Timeline:** A beautiful vertical journey showing your progression through the course blueprint.
- **Premium Content Cards:** Collapsible, markdown-ready cards with format-specific icons and duration tracking.
- **Live Quiz Block:** Interactive MCQs that allow you to test yourself with immediate feedback.
- **Student Agent Logs:** A "Behind the Scenes" section to see the AI's internal evaluation of the course quality.
- **PDF Export:** A one-click button to download the entire course curriculum as a professionally formatted PDF.

---

## Pedagogical Foundation

PADH AI is built on **Gagné's Nine Events of Instruction**, ensuring every course follows a proven psychological flow:
1. Gain Attention
2. Inform Objectives
3. Stimulate Recall (Prerequisites)
4. Present Content
5. Provide Guidance
6. Elicit Performance
7. Provide Feedback
8. Assess Performance
9. Enhance Retention

---

*Built with passion for the AI Hackathon — redefining automated education.*
