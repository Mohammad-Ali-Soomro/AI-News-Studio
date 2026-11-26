import datetime
import logging
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from backend.app.core.config import BACKEND_DIR, get_settings
from backend.app.pipeline.prompts import build_bulletin_prompt, build_story_retry_prompt
from backend.app.pipeline.validators import validate_story
from backend.app.schemas.bulletin import (
    Bulletin,
    InsightFact,
    SourceArticle,
    StoryRundown,
)

logger = logging.getLogger(__name__)

SAMPLE_BULLETIN_UR_PATH = BACKEND_DIR / "data" / "sample_bulletin_ur.json"


class GeneratedInsightSchema(BaseModel):
    key: str
    value: str


class GeneratedStorySchema(BaseModel):
    category: Literal["National", "Economy", "World", "Sports", "Technology"]
    anchor: Literal["Anchor_A"] = "Anchor_A"
    headline: str
    ticker_text: str
    spoken_script: str
    insight_panel: List[GeneratedInsightSchema] = Field(min_length=3, max_length=3)


class GeneratedBulletinSchema(BaseModel):
    title: str
    stories: List[GeneratedStorySchema]


def _is_retryable_gemini_error(exc: Exception) -> bool:
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code in (429, 500, 502, 503, 504):
        return True
    msg = str(exc).upper()
    return any(
        token in msg
        for token in (
            "429",
            "500",
            "502",
            "503",
            "504",
            "RESOURCE_EXHAUSTED",
            "UNAVAILABLE",
            "INTERNAL",
            "DEADLINE_EXCEEDED",
        )
    )


def _is_invalid_model_error(exc: Exception) -> bool:
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    msg = str(exc).upper()
    return code == 404 or "404 NOT_FOUND" in msg or "NO LONGER AVAILABLE" in msg


def _call_with_backoff(
    fn: Callable[[], Any],
    model_name: str,
    max_retries: int = 3,
    base_delay: float = 1.5,
) -> Any:
    """Execute a Gemini API call with exponential backoff on 429 and 5xx errors."""
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if _is_invalid_model_error(exc):
                raise ValueError(
                    f"Invalid or unavailable Gemini model '{model_name}': {exc}"
                ) from exc
            if attempt < max_retries and _is_retryable_gemini_error(exc):
                delay = base_delay * (2**attempt)
                logger.warning(
                    "Gemini temporary error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    max_retries + 1,
                    delay,
                    exc,
                )
                time.sleep(delay)
                continue
            raise
    raise last_exc  # pragma: no cover


def _build_story_from_schema(
    generated: GeneratedStorySchema,
    cluster: Dict,
    story_idx: int,
    language: str,
) -> StoryRundown:
    publishers = cluster.get("publishers") or ["Dawn"]
    source_summary = (cluster.get("aggregated_body") or "").strip()[:1200] or None
    return StoryRundown(
        story_id=f"story_{story_idx}",
        category=generated.category,
        anchor="Anchor_A",
        language=language,
        spoken_script=generated.spoken_script.strip(),
        headline=generated.headline.strip(),
        ticker_text=generated.ticker_text.strip(),
        source=SourceArticle(
            title=cluster.get("title", ""),
            publisher=publishers[0],
            source_url=cluster.get("primary_source_url", ""),
            summary=source_summary,
        ),
        insight_panel=[
            InsightFact(key=item.key.strip(), value=item.value.strip())
            for item in generated.insight_panel
        ],
    )


def _parse_response(response: Any, schema_cls: type[BaseModel]) -> Any:
    parsed = getattr(response, "parsed", None)
    if parsed is not None:
        if isinstance(parsed, schema_cls):
            return parsed
        return schema_cls.model_validate(parsed)
    return schema_cls.model_validate_json(response.text)


