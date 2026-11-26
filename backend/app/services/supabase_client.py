from datetime import datetime, timezone
import json
import logging
import mimetypes
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
import uuid

from supabase import Client, create_client

from backend.app.core.config import BACKEND_DIR, get_settings
from backend.app.schemas.bulletin import (
    Bulletin,
    InsightFact,
    SourceArticle,
    StoryRundown,
)

logger = logging.getLogger(__name__)

MEDIA_BUCKET = "media"
VALID_RUN_STATUSES = {"running", "success", "partial", "failed"}


def get_data_dir() -> Path:
    """Return the local JSON fallback directory under backend/data."""
    return BACKEND_DIR / "data"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_remote_path(remote_path: str) -> str:
    return remote_path.replace("\\", "/").lstrip("/")


def is_supabase_configured() -> bool:
    """Return True when both Supabase URL and backend key are non-empty."""
    settings = get_settings()
    return bool(
        settings.SUPABASE_URL.strip() and settings.SUPABASE_SERVICE_ROLE_KEY.strip()
    )


def get_client() -> Optional[Client]:
    """
    Create a Supabase client using SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.
    Supports both legacy service_role JWT keys and sb_secret_ keys.
    Returns None when Supabase environment variables are not configured so
    callers fall back to local_json storage.
    """
    settings = get_settings()
    url = settings.SUPABASE_URL.strip()
    key = settings.SUPABASE_SERVICE_ROLE_KEY.strip()
    if not url or not key:
        return None
    return create_client(url, key)


def _resolve_client(client: Optional[Client]) -> Optional[Client]:
    return client if client is not None else get_client()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _story_to_row(
    story: StoryRundown, bulletin_db_id: str, position: int
) -> Dict[str, Any]:
    insight_rows = [fact.model_dump() for fact in story.insight_panel]
    source_dict = story.source.model_dump()
    sources_list = getattr(story, "sources", None) or [source_dict]

    audio_path = None
    if story.audio_url and f"/{MEDIA_BUCKET}/" in story.audio_url:
        audio_path = story.audio_url.split(f"/{MEDIA_BUCKET}/", 1)[1].split("?")[0]
    elif story.audio_url and story.audio_url.startswith("/media/"):
        audio_path = story.audio_url[len("/media/") :]

    return {
        "bulletin_id": bulletin_db_id,
        "position": position,
        "story_key": story.story_id,
        "category": story.category,
        "anchor": story.anchor,
        "headline": story.headline,
        "ticker_text": story.ticker_text,
        "spoken_script": story.spoken_script,
        "insight": insight_rows,
        "source": source_dict,
        "sources": sources_list,
        "audio_path": audio_path,
        "audio_url": story.audio_url,
        "start_time_sec": float(story.start_time_sec),
        "duration_sec": float(story.duration_sec),
    }


def _row_to_story(row: Dict[str, Any]) -> StoryRundown:
    insight_raw = row.get("insight") or []
    source_raw = row.get("source") or {}
    return StoryRundown(
        story_id=row.get("story_key", ""),
        category=row.get("category", "National"),
        anchor=row.get("anchor", "Anchor_A"),
        language=row.get("language", "ur"),
        spoken_script=row.get("spoken_script", ""),
        headline=row.get("headline", ""),
        ticker_text=row.get("ticker_text", ""),
        source=SourceArticle(**source_raw),
        insight_panel=[InsightFact(**item) for item in insight_raw],
        start_time_sec=float(row.get("start_time_sec") or 0.0),
        duration_sec=float(row.get("duration_sec") or 0.0),
        audio_url=row.get("audio_url"),
    )


