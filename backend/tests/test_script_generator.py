from types import SimpleNamespace

import pytest

from backend.app.core.config import Settings
from backend.app.pipeline import script_generator
from backend.app.pipeline.script_generator import (
    GeneratedBulletinSchema,
    GeneratedInsightSchema,
    GeneratedStorySchema,
)


def _sample_clusters():
    return [
        {
            "cluster_id": "cluster_1",
            "title": "Federal cabinet approves solar energy policy for 2026",
            "publishers": ["Dawn"],
            "primary_source_url": "https://www.dawn.com/news/101",
            "aggregated_body": (
                "The federal cabinet approved new solar energy incentives in Islamabad "
                "for 2026 on Thursday after consultation with provincial governments."
            ),
            "sources": [
                {
                    "title": "Federal cabinet approves solar energy policy for 2026",
                    "publisher": "Dawn",
                    "url": "https://www.dawn.com/news/101",
                }
            ],
        }
    ]


def _valid_urdu_script():
    return (
        "السلام علیکم، اے آئی نیوز اسٹوڈیو میں خوش آمدید۔ ڈان کے مطابق "
        "وفاقی کابینہ نے جمعرات کو اسلام آباد میں صوبائی حکومتوں سے مشاورت "
        "کے بعد سال 2026 کے لیے شمسی توانائی کی نئی پالیسی اور مراعات کی "
        "منظوری دے دی ہے جس کا اطلاق فوری طور پر کیا جائے گا۔"
    )


def _valid_story_schema(script_override=None):
    return GeneratedStorySchema(
        category="Economy",
        anchor="Anchor_A",
        headline="شمسی توانائی پالیسی کی منظوری",
        ticker_text="بریکنگ نیوز: وفاقی کابینہ نے سال 2026 کی شمسی توانائی پالیسی منظور کر لی",
        spoken_script=script_override or _valid_urdu_script(),
        insight_panel=[
            GeneratedInsightSchema(key="مقام", value="اسلام آباد"),
            GeneratedInsightSchema(key="سال", value="2026"),
            GeneratedInsightSchema(key="ماخذ", value="ڈان"),
        ],
    )


class FakeModels:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def generate_content(self, model, contents, config=None):
        self.calls.append({"model": model, "contents": contents, "config": config})
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(parsed=item, text=item.model_dump_json())


class FakeGenAIClient:
    def __init__(self, responses):
        self.models = FakeModels(responses)


def test_urdu_raises_clear_error_without_gemini_key(monkeypatch, tmp_path):
    monkeypatch.setattr(
        script_generator,
        "get_settings",
        lambda: Settings(_env_file=None, GEMINI_API_KEY="", GEMINI_MODEL=""),
    )

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        script_generator.generate_bulletin_with_report(
            _sample_clusters(),
            language="ur",
            sample_path=tmp_path / "missing.json",
        )


def test_missing_gemini_model_raises_value_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        script_generator,
        "get_settings",
        lambda: Settings(_env_file=None, GEMINI_API_KEY="fake-key", GEMINI_MODEL=""),
    )

    with pytest.raises(ValueError, match="GEMINI_MODEL"):
        script_generator.generate_bulletin_with_report(
            _sample_clusters(),
            language="ur",
            sample_path=tmp_path / "missing.json",
        )


def test_english_fallback_works_without_gemini_key(monkeypatch, tmp_path):
    monkeypatch.setattr(
        script_generator,
        "get_settings",
        lambda: Settings(_env_file=None, GEMINI_API_KEY="", GEMINI_MODEL=""),
    )

    bulletin, report = script_generator.generate_bulletin_with_report(
        _sample_clusters(),
        language="en",
        sample_path=tmp_path / "missing.json",
    )
    assert bulletin.language == "en"
    assert len(bulletin.stories) == 1
    assert report["stale"] is False


