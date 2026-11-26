from backend.app.pipeline.validators import (
    compute_urdu_letter_ratio,
    normalize_digits,
    validate_story,
)
from backend.app.schemas.bulletin import InsightFact, SourceArticle, StoryRundown


def _make_valid_urdu_script(extra: str = "") -> str:
    base = (
        "السلام علیکم، اے آئی نیوز اسٹوڈیو میں خوش آمدید۔ ڈان کے مطابق "
        "وفاقی کابینہ نے جمعرات کو اسلام آباد میں توانائی اصلاحات کے نئے "
        "منصوبے کی منظوری دے دی ہے جس کے تحت سال 2026 میں بجلی کی تقسیم "
        "کا نظام بہتر بنایا جائے گا اور صوبوں کے ساتھ مشاورت جاری رہے گی۔"
    )
    if extra:
        return f"{base} {extra}".strip()
    return base


def _sample_cluster():
    return {
        "cluster_id": "cluster_1",
        "title": "Federal cabinet approves energy reform plan for 2026 in Islamabad",
        "publishers": ["Dawn"],
        "primary_source_url": "https://www.dawn.com/news/101",
        "aggregated_body": (
            "The federal cabinet approved an energy reform plan in Islamabad on Thursday "
            "to improve power distribution in 2026 with provincial consultation."
        ),
        "sources": [
            {
                "title": "Federal cabinet approves energy reform plan for 2026 in Islamabad",
                "publisher": "Dawn",
                "url": "https://www.dawn.com/news/101",
            }
        ],
    }


def _make_story(
    spoken_script: str,
    insight_panel=None,
    ticker_text: str = "اہم خبر: وفاقی کابینہ نے توانائی اصلاحات کے منصوبے کی منظوری دے دی",
    category: str = "National",
) -> StoryRundown:
    if insight_panel is None:
        insight_panel = [
            InsightFact(key="مقام", value="اسلام آباد"),
            InsightFact(key="سال", value="۲۰۲۶"),
            InsightFact(key="ماخذ", value="ڈان"),
        ]
    return StoryRundown(
        story_id="story_1",
        category=category,
        anchor="Anchor_A",
        language="ur",
        spoken_script=spoken_script,
        headline="توانائی اصلاحات منصوبے کی منظوری",
        ticker_text=ticker_text,
        source=SourceArticle(
            title="Federal cabinet approves energy reform plan for 2026 in Islamabad",
            publisher="Dawn",
            source_url="https://www.dawn.com/news/101",
        ),
        insight_panel=insight_panel,
    )


def test_valid_urdu_story_passes_with_urdu_digit_normalization():
    story = _make_story(_make_valid_urdu_script())
    result = validate_story(story, _sample_cluster())
    assert result.is_valid, f"Unexpected errors: {result.errors}"
    assert result.metrics["urdu_ratio"] >= 0.80
    assert 35 <= result.metrics["word_count"] <= 60


def test_invented_number_is_rejected():
    script = _make_valid_urdu_script("اس منصوبے پر 99 ارب روپے خرچ ہوں گے۔")
    story = _make_story(script)
    result = validate_story(story, _sample_cluster())
    assert not result.is_valid
    assert any("99" in err for err in result.errors)


def test_unverified_english_entity_is_rejected():
    story = _make_story(
        _make_valid_urdu_script(),
        insight_panel=[
            InsightFact(key="ادارہ", value="IMF"),
            InsightFact(key="مقام", value="اسلام آباد"),
            InsightFact(key="ماخذ", value="ڈان"),
        ],
    )
    result = validate_story(story, _sample_cluster())
    assert not result.is_valid
    assert any("IMF" in err for err in result.errors)


def test_english_heavy_script_is_rejected():
    english_heavy = (
        "Welcome to AI News Studio. According to Dawn, the federal cabinet in Islamabad "
        "approved the new energy reform plan for 2026 on Thursday to modernize power "
        "distribution across all provinces with full coordination and oversight today. "
        "وزیر توانائی نے بیان جاری کیا۔"
    )
    assert compute_urdu_letter_ratio(english_heavy) < 0.80
    story = _make_story(english_heavy)
    result = validate_story(story, _sample_cluster())
    assert not result.is_valid
    assert any("Urdu script ratio" in err for err in result.errors)


def test_digit_normalization_helper():
    assert normalize_digits("۲۰۲۶ اور ١٢") == "2026 اور 12"
