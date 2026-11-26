import datetime
import json
from typing import Dict, List

from backend.app.core.config import get_settings
from backend.app.schemas.bulletin import Bulletin, InsightFact, SourceArticle, StoryRundown


def build_broadcast_prompt(clusters: List[Dict], language: str = "ur") -> str:
    """
    Construct an expert broadcast journalism prompt for the LLM.
    Instructs the model to generate a television news rundown with
    insight facts and live ticker lines.
    """
    stories_context = []
    for i, c in enumerate(clusters, 1):
        stories_context.append(
            f"Story #{i}:\n"
            f"- Title: {c['title']}\n"
            f"- Publishers: {', '.join(c.get('publishers', []))}\n"
            f"- URL: {c.get('primary_source_url', '')}\n"
            f"- Details: {c.get('aggregated_body', '')[:800]}\n"
        )

    combined_stories = "\n".join(stories_context)

    if language == "ur":
        instructions = """
You are the Executive Producer for 'AI News Studio', a premier Pakistani television news channel.
Your task is to transform the provided raw stories into a professional Urdu broadcast bulletin.

RULES:
1. Spoken Script (Urdu):
   - Anchor_A presents the broadcast in formal, dignified Urdu as heard on Pakistan television.
   - Keep each story's spoken script between 35 and 60 words (concise, clear, easy to vocalize).
   - Never invent facts, numbers, or unverified claims.
2. Insight Panel (Urdu):
   - Extract exactly 3 key-value facts per story.
3. Ticker Text (Urdu):
   - An eye-catching 10 to 15 word scrolling ticker headline.
"""
    else:
        instructions = """
You are the Executive Producer for 'AI News Studio', a premier international television news network.
Your task is to transform the provided raw stories into a professional English broadcast bulletin.

RULES:
1. Spoken Script (English):
   - Clear, objective, authoritative broadcast journalism.
   - Keep each story's spoken script between 40 and 65 words.
   - Never invent facts or numbers.
2. Insight Panel:
   - Extract exactly 3 key-value facts per story (Key Figure, Date, Location, Source).
3. Ticker Text:
   - A concise 10 to 15 word scrolling ticker.
"""

    return f"""{instructions}

RAW INGESTED STORIES:
{combined_stories}

Return your response strictly as a JSON object adhering to this schema:
{{
  "bulletin_id": "bulletin-{datetime.date.today().isoformat()}-001",
  "title": "Evening News Broadcast",
  "language": "{language}",
  "stories": [
    {{
      "story_id": "story_1",
      "category": "National",
      "anchor": "Anchor_A",
      "language": "{language}",
      "spoken_script": "Full anchor spoken dialogue...",
      "headline": "Brief Headline...",
      "ticker_text": "Live ticker line...",
      "source": {{
        "title": "Original headline",
        "publisher": "Dawn",
        "source_url": "https://..."
      }},
      "insight_panel": [
        {{"key": "Key Metric", "value": "Value"}},
        {{"key": "Location", "value": "Value"}},
        {{"key": "Source", "value": "Dawn"}}
      ]
    }}
  ]
}}
"""


def generate_bulletin_with_gemini(clusters: List[Dict], language: str = "ur") -> Bulletin:
    """
    Generate a broadcast-ready bulletin using the Google Gemini API.
    For Urdu ("ur"), raises a clear error if Gemini is unconfigured or fails
    rather than mixing English text into an Urdu script.
    For English ("en"), falls back to the English template synthesizer.
    """
    if not clusters:
        raise ValueError("No story clusters provided for bulletin generation.")

    settings = get_settings()
    api_key = settings.GEMINI_API_KEY.strip()
    model_name = settings.GEMINI_MODEL.strip()

    has_valid_key = bool(api_key and api_key != "your_gemini_api_key_here")
    if has_valid_key:
        if not model_name:
            raise ValueError(
                "GEMINI_MODEL is not configured. Set GEMINI_MODEL in backend/.env."
            )

        prompt = build_broadcast_prompt(clusters, language=language)
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            raw_json = json.loads(response.text)
            return Bulletin(
                bulletin_id=raw_json.get(
                    "bulletin_id",
                    f"bulletin-{datetime.datetime.now().strftime('%Y%m%d%H%M')}",
                ),
                title=raw_json.get("title", "AI News Studio Bulletin"),
                generated_at=datetime.datetime.now().isoformat(),
                language=language,
                total_duration_sec=0.0,
                stories=[StoryRundown(**s) for s in raw_json.get("stories", [])],
            )
        except Exception as exc:
            if language == "ur":
                raise RuntimeError(
                    f"Gemini Urdu script generation failed for model '{model_name}': {exc}"
                ) from exc
            print(
                f"[Gemini Generator Warning] Error calling Gemini API: {exc}. "
                "Falling back to English template synthesizer."
            )
    elif language == "ur":
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Urdu bulletins cannot fall back to "
            "an English template; set GEMINI_API_KEY and GEMINI_MODEL in backend/.env."
        )

    return generate_fallback_bulletin(clusters, language="en")


