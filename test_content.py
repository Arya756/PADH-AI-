import asyncio
from architect_agent.app.agent import generate_blueprint
from content_agent.agent import generate_content
import json

blueprint = generate_blueprint("nlp")
print("BLUEPRINT:", json.dumps(blueprint, indent=2))
if "error" not in blueprint:
    class BlueprintMock:
        def __init__(self, d):
            self.course_title = d.get("course_title", "NLP")
            self.prerequisites = d.get("prerequisites", [])
            self.assessment = d.get("assessment", "")
            
            class EventMock:
                pass
            self.events = []
            for ev in d.get("events", []):
                e = EventMock()
                e.event_id = ev.get("event_id")
                e.title = ev.get("title")
                e.instruction = ev.get("instruction")
                e.example = ev.get("example")
                e.technical_depth = ev.get("technical_depth")
                e.learning_objective = ev.get("learning_objective")
                e.output_format = ev.get("output_format")
                e.estimated_duration = ev.get("estimated_duration")
                self.events.append(e)

    mock_bp = BlueprintMock(blueprint)
    content = generate_content(mock_bp)
    for c in content["content"]:
        if "encountered an error" in c["content"]:
            print(f"FAILED Event {c['event_id']}")
        else:
            print(f"SUCCESS Event {c['event_id']}")
