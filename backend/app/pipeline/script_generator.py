import os
import json
import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load local environment variables (.env)
load_dotenv()

from backend.app.schemas.bulletin import Bulletin, StoryRundown, SourceArticle, InsightFact

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def build_broadcast_prompt(clusters: List[Dict], language: str = "ur") -> str:
    """
    Constructs an expert broadcast journalism prompt for the LLM.
    Instructs the model to generate a television news rundown with dual anchors,
    insight facts, and live ticker lines.
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
   - Anchor_A (Uzma) presents the top national headlines.
   - Anchor_B (Asad) presents the business/international/tech updates.
   - Tone: Formal, dignified, broadcast Urdu as heard on Pakistan television (e.g., 'ناظرین کرام! نیوز اسٹوڈیو میں خوش آمدید...').
   - Keep each story's spoken script between 35 and 60 words (concise, clear, easy to vocalize).
   - Never invent facts, numbers, or unverified claims.
2. Insight Panel (Urdu):
   - Extract exactly 3 key-value facts per story (e.g., key: 'عنوان', value: '...', key: 'اہم اعداد و شمار', value: '...', key: 'ماخذ', value: 'ڈان نیوز').
3. Ticker Text (Urdu):
   - An eye-catching 10 to 15 word scrolling ticker headline (e.g., 'بریکنگ نیوز: ...').
4. Anchor Assignment:
   - Alternate anchors between stories (Anchor_A, Anchor_B).
"""
    else:
        instructions = """
You are the Executive Producer for 'AI News Studio', a premier international television news network.
Your task is to transform the provided raw stories into a professional English broadcast bulletin.

RULES:
1. Spoken Script (English):
   - Anchor_A (Ava) and Anchor_B (Andrew) alternate delivery.
   - Tone: Clear, objective, authoritative broadcast journalism.
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
        {{"key": "Source", "value": "Dawn News"}}
      ]
    }}
  ]
}}
"""

def generate_bulletin_with_gemini(clusters: List[Dict], language: str = "ur") -> Bulletin:
    """
    Generates a broadcast-ready bulletin using Google Gemini API.
    Falls back gracefully to an authentic structured mock if API key is not yet set.
    """
    if not clusters:
        raise ValueError("No story clusters provided for bulletin generation.")

    prompt = build_broadcast_prompt(clusters, language=language)

    # Check if Gemini API Key is provided
    if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            raw_json = json.loads(response.text)
            return Bulletin(
                bulletin_id=raw_json.get("bulletin_id", f"bulletin-{datetime.datetime.now().strftime('%Y%m%d%H%M')}"),
                title=raw_json.get("title", "AI News Studio Bulletin"),
                generated_at=datetime.datetime.now().isoformat(),
                language=language,
                total_duration_sec=0.0,
                stories=[StoryRundown(**s) for s in raw_json.get("stories", [])]
            )
        except Exception as e:
            print(f"[Gemini Generator Warning] Error calling Gemini API: {e}. Falling back to template synthesizer.")

    # High-quality fallback synthesizer for local testing before API key is plugged in
    return generate_fallback_bulletin(clusters, language=language)

def generate_fallback_bulletin(clusters: List[Dict], language: str = "ur") -> Bulletin:
    """
    Deterministic synthesizer that creates broadcast-formatted rundown objects from clusters.
    Guarantees the system works end-to-end even in offline/demo situations.
    """
    stories: List[StoryRundown] = []
    anchors = ["Anchor_A", "Anchor_B"]
    
    for idx, cluster in enumerate(clusters[:4]):
        anchor = anchors[idx % 2]
        story_id = f"story_{idx + 1}"
        publisher_name = cluster.get("publishers", ["Dawn"])[0]
        
        if language == "ur":
            intro = "السلام علیکم! نیوز اسٹوڈیو میں خوش آمدید۔ " if idx == 0 else "مزید خبروں میں، "
            spoken_script = f"{intro} اہم ترین پیش رفت کے مطابق، {cluster['title']}۔ مصدقہ ذرائع کی رپورٹ کے مطابق اس حوالے سے اقدامات جاری ہیں۔"
            headline = f"اہم خبر: {cluster['title'][:60]}"
            ticker = f"بریکنگ نیوز: {cluster['title'][:70]} | ماخذ: {publisher_name}"
            insight = [
                InsightFact(key="اہم خبر", value=cluster['title'][:40]),
                InsightFact(key="شعبہ", value="قومی و سیاسی امور"),
                InsightFact(key="مصدقہ ماخذ", value=publisher_name)
            ]
        else:
            intro = "Good evening and welcome to AI News Studio. " if idx == 0 else "In other major developments, "
            spoken_script = f"{intro} According to confirmed reports, {cluster['title']}. Authorities and representatives are monitoring the situation closely."
            headline = cluster['title'][:60]
            ticker = f"BREAKING: {cluster['title'][:70]} | Source: {publisher_name}"
            insight = [
                InsightFact(key="Headline", value=cluster['title'][:40]),
                InsightFact(key="Category", value="National Affairs"),
                InsightFact(key="Verified Source", value=publisher_name)
            ]

        story = StoryRundown(
            story_id=story_id,
            category="National",
            anchor=anchor,
            language=language,
            spoken_script=spoken_script,
            headline=headline,
            ticker_text=ticker,
            source=SourceArticle(
                title=cluster["title"],
                publisher=publisher_name,
                source_url=cluster.get("primary_source_url", "")
            ),
            insight_panel=insight
        )
        stories.append(story)

    return Bulletin(
        bulletin_id=f"bulletin-{datetime.datetime.now().strftime('%Y%m%d-%H%M')}",
        title="AI News Studio Broadcast Bulletin",
        generated_at=datetime.datetime.now().isoformat(),
        language=language,
        total_duration_sec=0.0,
        stories=stories
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
