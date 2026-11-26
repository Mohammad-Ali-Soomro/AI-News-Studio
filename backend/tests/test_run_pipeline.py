from backend.app.jobs import run_pipeline as job_mod
from backend.app.schemas.bulletin import (
    Bulletin,
    InsightFact,
    SourceArticle,
    StoryRundown,
)


def _sample_bulletin(bulletin_id="b-pipe-1"):
    return Bulletin(
        bulletin_id=bulletin_id,
        title="Evening Bulletin",
        generated_at="2026-11-26T10:00:00Z",
        language="ur",
        total_duration_sec=15.0,
        stories=[
            StoryRundown(
                story_id="story_1",
                category="National",
                anchor="Anchor_A",
                language="ur",
                spoken_script="ڈان کے مطابق اہم قومی خبر جاری ہے۔",
                headline="اہم خبر",
                ticker_text="بریکنگ نیوز: اہم قومی خبر",
                source=SourceArticle(
                    title="National story",
                    publisher="Dawn",
                    source_url="https://www.dawn.com/news/1",
                ),
                insight_panel=[
                    InsightFact(key="شعبہ", value="قومی"),
                    InsightFact(key="مقام", value="اسلام آباد"),
                    InsightFact(key="ماخذ", value="ڈان"),
                ],
                start_time_sec=0.0,
                duration_sec=15.0,
                audio_url="https://example.supabase.co/storage/v1/object/public/media/audio/s1.mp3",
            )
        ],
    )


def test_select_top_clusters_prefers_multi_publisher_then_recency():
    clusters = [
        {
            "cluster_id": "c_single_old",
            "publishers": ["Dawn"],
            "sources": [{"published_at": "Thu, 26 Nov 2026 06:00:00 GMT"}],
        },
        {
            "cluster_id": "c_single_new",
            "publishers": ["Express Tribune"],
            "sources": [{"published_at": "Thu, 26 Nov 2026 11:00:00 GMT"}],
        },
        {
            "cluster_id": "c_multi_older",
            "publishers": ["Dawn", "Express Tribune"],
            "sources": [{"published_at": "Thu, 26 Nov 2026 07:00:00 GMT"}],
        },
    ]

    selected = job_mod.select_top_clusters(clusters, limit=2)
    assert [c["cluster_id"] for c in selected] == ["c_multi_older", "c_single_new"]


def test_run_pipeline_full_mocked_success(monkeypatch):
    calls = []
    sample_articles = [
        {
            "title": "A",
            "summary": "S",
            "body_text": "B",
            "source_url": "https://dawn.com/1",
            "published_at": "Thu, 26 Nov 2026 10:00:00 GMT",
            "publisher": "Dawn",
        }
    ]
    sample_clusters = [
        {
            "cluster_id": "cluster_1",
            "title": "A",
            "publishers": ["Dawn"],
            "primary_source_url": "https://dawn.com/1",
            "aggregated_body": "B",
            "sources": [{"published_at": "Thu, 26 Nov 2026 10:00:00 GMT"}],
        }
    ]

    monkeypatch.setattr(job_mod, "start_run", lambda: (calls.append("start_run"), "run-123")[1])
    monkeypatch.setattr(job_mod, "fetch_rss_articles", lambda fetch_full_body=True: sample_articles)
    monkeypatch.setattr(
        job_mod,
        "save_articles",
        lambda arts: (calls.append(("save_articles", len(arts))), len(arts))[1],
    )
    monkeypatch.setattr(job_mod, "cluster_and_deduplicate", lambda arts: sample_clusters)
    monkeypatch.setattr(
        job_mod,
        "generate_bulletin_with_report",
        lambda clusters, language="ur": (_sample_bulletin(), {"stale": False, "dropped_reasons": []}),
    )

    async def fake_tts(bulletin, upload_to_supabase=True):
        calls.append(("tts", upload_to_supabase))
        return bulletin, {"synthesized": 1, "skipped": 0, "skipped_reasons": []}

    monkeypatch.setattr(job_mod, "synthesize_bulletin_audio", fake_tts)
    monkeypatch.setattr(
        job_mod,
        "save_bulletin",
        lambda b, run_id=None, model_name=None: (calls.append(("save_bulletin", run_id)), "db-b1")[1],
    )
    monkeypatch.setattr(
        job_mod,
        "prune_old_bulletins",
        lambda keep=10: (calls.append(("prune", keep)), 2)[1],
    )
    monkeypatch.setattr(
        job_mod,
        "finish_run",
        lambda run_id, status, stats=None, error=None: calls.append(("finish_run", run_id, status, stats)),
    )

    result = job_mod.run_pipeline(stories=4, dry_run=False)

    assert result["status"] == "success"
    assert result["run_id"] == "run-123"
    assert result["stories_kept"] == 1
    assert result["stories_dropped"] == 0
    assert result["articles_collected"] == 1
    assert result["clusters"] == 1
    assert "collect" in result["seconds_per_stage"]
    assert "tts_upload" in result["seconds_per_stage"]
    assert ("tts", True) in calls
    assert ("save_bulletin", "run-123") in calls
    assert ("prune", 10) in calls
    assert any(c[0] == "finish_run" and c[2] == "success" for c in calls if isinstance(c, tuple))


