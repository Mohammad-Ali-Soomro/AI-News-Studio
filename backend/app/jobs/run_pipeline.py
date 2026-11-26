"""
End-to-end batch pipeline job for AI News Studio.

Usage:
    python -m backend.app.jobs.run_pipeline [--stories 4] [--dry-run]
"""

import argparse
import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

from backend.app.core.config import get_settings
from backend.app.pipeline.collector import fetch_rss_articles
from backend.app.pipeline.deduplicator import cluster_and_deduplicate
from backend.app.pipeline.script_generator import generate_bulletin_with_report
from backend.app.pipeline.tts_engine import synthesize_bulletin_audio
from backend.app.services.supabase_client import (
    finish_run,
    get_data_dir,
    prune_old_bulletins,
    save_articles,
    save_bulletin,
    start_run,
)

logger = logging.getLogger(__name__)


def _parse_published_timestamp(published_at: Optional[str]) -> float:
    """Parse RFC 2822 or ISO timestamps into a UTC epoch float; return 0.0 if missing."""
    if not published_at:
        return 0.0
    raw = str(published_at).strip()
    if not raw:
        return 0.0
    try:
        dt = parsedate_to_datetime(raw)
    except Exception:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def select_top_clusters(clusters: List[Dict], limit: int = 4) -> List[Dict]:
    """
    Pick the top N story clusters, preferring stories covered by more than one
    publisher first and then sorting by most recent publication timestamp.
    """
    if limit <= 0 or not clusters:
        return []

    def sort_key(cluster: Dict) -> tuple:
        unique_pubs = len(set(cluster.get("publishers") or []))
        multi_publisher = 1 if unique_pubs > 1 else 0
        timestamps = [
            _parse_published_timestamp(src.get("published_at"))
            for src in (cluster.get("sources") or [])
        ]
        newest_ts = max(timestamps) if timestamps else 0.0
        return (multi_publisher, unique_pubs, newest_ts)

    ranked = sorted(clusters, key=sort_key, reverse=True)
    return ranked[:limit]