def save_articles(
    articles: List[Dict[str, Any]], client: Optional[Client] = None
) -> int:
    """Upsert raw ingested articles keyed by URL."""
    if not articles:
        return 0

    deduped_by_url: Dict[str, Dict[str, Any]] = {}
    for article in articles:
        url = (article.get("url") or article.get("source_url") or "").strip()
        if not url:
            continue
        deduped_by_url[url] = {
            "publisher": article.get("publisher", "Unknown"),
            "title": article.get("title", ""),
            "url": url,
            "summary": article.get("summary") or "",
            "published_at": article.get("published_at") or "",
        }

    rows = list(deduped_by_url.values())
    if not rows:
        return 0

    active_client = _resolve_client(client)
    if active_client is None:
        path = get_data_dir() / "articles.json"
        existing = _read_json(path, {})
        for row in rows:
            existing[row["url"]] = {**row, "fetched_at": _utc_now_iso()}
        _write_json(path, existing)
        return len(rows)

    active_client.table("articles").upsert(rows, on_conflict="url").execute()
    return len(rows)


def start_run(client: Optional[Client] = None) -> str:
    """Insert a new pipeline_runs row with status 'running' and return its id."""
    active_client = _resolve_client(client)
    if active_client is None:
        run_id = str(uuid.uuid4())
        path = get_data_dir() / "pipeline_runs.json"
        runs = _read_json(path, [])
        runs.append(
            {
                "id": run_id,
                "started_at": _utc_now_iso(),
                "finished_at": None,
                "status": "running",
                "stats": {},
                "error": None,
            }
        )
        _write_json(path, runs)
        return run_id

    resp = (
        active_client.table("pipeline_runs")
        .insert({"status": "running", "stats": {}})
        .execute()
    )
    return resp.data[0]["id"]


def finish_run(
    run_id: str,
    status: str,
    stats: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    client: Optional[Client] = None,
) -> None:
    """Update a pipeline_runs row with completion status, stats, and optional error."""
    if status not in VALID_RUN_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of {sorted(VALID_RUN_STATUSES)}."
        )

    payload = {
        "finished_at": _utc_now_iso(),
        "status": status,
        "stats": stats or {},
        "error": error,
    }

    active_client = _resolve_client(client)
    if active_client is None:
        path = get_data_dir() / "pipeline_runs.json"
        runs = _read_json(path, [])
        for run in runs:
            if run.get("id") == run_id:
                run.update(payload)
                break
        _write_json(path, runs)
        return

    active_client.table("pipeline_runs").update(payload).eq("id", run_id).execute()


def upload_audio(
    local_path: str | Path,
    remote_path: str,
    client: Optional[Client] = None,
) -> str:
    """
    Upload an audio file to the public 'media' Storage bucket and return its URL.
    Falls back to copying under backend/data/media in local_json mode.
    """
    src = Path(local_path)
    if not src.exists():
        raise FileNotFoundError(f"Audio file not found: {src}")

    clean_remote = _normalize_remote_path(remote_path)
    guessed_type, _ = mimetypes.guess_type(str(src))
    content_type = guessed_type or "audio/mpeg"

    active_client = _resolve_client(client)
    if active_client is None:
        dest = get_data_dir() / MEDIA_BUCKET / clean_remote
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        return f"/media/{clean_remote}"

    data = src.read_bytes()
    bucket = active_client.storage.from_(MEDIA_BUCKET)
    bucket.upload(
        path=clean_remote,
        file=data,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return bucket.get_public_url(clean_remote)


def save_bulletin(
    bulletin: Bulletin,
    run_id: Optional[str] = None,
    model_name: Optional[str] = None,
    client: Optional[Client] = None,
) -> str:
    """
    Save a bulletin and its ordered stories.
    Writes the bulletin as 'draft', replaces its stories, and marks it 'ready'.
    """
    active_client = _resolve_client(client)
    if active_client is None:
        bulletins_dir = get_data_dir() / "bulletins"
        bulletins_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "bulletin": bulletin.model_dump(),
            "status": "ready",
            "model_name": model_name,
            "run_id": run_id,
            "generated_at": bulletin.generated_at or _utc_now_iso(),
        }
        _write_json(bulletins_dir / f"{bulletin.bulletin_id}.json", record)
        _write_json(bulletins_dir / f"{bulletin.language}_latest.json", record)
        return bulletin.bulletin_id

    draft_payload = {
        "bulletin_key": bulletin.bulletin_id,
        "title": bulletin.title,
        "language": bulletin.language,
        "status": "draft",
        "total_duration_sec": float(bulletin.total_duration_sec),
        "model_name": model_name,
        "generated_at": bulletin.generated_at or _utc_now_iso(),
        "run_id": run_id,
    }
    resp = (
        active_client.table("bulletins")
        .upsert(draft_payload, on_conflict="bulletin_key")
        .execute()
    )
    bulletin_db_id = resp.data[0]["id"]

    active_client.table("stories").delete().eq(
        "bulletin_id", bulletin_db_id
    ).execute()

    if bulletin.stories:
        story_rows = [
            _story_to_row(story, bulletin_db_id, idx)
            for idx, story in enumerate(bulletin.stories)
        ]
        active_client.table("stories").insert(story_rows).execute()

    active_client.table("bulletins").update({"status": "ready"}).eq(
        "id", bulletin_db_id
    ).execute()
    return bulletin_db_id