def generate_fallback_bulletin(clusters: List[Dict], language: str = "en") -> Bulletin:
    """
    Deterministic English-only template synthesizer for offline English testing.
    Never produces mixed English-inside-Urdu scripts.
    """
    if language != "en":
        raise ValueError(
            "Template fallback is only supported for language='en'. "
            "Urdu bulletins require Gemini or a saved Urdu sample bulletin."
        )

    stories: List[StoryRundown] = []
    for idx, cluster in enumerate(clusters[:4]):
        story_id = f"story_{idx + 1}"
        publisher_name = cluster.get("publishers", ["Dawn"])[0]
        intro = (
            "Good evening and welcome to AI News Studio. "
            if idx == 0
            else "In other major developments, "
        )
        spoken_script = (
            f"{intro}According to confirmed reports, {cluster['title']}. "
            "Authorities and representatives are monitoring the situation closely."
        )
        headline = cluster["title"][:60]
        ticker = f"BREAKING: {cluster['title'][:70]} | Source: {publisher_name}"
        insight = [
            InsightFact(key="Headline", value=cluster["title"][:40]),
            InsightFact(key="Category", value="National Affairs"),
            InsightFact(key="Verified Source", value=publisher_name),
        ]

        stories.append(
            StoryRundown(
                story_id=story_id,
                category="National",
                anchor="Anchor_A",
                language="en",
                spoken_script=spoken_script,
                headline=headline,
                ticker_text=ticker,
                source=SourceArticle(
                    title=cluster["title"],
                    publisher=publisher_name,
                    source_url=cluster.get("primary_source_url", ""),
                ),
                insight_panel=insight,
            )
        )

    return Bulletin(
        bulletin_id=f"bulletin-{datetime.datetime.now().strftime('%Y%m%d-%H%M')}",
        title="AI News Studio Broadcast Bulletin",
        generated_at=datetime.datetime.now().isoformat(),
        language="en",
        total_duration_sec=0.0,
        stories=stories,
    )


if __name__ == "__main__":
    from backend.app.pipeline.collector import fetch_rss_articles
    from backend.app.pipeline.deduplicator import cluster_and_deduplicate

    print("Running Full Script Generator Test...")
    articles = fetch_rss_articles(limit_per_feed=2, fetch_full_body=False)
    clusters = cluster_and_deduplicate(articles)

    print(f"\nGenerating Urdu Bulletin from {len(clusters)} clusters...")
    bulletin_ur = generate_bulletin_with_gemini(clusters, language="ur")

    print("\n--- GENERATED URDU BULLETIN PREVIEW ---")
    print(f"Bulletin ID: {bulletin_ur.bulletin_id}")
    print(f"Total Stories: {len(bulletin_ur.stories)}")
    for s in bulletin_ur.stories:
        print(f"\n[{s.anchor}] Headline: {s.headline}")
        print(f"Spoken Script: {s.spoken_script}")
        print(f"Ticker: {s.ticker_text}")
        print(f"Insight Facts: {[f'{f.key}: {f.value}' for f in s.insight_panel]}")
        print(f"Source: {s.source.publisher} -> {s.source.source_url}")