def test_run_pipeline_dry_run_skips_supabase_and_writes_json(monkeypatch, tmp_path, capsys):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Supabase write should not be called in dry_run mode")

    monkeypatch.setattr(job_mod, "start_run", fail_if_called)
    monkeypatch.setattr(job_mod, "save_articles", fail_if_called)
    monkeypatch.setattr(job_mod, "save_bulletin", fail_if_called)
    monkeypatch.setattr(job_mod, "prune_old_bulletins", fail_if_called)
    monkeypatch.setattr(job_mod, "finish_run", fail_if_called)
    monkeypatch.setattr(job_mod, "get_data_dir", lambda: tmp_path)
    monkeypatch.setattr(
        job_mod,
        "fetch_rss_articles",
        lambda fetch_full_body=True: [
            {
                "title": "A",
                "summary": "S",
                "body_text": "B",
                "source_url": "https://dawn.com/1",
                "published_at": "",
                "publisher": "Dawn",
            }
        ],
    )
    monkeypatch.setattr(
        job_mod,
        "cluster_and_deduplicate",
        lambda arts: [
            {
                "cluster_id": "cluster_1",
                "title": "A",
                "publishers": ["Dawn"],
                "primary_source_url": "https://dawn.com/1",
                "aggregated_body": "B",
                "sources": [],
            }
        ],
    )
    monkeypatch.setattr(
        job_mod,
        "generate_bulletin_with_report",
        lambda clusters, language="ur": (_sample_bulletin("b-dry"), {"stale": False, "dropped_reasons": []}),
    )

    async def fake_tts(bulletin, upload_to_supabase=True):
        assert upload_to_supabase is False
        return bulletin, {"synthesized": 1, "skipped": 0, "skipped_reasons": []}

    monkeypatch.setattr(job_mod, "synthesize_bulletin_audio", fake_tts)

    exit_code = job_mod.main(["--stories", "2", "--dry-run"])
    captured = capsys.readouterr()

    assert exit_code == 0
    expected_file = tmp_path / "bulletins" / "b-dry_dryrun.json"
    assert expected_file.exists()
    assert str(expected_file) in captured.out


def test_run_pipeline_failure_marks_run_failed_and_exits_nonzero(monkeypatch):
    recorded = {}
    monkeypatch.setattr(job_mod, "start_run", lambda: "run-fail-1")
    monkeypatch.setattr(job_mod, "fetch_rss_articles", lambda fetch_full_body=True: [])
    monkeypatch.setattr(
        job_mod,
        "finish_run",
        lambda run_id, status, stats=None, error=None: recorded.update(
            {"run_id": run_id, "status": status, "error": error}
        ),
    )

    exit_code = job_mod.main(["--stories", "4"])

    assert exit_code == 1
    assert recorded["run_id"] == "run-fail-1"
    assert recorded["status"] == "failed"
    assert "No articles" in recorded["error"]