def test_mocked_gemini_valid_response_passes_and_saves_sample(monkeypatch, tmp_path):
    monkeypatch.setattr(
        script_generator,
        "get_settings",
        lambda: Settings(
            _env_file=None, GEMINI_API_KEY="fake-key", GEMINI_MODEL="gemini-test"
        ),
    )
    sample_file = tmp_path / "sample_bulletin_ur.json"
    fake_client = FakeGenAIClient(
        [
            GeneratedBulletinSchema(
                title="شام کا خبرنامہ",
                stories=[_valid_story_schema()],
            )
        ]
    )

    bulletin, report = script_generator.generate_bulletin_with_report(
        _sample_clusters(),
        language="ur",
        client=fake_client,
        sample_path=sample_file,
    )

    assert len(fake_client.models.calls) == 1
    assert fake_client.models.calls[0]["model"] == "gemini-test"
    assert report["kept"] == 1
    assert report["dropped"] == 0
    assert report["stale"] is False
    assert len(bulletin.stories) == 1
    assert bulletin.stories[0].anchor == "Anchor_A"
    assert sample_file.exists()


def test_invented_number_triggers_single_story_retry_and_passes(monkeypatch, tmp_path):
    monkeypatch.setattr(
        script_generator,
        "get_settings",
        lambda: Settings(
            _env_file=None, GEMINI_API_KEY="fake-key", GEMINI_MODEL="gemini-test"
        ),
    )
    bad_script = _valid_urdu_script().replace("سال 2026", "سال 2026 اور 77")
    fake_client = FakeGenAIClient(
        [
            GeneratedBulletinSchema(
                title="شام کا خبرنامہ",
                stories=[_valid_story_schema(script_override=bad_script)],
            ),
            _valid_story_schema(),
        ]
    )

    bulletin, report = script_generator.generate_bulletin_with_report(
        _sample_clusters(),
        language="ur",
        client=fake_client,
        sample_path=tmp_path / "sample.json",
    )

    assert len(fake_client.models.calls) == 2
    assert "77" in fake_client.models.calls[1]["contents"]
    assert report["retried"] == 1
    assert report["kept"] == 1
    assert len(bulletin.stories) == 1


def test_english_heavy_script_dropped_when_retry_still_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(
        script_generator,
        "get_settings",
        lambda: Settings(
            _env_file=None, GEMINI_API_KEY="fake-key", GEMINI_MODEL="gemini-test"
        ),
    )
    english_heavy = (
        "Good evening from AI News Studio. The federal cabinet in Islamabad approved "
        "new solar energy incentives for 2026 on Thursday after provincial consultation "
        "to expand clean power generation nationwide. مزید تفصیلات جاری کر دی گئیں۔"
    )
    fake_client = FakeGenAIClient(
        [
            GeneratedBulletinSchema(
                title="Bulletin",
                stories=[_valid_story_schema(script_override=english_heavy)],
            ),
            _valid_story_schema(script_override=english_heavy),
        ]
    )

    with pytest.raises(RuntimeError, match="All generated Urdu stories failed"):
        script_generator.generate_bulletin_with_report(
            _sample_clusters(),
            language="ur",
            client=fake_client,
            sample_path=tmp_path / "sample.json",
        )
    assert len(fake_client.models.calls) == 2


def test_gemini_failure_returns_stale_saved_urdu_bulletin(monkeypatch, tmp_path):
    monkeypatch.setattr(
        script_generator,
        "get_settings",
        lambda: Settings(
            _env_file=None, GEMINI_API_KEY="fake-key", GEMINI_MODEL="gemini-test"
        ),
    )
    sample_file = tmp_path / "sample.json"
    good_client = FakeGenAIClient(
        [
            GeneratedBulletinSchema(
                title="شام کا خبرنامہ",
                stories=[_valid_story_schema()],
            )
        ]
    )
    script_generator.generate_bulletin_with_report(
        _sample_clusters(),
        language="ur",
        client=good_client,
        sample_path=sample_file,
    )

    monkeypatch.setattr(script_generator.time, "sleep", lambda _sec: None)
    failing_client = FakeGenAIClient(
        [RuntimeError("503 UNAVAILABLE")] * 4
    )
    stale_bulletin, report = script_generator.generate_bulletin_with_report(
        _sample_clusters(),
        language="ur",
        client=failing_client,
        sample_path=sample_file,
    )

    assert report["stale"] is True
    assert len(stale_bulletin.stories) == 1
