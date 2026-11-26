import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import get_settings
from backend.app.pipeline.collector import fetch_rss_articles
from backend.app.pipeline.deduplicator import cluster_and_deduplicate
from backend.app.pipeline.script_generator import generate_bulletin_with_gemini
from backend.app.schemas.bulletin import Bulletin

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Automated AI Anchor News Presentation Engine",
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

LATEST_BULLETINS = {}


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "team": ["Muhammad Ali", "Hassan Khalid", "Sajeel Malik"],
        "institution": "GIK Institute",
        "active_module": "Pipeline, Deduplication & Script Engine (Muhammad Ali)",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/v1/news/latest-raw")
def get_raw_news(limit: int = Query(default=3, ge=1, le=10)):
    """Fetch raw articles from Dawn and Express Tribune RSS feeds."""
    articles = fetch_rss_articles(limit_per_feed=limit, fetch_full_body=False)
    return {
        "total_articles": len(articles),
        "articles": articles,
    }


@app.get("/api/v1/news/clusters")
def get_clustered_news(
    similarity_threshold: float = Query(default=0.35, ge=0.1, le=0.9)
):
    """Run TF-IDF and cosine similarity deduplication on incoming news."""
    articles = fetch_rss_articles(limit_per_feed=3, fetch_full_body=False)
    clusters = cluster_and_deduplicate(
        articles, similarity_threshold=similarity_threshold
    )
    return {
        "raw_article_count": len(articles),
        "story_cluster_count": len(clusters),
        "clusters": clusters,
    }


@app.post("/api/v1/bulletin/generate", response_model=Bulletin)
def generate_broadcast_bulletin(
    language: str = Query(default="ur", pattern="^(ur|en)$")
):
    """Orchestrate collection, deduplication, and script generation."""
    try:
        articles = fetch_rss_articles(limit_per_feed=2, fetch_full_body=True)
        clusters = cluster_and_deduplicate(articles)
        bulletin = generate_bulletin_with_gemini(clusters, language=language)
        LATEST_BULLETINS[language] = bulletin
        return bulletin
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Pipeline generation failed: {exc}"
        ) from exc


@app.get("/api/v1/bulletin/latest", response_model=Bulletin)
def get_latest_bulletin(
    language: str = Query(default="ur", pattern="^(ur|en)$")
):
    """Return the latest cached broadcast bulletin or generate one."""
    if language in LATEST_BULLETINS:
        return LATEST_BULLETINS[language]
    return generate_broadcast_bulletin(language=language)
