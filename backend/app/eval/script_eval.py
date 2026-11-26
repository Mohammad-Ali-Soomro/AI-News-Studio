"""
Evaluation helper that runs story validators over saved Urdu bulletins
and prints a pass-rate table for FYP reporting.

Usage:
    python -m backend.app.eval.script_eval
"""

from pathlib import Path
import sys
from typing import List

from backend.app.core.config import BACKEND_DIR
from backend.app.pipeline.validators import validate_story
from backend.app.schemas.bulletin import Bulletin, StoryRundown


def _cluster_from_story(story: StoryRundown) -> dict:
    return {
        "title": story.source.title,
        "aggregated_body": story.source.summary or story.source.title,
        "publishers": [story.source.publisher],
        "sources": [
            {
                "title": story.source.title,
                "publisher": story.source.publisher,
                "url": story.source.source_url,
            }
        ],
    }


def discover_saved_bulletins(data_dir: Path) -> List[Path]:
    paths: List[Path] = []
    sample = data_dir / "sample_bulletin_ur.json"
    if sample.exists():
        paths.append(sample)
    bulletins_dir = data_dir / "bulletins"
    if bulletins_dir.exists():
        for p in sorted(bulletins_dir.glob("*.json")):
            if not p.name.endswith("_latest.json"):
                paths.append(p)
    return paths


def evaluate_bulletins(paths: List[Path]) -> int:
    if not paths:
        print("No saved bulletins found under backend/data/.")
        return 1

    total_stories = 0
    passed_stories = 0

    print("| Bulletin | Story | Words | Urdu Ratio | Passed | Errors |")
    print("| :--- | :--- | ---: | ---: | :---: | :--- |")

    for path in paths:
        raw = path.read_text(encoding="utf-8")
        try:
            bulletin = Bulletin.model_validate_json(raw)
        except Exception:
            import json

            wrapped = json.loads(raw)
            bulletin = Bulletin(**wrapped["bulletin"])

        for story in bulletin.stories:
            total_stories += 1
            res = validate_story(story, _cluster_from_story(story))
            if res.is_valid:
                passed_stories += 1
            status = "PASS" if res.is_valid else "FAIL"
            errors = "; ".join(res.errors) if res.errors else "-"
            print(
                f"| {bulletin.bulletin_id} | {story.story_id} | "
                f"{res.metrics['word_count']} | {res.metrics['urdu_ratio']:.2f} | "
                f"{status} | {errors} |"
            )

    rate = (passed_stories / total_stories * 100.0) if total_stories else 0.0
    print(f"\nTotal stories: {total_stories}, Passed: {passed_stories}, Pass rate: {rate:.1f}%")
    return 0


def main() -> int:
    paths = discover_saved_bulletins(BACKEND_DIR / "data")
    return evaluate_bulletins(paths)


if __name__ == "__main__":
    sys.exit(main())