def run_pipeline(
    stories: int = 4,
    dry_run: bool = False,
    existing_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the full AI News Studio pipeline from RSS collection through
    Supabase publication (or dry-run JSON output).
    """
    if stories <= 0:
        raise ValueError("stories must be a positive integer.")

    settings = get_settings()
    seconds_per_stage: Dict[str, float] = {}
    stats: Dict[str, Any] = {
        "articles_collected": 0,
        "clusters": 0,
        "stories_kept": 0,
        "stories_dropped": 0,
        "dropped_reasons": [],
        "seconds_per_stage": seconds_per_stage,
        "dry_run": dry_run,
    }

    total_start = time.perf_counter()
    run_id = existing_run_id
    if not dry_run and run_id is None:
        run_id = start_run()

    try:
        # 1. Collect RSS articles
        t0 = time.perf_counter()
        articles = fetch_rss_articles(fetch_full_body=True)
        seconds_per_stage["collect"] = round(time.perf_counter() - t0, 3)
        stats["articles_collected"] = len(articles)
        if not articles:
            raise RuntimeError("No articles were collected from any RSS feed.")

        # 2. Save raw articles
        if not dry_run:
            t0 = time.perf_counter()
            save_articles(articles)
            seconds_per_stage["save_articles"] = round(time.perf_counter() - t0, 3)

        # 3. Deduplicate and cluster
        t0 = time.perf_counter()
        clusters = cluster_and_deduplicate(articles)
        seconds_per_stage["deduplicate"] = round(time.perf_counter() - t0, 3)
        stats["clusters"] = len(clusters)
        if not clusters:
            raise RuntimeError("Clustering produced zero story clusters.")

        # 4. Select top N clusters
        t0 = time.perf_counter()
        selected_clusters = select_top_clusters(clusters, limit=stories)
        seconds_per_stage["select"] = round(time.perf_counter() - t0, 3)

        # 5. Generate & validate Urdu script
        t0 = time.perf_counter()
        bulletin, script_report = generate_bulletin_with_report(
            selected_clusters, language="ur"
        )
        seconds_per_stage["script_generation"] = round(time.perf_counter() - t0, 3)

        # 6. Synthesize TTS, measure duration, compute timeline, upload audio
        t0 = time.perf_counter()
        bulletin, tts_report = asyncio.run(
            synthesize_bulletin_audio(
                bulletin,
                upload_to_supabase=not dry_run,
            )
        )
        seconds_per_stage["tts_upload"] = round(time.perf_counter() - t0, 3)

        if not bulletin.stories:
            raise RuntimeError("All stories failed TTS synthesis; aborting bulletin.")

        dropped_reasons = list(script_report.get("dropped_reasons") or []) + list(
            tts_report.get("skipped_reasons") or []
        )
        stats["stories_kept"] = len(bulletin.stories)
        stats["stories_dropped"] = len(dropped_reasons)
        stats["dropped_reasons"] = dropped_reasons
        stats["stale"] = bool(script_report.get("stale", False))
        stats["bulletin_id"] = bulletin.bulletin_id
        stats["total_duration_sec"] = bulletin.total_duration_sec

        # 7. Save bulletin & prune old bulletins (or write dry-run JSON)
        if dry_run:
            dry_run_path: Path = (
                get_data_dir() / "bulletins" / f"{bulletin.bulletin_id}_dryrun.json"
            )
            dry_run_path.parent.mkdir(parents=True, exist_ok=True)
            dry_run_path.write_text(bulletin.model_dump_json(indent=2), encoding="utf-8")
            seconds_per_stage["total"] = round(time.perf_counter() - total_start, 3)
            stats["dry_run_path"] = str(dry_run_path)
            logger.info("Dry-run complete. Bulletin JSON saved to %s", dry_run_path)
            return stats

        t0 = time.perf_counter()
        save_bulletin(
            bulletin,
            run_id=run_id,
            model_name=settings.GEMINI_MODEL.strip() or None,
        )
        seconds_per_stage["save_bulletin"] = round(time.perf_counter() - t0, 3)

        t0 = time.perf_counter()
        pruned_count = prune_old_bulletins(keep=10)
        seconds_per_stage["prune"] = round(time.perf_counter() - t0, 3)
        stats["pruned_bulletins"] = pruned_count

        seconds_per_stage["total"] = round(time.perf_counter() - total_start, 3)
        final_status = (
            "partial"
            if (stats["stories_dropped"] > 0 or stats["stale"])
            else "success"
        )
        if run_id is not None:
            finish_run(run_id, status=final_status, stats=stats)

        stats["run_id"] = run_id
        stats["status"] = final_status
        return stats

    except Exception as exc:
        seconds_per_stage["total"] = round(time.perf_counter() - total_start, 3)
        logger.error("Pipeline run failed: %s", exc)
        if not dry_run and run_id is not None:
            try:
                finish_run(run_id, status="failed", stats=stats, error=str(exc))
            except Exception as finish_exc:
                logger.error("Could not record failed run status: %s", finish_exc)
        raise


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Run the end-to-end AI News Studio Urdu bulletin pipeline."
    )
    parser.add_argument(
        "--stories",
        type=int,
        default=4,
        help="Maximum number of top story clusters to include (default: 4)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all stages without Supabase writes and print the output JSON path",
    )
    args = parser.parse_args(argv)

    try:
        result = run_pipeline(stories=args.stories, dry_run=args.dry_run)
    except Exception as exc:
        print(f"ERROR: Pipeline failed: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"Dry-run bulletin JSON: {result['dry_run_path']}")
    else:
        print(
            f"Pipeline {result['status']}: run_id={result['run_id']}, "
            f"bulletin_id={result['bulletin_id']}, "
            f"kept={result['stories_kept']}, dropped={result['stories_dropped']}"
        )
    print(f"Stage timings (sec): {result['seconds_per_stage']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
