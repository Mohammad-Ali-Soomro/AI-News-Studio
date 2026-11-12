from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

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

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "AI News Studio API",
        "team": ["Muhammad Ali", "Hassan Khalid", "Sajeel Malik"],
        "institution": "GIK Institute"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
