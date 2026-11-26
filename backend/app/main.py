import os
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import get_settings
from backend.app.jobs.run_pipeline import run_pipeline
from backend.app.schemas.bulletin import Bulletin
from backend.app.services.supabase_client import (
    get_latest_ready_bulletin,
    list_recent_runs,
    start_run,
)

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Automated Urdu AI Anchor News Presentation Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

media_dir = os.path.abspath(settings.MEDIA_STORAGE_DIR)
os.makedirs(media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_dir), name="media")


def _run_pipeline_background(stories: int, run_id: str) -> None:
    try:
        run_pipeline(stories=stories, dry_run=False, existing_run_id=run_id)
    except Exception:
        # Failure status and error details are recorded in pipeline_runs by run_pipeline.
        pass


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "institution": "GIK Institute",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/v1/bulletin/latest", response_model=Bulletin)
def get_latest_bulletin(
    language: str = Query(default="ur", pattern="^(ur|en)$")
):
    """Return the latest ready broadcast bulletin from Supabase (or local JSON)."""
    bulletin = get_latest_ready_bulletin(language=language)
    if bulletin is None:
        raise HTTPException(
            status_code=404,
            detail="No ready bulletin available. Trigger the pipeline first.",
        )
    return bulletin


@app.post("/api/v1/pipeline/run")
def trigger_pipeline_run(
    background_tasks: BackgroundTasks,
    stories: int = Query(default=4, ge=1, le=5),
):
    """Trigger the end-to-end bulletin pipeline in a background task and return its run_id."""
    run_id = start_run()
    background_tasks.add_task(_run_pipeline_background, stories, run_id)
    return {"run_id": run_id, "status": "running"}


@app.get("/api/v1/pipeline/runs")
def get_pipeline_runs(limit: int = Query(default=10, ge=1, le=50)):
    """List recent pipeline runs ordered newest first."""
    runs = list_recent_runs(limit=limit)
    return {"runs": runs, "count": len(runs)}