def get_latest_ready_bulletin(
    language: str = "ur", client: Optional[Client] = None
) -> Optional[Bulletin]:
    """Fetch the latest 'ready' bulletin for the given language with ordered stories."""
    active_client = _resolve_client(client)
    if active_client is None:
        bulletins_dir = get_data_dir() / "bulletins"
        latest_file = bulletins_dir / f"{language}_latest.json"
        if latest_file.exists():
            record = _read_json(latest_file, None)
            if record and record.get("status") == "ready":
                return Bulletin(**record["bulletin"])
        return None

    b_resp = (
        active_client.table("bulletins")
        .select("*")
        .eq("language", language)
        .eq("status", "ready")
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    )
    if not b_resp.data:
        return None

    b_row = b_resp.data[0]
    s_resp = (
        active_client.table("stories")
        .select("*")
        .eq("bulletin_id", b_row["id"])
        .order("position", desc=False)
        .execute()
    )

    stories = []
    for s_row in s_resp.data or []:
        row_with_lang = {**s_row, "language": b_row.get("language", language)}
        stories.append(_row_to_story(row_with_lang))

    return Bulletin(
        bulletin_id=b_row["bulletin_key"],
        title=b_row["title"],
        generated_at=str(b_row["generated_at"]),
        language=b_row["language"],
        total_duration_sec=float(b_row.get("total_duration_sec") or 0.0),
        stories=stories,
    )


def prune_old_bulletins(
    keep: int = 10, client: Optional[Client] = None
) -> int:
    """
    Delete bulletins beyond the newest `keep` entries along with their audio files
    to stay within Supabase free storage limits. Returns the number of deleted bulletins.
    """
    if keep < 0:
        raise ValueError("keep must be non-negative")

    active_client = _resolve_client(client)
    if active_client is None:
        bulletins_dir = get_data_dir() / "bulletins"
        if not bulletins_dir.exists():
            return 0
        files = sorted(
            [
                p
                for p in bulletins_dir.glob("*.json")
                if not p.name.endswith("_latest.json")
            ],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        deleted = 0
        for old_file in files[keep:]:
            old_file.unlink(missing_ok=True)
            deleted += 1
        return deleted

    b_resp = (
        active_client.table("bulletins")
        .select("id, bulletin_key, generated_at")
        .order("generated_at", desc=True)
        .execute()
    )
    rows = b_resp.data or []
    old_rows = rows[keep:]
    if not old_rows:
        return 0

    old_ids = [r["id"] for r in old_rows]
    s_resp = (
        active_client.table("stories")
        .select("audio_path")
        .in_("bulletin_id", old_ids)
        .execute()
    )
    audio_paths = [
        s["audio_path"] for s in (s_resp.data or []) if s.get("audio_path")
    ]
    if audio_paths:
        try:
            active_client.storage.from_(MEDIA_BUCKET).remove(audio_paths)
        except Exception as exc:
            logger.warning("Failed to remove some old audio files: %s", exc)

    active_client.table("bulletins").delete().in_("id", old_ids).execute()
    return len(old_ids)
