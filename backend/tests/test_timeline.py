import pytest

from backend.app.pipeline.timeline import compute_bulletin_timeline
from backend.app.schemas.bulletin import (
    Bulletin,
    InsightFact,
    SourceArticle,
    StoryRundown,
)


def _story(story_id: str, duration: float) -> StoryRundown:
    return StoryRundown(
        story_id=story_id,
        category="National",
        anchor="Anchor_A",
        language="ur",
        spoken_script="خبر کا متن۔",
        headline="عنوان",
        ticker_text="ٹکر خبر",
        source=SourceArticle(
            title="Test",
            publisher="Dawn",
            source_url="https://www.dawn.com/news/1",
        ),
        insight_panel=[
            InsightFact(key="ک", value="و"),
            InsightFact(key="م", value="ق"),
            InsightFact(key="ن", value="ز"),
        ],
        duration_sec=duration,
    )


def test_timeline_computes_cumulative_starts_with_gap():
    bulletin = Bulletin(
        bulletin_id="b-1",
        title="Test",
        generated_at="2026-11-26T00:00:00Z",
        language="ur",
        stories=[_story("story_1", 10.25), _story("story_2", 14.5), _story("story_3", 8.0)],
    )

    updated = compute_bulletin_timeline(bulletin, gap_sec=0.6)

    assert updated.stories[0].start_time_sec == 0.0
    assert updated.stories[1].start_time_sec == 10.85
    assert updated.stories[2].start_time_sec == 25.95
    assert updated.total_duration_sec == 33.95


def test_timeline_handles_empty_stories():
    bulletin = Bulletin(
        bulletin_id="b-empty",
        title="Empty",
        generated_at="2026-11-26T00:00:00Z",
        language="ur",
        stories=[],
    )
    updated = compute_bulletin_timeline(bulletin)
    assert updated.total_duration_sec == 0.0


def test_timeline_rejects_negative_gap():
    bulletin = Bulletin(
        bulletin_id="b-neg",
        title="Test",
        generated_at="2026-11-26T00:00:00Z",
        language="ur",
        stories=[_story("story_1", 5.0)],
    )
    with pytest.raises(ValueError, match="non-negative"):
        compute_bulletin_timeline(bulletin, gap_sec=-0.1)
