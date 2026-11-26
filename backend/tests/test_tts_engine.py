import asyncio
from pathlib import Path
import pytest

from backend.app.pipeline.tts_engine import (
    AzureSpeechProvider,
    TTSProvider,
    clean_text_for_tts,
    synthesize_bulletin_audio,
)
from backend.app.schemas.bulletin import (
    Bulletin,
    InsightFact,
    SourceArticle,
    StoryRundown,
)


def _story(story_id: str, text: str = "ڈان کے مطابق اہم خبر جاری ہے۔") -> StoryRundown:
    return StoryRundown(
        story_id=story_id,
        category="National",
        anchor="Anchor_A",
        language="ur",
        spoken_script=text,
        headline="اہم خبر",
        ticker_text="بریکنگ نیوز: اہم خبر جاری کر دی گئی",
        source=SourceArticle(
            title="Test",
            publisher="Dawn",
            source_url="https://www.dawn.com/news/1",
        ),
        insight_panel=[
            InsightFact(key="شعبہ", value="قومی"),
            InsightFact(key="مقام", value="اسلام آباد"),
            InsightFact(key="ماخذ", value="ڈان"),
        ],
    )


def test_clean_text_for_tts_expands_abbreviations_and_normalizes_digits():
    raw = "PM اور IMF کے درمیان ۲۰۲۶ میں 1,200 ملین ڈالر کا معاہدہ ہوا۔SBP نے تصدیق کی۔"
    cleaned = clean_text_for_tts(raw)

    assert "وزیر اعظم" in cleaned
    assert "آئی ایم ایف" in cleaned
    assert "اسٹیٹ بینک آف پاکستان" in cleaned
    assert "2026" in cleaned
    assert "1200" in cleaned
    assert "ہوا۔ اسٹیٹ" in cleaned


def test_clean_text_for_tts_adds_attribution_pause_and_pronunciation_hints():
    raw = "ڈان کے مطابق اے آئی نیوز اسٹوڈیو میں سکیورٹی اجلاس ہوا۔"
    cleaned = clean_text_for_tts(raw)

    assert "ڈان کے مطابق،" in cleaned
    assert "اے آئی نیوز سٹوڈیو" in cleaned
    assert "سیکیورٹی" in cleaned


def test_clean_text_for_tts_supports_custom_abbreviations():
    cleaned = clean_text_for_tts("GIKI میں نیا سیمینار ہوا۔", abbreviations={"GIKI": "غلام اسحاق خان انسٹی ٹیوٹ"})
    assert "غلام اسحاق خان انسٹی ٹیوٹ" in cleaned


def test_azure_speech_provider_stub_raises_not_implemented(tmp_path):
    provider = AzureSpeechProvider()
    with pytest.raises(NotImplementedError):
        asyncio.run(provider.synthesize("سلام", "ur-PK-UzmaNeural", tmp_path / "a.mp3"))


class FlakyFakeProvider(TTSProvider):
    def __init__(self, fail_story_1_times: int = 1, always_fail_story_2: bool = True):
        self.attempts = {}
        self.fail_story_1_times = fail_story_1_times
        self.always_fail_story_2 = always_fail_story_2

    async def synthesize(self, text: str, voice: str, out_path: Path | str) -> None:
        name = Path(out_path).name
        self.attempts[name] = self.attempts.get(name, 0) + 1
        if "story_1" in name and self.attempts[name] <= self.fail_story_1_times:
            raise RuntimeError("Transient TTS error")
        if "story_2" in name and self.always_fail_story_2:
            raise RuntimeError("Permanent TTS error")
        target = Path(out_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake-mp3")


def test_provider_retries_and_skips_permanently_failing_story(tmp_path):
    bulletin = Bulletin(
        bulletin_id="b-tts",
        title="Test",
        generated_at="2026-11-26T00:00:00Z",
        language="ur",
        stories=[_story("story_1"), _story("story_2"), _story("story_3")],
    )
    fake_provider = FlakyFakeProvider(fail_story_1_times=1, always_fail_story_2=True)

    updated, report = asyncio.run(
        synthesize_bulletin_audio(
            bulletin,
            provider=fake_provider,
            gap_sec=0.6,
            upload_to_supabase=False,
            media_dir=tmp_path,
            duration_fn=lambda _p: 11.5,
            max_retries=3,
            base_delay=0.0,
        )
    )

    assert report["synthesized"] == 2
    assert report["skipped"] == 1
    assert report["skipped_reasons"][0]["story_id"] == "story_2"
    assert [s.story_id for s in updated.stories] == ["story_1", "story_3"]
    assert updated.stories[0].start_time_sec == 0.0
    assert updated.stories[1].start_time_sec == 12.1
    assert updated.total_duration_sec == 23.6
    assert updated.stories[0].audio_url == "/media/audio/b-tts_story_1.mp3"
    assert fake_provider.attempts["b-tts_story_1.mp3"] == 2
    assert fake_provider.attempts["b-tts_story_2.mp3"] == 3
