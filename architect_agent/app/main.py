import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from architect_agent.app.agent import generate_blueprint
from content_agent.main import router as content_router
from student_agent.main import router as student_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)

app = FastAPI(
    title="AI Course Generator",
    description="Architecture Agent + Content Agent pipeline",
    version="1.0.0",
)

# ── CORS — allow the UI (any origin during dev) to call the API ────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Content Agent routes ───────────────────────────────────────────────────
app.include_router(content_router)

# ── Student Agent routes ────────────────────────────────────────────────────
app.include_router(student_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logging.getLogger("uvicorn").error(f"Validation error: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


class InputData(BaseModel):
    content: str


from fastapi import HTTPException

@app.post("/generate-blueprint")
def create_blueprint(data: InputData):
    result = generate_blueprint(data.content)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=500, detail=result)
    return {"blueprint": result}


from content_agent.schemas import Blueprint
from architect_agent.app.orchestrator import run_end_to_end_pipeline

@app.post("/generate-end-to-end")
def generate_end_to_end(blueprint: Blueprint):
    try:
        result = run_end_to_end_pipeline(blueprint)
        return result
    except Exception as exc:
        logging.exception("End-to-End Pipeline failed.")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Serve the UI ───────────────────────────────────────────────────────────
_UI_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ui")
_UI_DIR = os.path.abspath(_UI_DIR)

if os.path.isdir(_UI_DIR):
    app.mount("/ui", StaticFiles(directory=_UI_DIR, html=True), name="ui")

    @app.get("/")
    def serve_ui():
        return FileResponse(os.path.join(_UI_DIR, "index.html"))