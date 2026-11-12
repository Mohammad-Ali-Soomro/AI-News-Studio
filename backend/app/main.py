from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from typing import Optional

from backend.app.schemas.bulletin import Bulletin
from backend.app.pipeline.collector import fetch_rss_articles
from backend.app.pipeline.deduplicator import cluster_and_deduplicate
from backend.app.pipeline.script_generator import generate_bulletin_with_gemini

app = FastAPI(
    title="AI News Studio API",
    description="Automated Bilingual AI Anchor News Presentation Engine",
    version="1.0.0"
)

# CORS configuration for Frontend Studio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated media (audio clips, avatar videos, images)
media_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "media")
os.makedirs(media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_dir), name="media")

# In-memory bulletin cache (can be persisted to SQLite)
LATEST_BULLETINS = {}

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "AI News Studio API",
        "team": ["Muhammad Ali", "Hassan Khalid", "Sajeel Malik"],
        "institution": "GIK Institute",
        "active_module": "Pipeline, Deduplication & Script Engine (Muhammad Ali)"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/v1/news/latest-raw")
def get_raw_news(limit: int = Query(default=3, ge=1, le=10)):
    """
    Fetches raw articles from Dawn and Tribune RSS feeds.
    Used by the Producer Dashboard to view incoming news streams.
    """
    articles = fetch_rss_articles(limit_per_feed=limit, fetch_full_body=False)
    return {
        "total_articles": len(articles),
        "articles": articles
    }

@app.get("/api/v1/news/clusters")
def get_clustered_news(similarity_threshold: float = Query(default=0.35, ge=0.1, le=0.9)):
    """
    Runs the TF-IDF and Cosine Similarity deduplication engine on incoming news.
    Visualized in the MCR Dashboard to demonstrate algorithmic depth.
    """
    articles = fetch_rss_articles(limit_per_feed=3, fetch_full_body=False)
    clusters = cluster_and_deduplicate(articles, similarity_threshold=similarity_threshold)
    return {
        "raw_article_count": len(articles),
        "story_cluster_count": len(clusters),
        "clusters": clusters
    }

@app.post("/api/v1/bulletin/generate", response_model=Bulletin)
def generate_broadcast_bulletin(language: str = Query(default="ur", regex="^(ur|en)$")):
    """
    Orchestrates the pipeline:
    1. Ingests raw news from authentic feeds
    2. Clusters and deduplicates stories
    3. Runs LLM Script Engine to produce broadcast dialogue, insight panel facts, and ticker lines
    """
    try:
        articles = fetch_rss_articles(limit_per_feed=2, fetch_full_body=True)
        clusters = cluster_and_deduplicate(articles)
        bulletin = generate_bulletin_with_gemini(clusters, language=language)
        
        # Cache as latest
        LATEST_BULLETINS[language] = bulletin
        return bulletin
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline generation failed: {str(e)}")

@app.get("/api/v1/bulletin/latest", response_model=Bulletin)
def get_latest_bulletin(language: str = Query(default="ur", regex="^(ur|en)$")):
    """
    Returns the latest broadcast bulletin for Sajeel's Web Studio Player.
    """
    if language in LATEST_BULLETINS:
        return LATEST_BULLETINS[language]
    
    # If not yet generated in memory, generate on the fly
    return generate_broadcast_bulletin(language=language)
