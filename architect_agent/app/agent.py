import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from architect_agent.app.prompts import (
    ARCHITECT_SYSTEM_PROMPT, 
    STEM_ADAPTATION, 
    CODE_ADAPTATION, 
    CONCEPT_ADAPTATION,
    REFINER_SYSTEM_PROMPT
)
from tavily import TavilyClient

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# Guard: only instantiate Tavily if the key is set
_tavily_key = os.getenv("TAVILY_API_KEY")
tavily = TavilyClient(api_key=_tavily_key) if _tavily_key else None


def fetch_technical_context(topic: str, is_code: bool = False) -> str:
    """
    Uses Tavily to fetch real-world, up-to-date technical context for the topic.
    Falls back to a structured grounding prompt if Tavily is unavailable.
    """
    if tavily:
        try:
            # 1. Tailor the query based on topic type
            if is_code:
                query = f"{topic} library python documentation StateGraph add_node State TypedDict code example"
            else:
                query = f"{topic} core concepts laws principles scientific overview"

            result = tavily.search(
                query=query,
                search_depth="advanced",  # Upgrade to advanced for technical accuracy
                max_results=5             # Increase results for better grounding
            )
            snippets = [r.get("content", "") for r in result.get("results", [])]
            combined = " ".join(snippets)[:1500]  # cap at 1500 chars
            if combined.strip():
                return (
                    f"Here is real-world reference material about '{topic}' from the web:\n\n"
                    f"{combined}\n\n"
                    f"Use this to ensure your blueprint covers the full breadth of the subject."
                )
        except Exception as e:
            print(f"[Tavily fallback] Search failed: {e}")

    # Fallback: structured grounding without search
    return (
        f"You are generating a blueprint for the topic: '{topic}'. "
        f"Your blueprint MUST cover ALL major sub-topics and foundational concepts of '{topic}', "
        f"not just a single subtopic. For example, if the topic is 'Thermodynamics', you must "
        f"reference the Zeroth, First, Second, and Third Laws across the 9 events."
    )


def clean_json_output(content: str) -> str:
    return re.sub(r"```json|```", "", content).strip()


def validate_blueprint(data: dict) -> bool:
    return (
        isinstance(data, dict)
        and "events" in data
        and len(data["events"]) == 9
    )


def normalize_output(data: dict, user_input: str) -> dict:
    """Ensure root-level fields are always present."""
    if isinstance(data, list):
        data = {"events": data}

    if isinstance(data, dict):
        # Inject course_title if missing
        if "course_title" not in data:
            data["course_title"] = user_input.strip().title()
        # Inject prerequisites if missing
        if "prerequisites" not in data:
            data["prerequisites"] = []
        # Inject assessment if missing
        if "assessment" not in data:
            data["assessment"] = ""

    return data



def refine_prompt(user_input: str) -> tuple[str, str]:
    """
    Expands a topic AND classifies it semantically.
    Returns (category, refined_text)
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": REFINER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Input: '{user_input}'"}
            ],
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        
        # Extract Category (e.g., [CATEGORY: CODE])
        cat_match = re.search(r"Category:\s*\[?(\w+)\]?", content, re.IGNORECASE)
        category = cat_match.group(1).lower() if cat_match else "concept"
        
        # Extract Expanded Request
        req_match = re.search(r"Expanded Request:\s*(.*)", content, re.DOTALL | re.IGNORECASE)
        refined = req_match.group(1).strip() if req_match else content
        
        print(f"[REFINER] Category: {category} | Refined: {refined[:100]}...")
        return category, refined
    except Exception as e:
        print(f"[REFINER ERROR] {e}")
        return "concept", user_input


def generate_blueprint(user_input: str):
    try:
        # 1. Semantic refinement and classification (The "De-Hardcoding" step)
        category, refined_input = refine_prompt(user_input)

        # 2. Domain Guard: Reject non-CS topics
        if category == "reject":
            return {
                "course_title": "Domain Limitation",
                "rejection_message": refined_input,
                "status": "rejected"
            }

        # 3. Select the right adaptation block based on semantic category
        if category == "code":
            adaptation = CODE_ADAPTATION
            topic_type_label = "PROGRAMMING/FRAMEWORK"
        elif category == "math":
            adaptation = STEM_ADAPTATION
            topic_type_label = "STEM/FORMULA-BASED"
        else:
            # For humanities, arts, or explicit 'no formula' requests
            adaptation = CONCEPT_ADAPTATION
            topic_type_label = "CONCEPTUAL/SOFT-SKILLS"

        # 3. Fetch dynamic technical context
        technical_context = fetch_technical_context(refined_input, is_code=(category == "code"))

        # 5. Compose the final system prompt: base + adaptation + grounding
        final_system_prompt = (
            f"{ARCHITECT_SYSTEM_PROMPT}"
            f"{adaptation}"
            f"\n\nTECHNICAL GROUNDING FOR THIS REQUEST:\n{technical_context}"
        )

        # 6. Call the Architect LLM with low temperature for strict adherence
        msg_suffix = ""
        if category == "code":
            msg_suffix = "This is a coding topic — Events 4-8 MUST include real, runnable code."
        elif category == "math":
            msg_suffix = "This is a STEM topic — Events 4-8 must use the core formula throughout."
        else:
            msg_suffix = "This is a conceptual topic — BANNED: Math formulas and code. Focus on CASE STUDIES."

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": final_system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Generate a complete Gagné's Nine Events blueprint for this request: '{refined_input}'.\n"
                        f"TOPIC TYPE: {topic_type_label}\n"
                        f"{msg_suffix}\n"
                        f"Return ONLY valid JSON with root fields: course_title, prerequisites, assessment, events."
                    )
                }
            ],
            temperature=0.1
        )

        content = response.choices[0].message.content
        print("[DEBUG] RAW OUTPUT:\n", content)

        cleaned = clean_json_output(content)
        parsed = json.loads(cleaned, strict=False)

        # 4. Normalize and validate
        normalized = normalize_output(parsed, user_input)

        if not validate_blueprint(normalized):
            return {
                "error": "Validation failed — model did not return 9 events",
                "data": normalized
            }

        return normalized

    except json.JSONDecodeError as e:
        return {"error": "Invalid JSON from model", "details": str(e)}
    except Exception as e:
        return {"error": "Groq API failure", "details": str(e)}