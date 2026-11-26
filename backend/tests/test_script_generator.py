import pytest

from backend.app.core.config import Settings
from backend.app.pipeline import script_generator


def _sample_clusters():
    return [
        {
            "cluster_id": "cluster_1",
            "title": "Federal cabinet approves solar energy policy",
            "publishers": ["Dawn"],
            "primary_source_url": "https://www.dawn.com/news/101",
            "aggregated_body": "The federal cabinet approved new solar energy incentives on Thursday.",
        }
    ]


def test_urdu_raises_clear_error_without_gemini_key(monkeypatch):
    monkeypatch.setattr(
        script_generator,
        "get_settings",
        lambda: Settings(_env_file=None, GEMINI_API_KEY="", GEMINI_MODEL=""),
    )

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        script_generator.generate_bulletin_with_gemini(_sample_clusters(), language="ur")


def test_missing_gemini_model_raises_value_error(monkeypatch):
    monkeypatch.setattr(
        script_generator,
        "get_settings",
        lambda: Settings(_env_file=None, GEMINI_API_KEY="fake-key", GEMINI_MODEL=""),
    )

    with pytest.raises(ValueError, match="GEMINI_MODEL"):
        script_generator.generate_bulletin_with_gemini(_sample_clusters(), language="ur")


def test_english_fallback_works_without_gemini_key(monkeypatch):
    monkeypatch.setattr(
        script_generator,
        "get_settings",
        lambda: Settings(_env_file=None, GEMINI_API_KEY="", GEMINI_MODEL=""),
    )

    bulletin = script_generator.generate_bulletin_with_gemini(
        _sample_clusters(), language="en"
    )
    assert bulletin.language == "en"
    assert len(bulletin.stories) == 1
    assert bulletin.stories[0].language == "en"
