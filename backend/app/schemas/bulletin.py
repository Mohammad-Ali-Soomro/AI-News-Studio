from pydantic import BaseModel, Field
from typing import List, Optional

class SourceArticle(BaseModel):
    title: str
    publisher: str  # e.g., "Dawn", "The Express Tribune", "Reuters"
    source_url: str
    published_at: Optional[str] = None
    summary: Optional[str] = None

class InsightFact(BaseModel):
    key: str        # e.g. "Headline", "Key Figure", "Location", "Date"
    value: str      # e.g. "$1.2 Billion", "Islamabad", "May 2025"

class StoryRundown(BaseModel):
    story_id: str
    category: str   # "National", "Economy", "World", "Technology"
    anchor: str     # "Anchor_A" or "Anchor_B"
    language: str   # "ur" or "en"
    
    # Broadcast scripts
    spoken_script: str
    headline: str
    ticker_text: str
    
    # Media and presentation assets
    source: SourceArticle
    insight_panel: List[InsightFact]
    image_url: Optional[str] = None
    
    # Timing contract (Generated after TTS/video synthesis)
    start_time_sec: float = 0.0
    duration_sec: float = 0.0
    audio_url: Optional[str] = None
    video_url: Optional[str] = None

class Bulletin(BaseModel):
    bulletin_id: str
    title: str
    generated_at: str
    language: str   # "ur" or "en"
    total_duration_sec: float = 0.0
    stories: List[StoryRundown] = Field(default_factory=list)