def save_sample_urdu_bulletin(
    bulletin: Bulletin, path: Path = SAMPLE_BULLETIN_UR_PATH
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(bulletin.model_dump_json(indent=2), encoding="utf-8")


def load_stale_urdu_bulletin(path: Path = SAMPLE_BULLETIN_UR_PATH) -> Optional[Bulletin]:
    if not path.exists():
        return None
    return Bulletin.model_validate_json(path.read_text(encoding="utf-8"))


def generate_bulletin_with_report(
    clusters: List[Dict],
    language: str = "ur",
    client: Any = None,
    sample_path: Path = SAMPLE_BULLETIN_UR_PATH,
) -> Tuple[Bulletin, Dict[str, Any]]:
    """
    Generate a validated broadcast bulletin in ONE Gemini call, retrying any
    individual failed story once and dropping stories that still fail validation.
    Returns (bulletin, report).
    """
    if not clusters:
        raise ValueError("No story clusters provided for bulletin generation.")

    selected_clusters = clusters[:5]
    settings = get_settings()
    api_key = settings.GEMINI_API_KEY.strip()
    model_name = settings.GEMINI_MODEL.strip()

    has_valid_key = bool(api_key and api_key != "your_gemini_api_key_here")
    if not has_valid_key and client is None:
        if language == "ur":
            stale_bulletin = load_stale_urdu_bulletin(sample_path)
            if stale_bulletin is not None:
                logger.warning(
                    "GEMINI_API_KEY not configured; returning stale saved Urdu bulletin."
                )
                return stale_bulletin, {"stale": True, "kept": len(stale_bulletin.stories), "dropped": 0, "dropped_reasons": []}
            raise RuntimeError(
                "GEMINI_API_KEY is not configured and no saved Urdu sample bulletin exists."
            )
        return generate_fallback_bulletin(selected_clusters, language="en"), {
            "stale": False,
            "kept": min(4, len(selected_clusters)),
            "dropped": 0,
            "dropped_reasons": [],
        }

    if not model_name:
        raise ValueError(
            "GEMINI_MODEL is not configured. Set GEMINI_MODEL in backend/.env."
        )

    from google import genai
    from google.genai import types

    active_client = client if client is not None else genai.Client(api_key=api_key)
    prompt = build_bulletin_prompt(selected_clusters, language=language)

    try:
        response = _call_with_backoff(
            lambda: active_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeneratedBulletinSchema,
                    temperature=0.2,
                ),
            ),
            model_name=model_name,
        )
        generated_bulletin: GeneratedBulletinSchema = _parse_response(
            response, GeneratedBulletinSchema
        )
    except ValueError:
        raise
    except Exception as exc:
        if language == "ur":
            stale_bulletin = load_stale_urdu_bulletin(sample_path)
            if stale_bulletin is not None:
                logger.warning(
                    "Gemini generation failed (%s); returning stale Urdu bulletin.", exc
                )
                return stale_bulletin, {
                    "stale": True,
                    "kept": len(stale_bulletin.stories),
                    "dropped": 0,
                    "dropped_reasons": [f"gemini_error: {exc}"],
                }
            raise RuntimeError(
                f"Gemini Urdu script generation failed for model '{model_name}': {exc}"
            ) from exc
        logger.warning(
            "Gemini English generation failed (%s); using English template fallback.",
            exc,
        )
        fb = generate_fallback_bulletin(selected_clusters, language="en")
        return fb, {"stale": False, "kept": len(fb.stories), "dropped": 0, "dropped_reasons": []}

    kept_stories: List[StoryRundown] = []
    dropped_reasons: List[Dict[str, Any]] = []
    retried_count = 0

    for idx, cluster in enumerate(selected_clusters):
        if idx >= len(generated_bulletin.stories):
            dropped_reasons.append(
                {
                    "cluster_id": cluster.get("cluster_id", f"cluster_{idx + 1}"),
                    "reason": "Missing story in Gemini response.",
                }
            )
            continue

        story = _build_story_from_schema(
            generated_bulletin.stories[idx], cluster, idx + 1, language
        )

        if language != "ur":
            kept_stories.append(story)
            continue

        validation = validate_story(story, cluster)
        if validation.is_valid:
            kept_stories.append(story)
            continue

        # Retry ONLY this failed story once with exact failure reasons
        retried_count += 1
        logger.info(
            "Story %d failed validation (%s); retrying once.",
            idx + 1,
            "; ".join(validation.errors),
        )
        retry_prompt = build_story_retry_prompt(
            cluster,
            position=idx + 1,
            total_stories=len(selected_clusters),
            failure_reasons=validation.errors,
        )
        try:
            retry_resp = _call_with_backoff(
                lambda: active_client.models.generate_content(
                    model=model_name,
                    contents=retry_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=GeneratedStorySchema,
                        temperature=0.1,
                    ),
                ),
                model_name=model_name,
            )
            retried_schema: GeneratedStorySchema = _parse_response(
                retry_resp, GeneratedStorySchema
            )
            retried_story = _build_story_from_schema(
                retried_schema, cluster, idx + 1, language
            )
            retry_validation = validate_story(retried_story, cluster)
            if retry_validation.is_valid:
                kept_stories.append(retried_story)
            else:
                reason = "; ".join(retry_validation.errors)
                logger.warning("Dropping story %d after retry: %s", idx + 1, reason)
                dropped_reasons.append(
                    {
                        "cluster_id": cluster.get("cluster_id", f"cluster_{idx + 1}"),
                        "reason": reason,
                    }
                )
        except Exception as exc:
            reason = f"Retry error: {exc}"
            logger.warning("Dropping story %d after retry error: %s", idx + 1, exc)
            dropped_reasons.append(
                {
                    "cluster_id": cluster.get("cluster_id", f"cluster_{idx + 1}"),
                    "reason": reason,
                }
            )

    if not kept_stories and language == "ur":
        stale_bulletin = load_stale_urdu_bulletin(sample_path)
        if stale_bulletin is not None:
            logger.warning(
                "All stories failed validation; returning stale saved Urdu bulletin."
            )
            return stale_bulletin, {
                "stale": True,
                "kept": len(stale_bulletin.stories),
                "dropped": len(dropped_reasons),
                "dropped_reasons": dropped_reasons,
                "retried": retried_count,
            }
        raise RuntimeError(
            f"All generated Urdu stories failed validation: {dropped_reasons}"
        )

    # Renumber kept story IDs cleanly
    for new_idx, s in enumerate(kept_stories, 1):
        s.story_id = f"story_{new_idx}"

    bulletin = Bulletin(
        bulletin_id=f"bulletin-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        title=generated_bulletin.title or "AI News Studio Urdu Bulletin",
        generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        language=language,
        total_duration_sec=0.0,
        stories=kept_stories,
    )

    if language == "ur" and kept_stories:
        save_sample_urdu_bulletin(bulletin, sample_path)

    report = {
        "stale": False,
        "kept": len(kept_stories),
        "dropped": len(dropped_reasons),
        "dropped_reasons": dropped_reasons,
        "retried": retried_count,
    }
    return bulletin, report


def generate_bulletin_with_gemini(
    clusters: List[Dict],
    language: str = "ur",
    client: Any = None,
) -> Bulletin:
    """Generate a validated broadcast-ready bulletin using Google Gemini."""
    bulletin, _ = generate_bulletin_with_report(
        clusters, language=language, client=client
    )
    return bulletin


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
        bulletin_id=f"bulletin-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M')}",
        title="AI News Studio Broadcast Bulletin",
        generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        language="en",
        total_duration_sec=0.0,
        stories=stories,
    )


if __name__ == "__main__":
    from backend.app.pipeline.collector import fetch_rss_articles
    from backend.app.pipeline.deduplicator import cluster_and_deduplicate

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    print("Running Full Script Generator Test...")
    articles = fetch_rss_articles(limit_per_feed=2, fetch_full_body=False)
    clusters = cluster_and_deduplicate(articles)

    print(f"\nGenerating Urdu Bulletin from {len(clusters[:4])} clusters...")
    bulletin_ur, gen_report = generate_bulletin_with_report(clusters[:4], language="ur")

    print("\n--- GENERATED URDU BULLETIN PREVIEW ---")
    print(f"Bulletin ID: {bulletin_ur.bulletin_id}")
    print(f"Report: {gen_report}")
    print(f"Total Stories: {len(bulletin_ur.stories)}")
    for s in bulletin_ur.stories:
        print(f"\n[{s.anchor} | {s.category}] Headline: {s.headline}")
        print(f"Spoken Script ({len(s.spoken_script.split())} words): {s.spoken_script}")
        print(f"Ticker: {s.ticker_text}")
        print(f"Insight Facts: {[f'{f.key}: {f.value}' for f in s.insight_panel]}")
        print(f"Source: {s.source.publisher} -> {s.source.source_url}")
