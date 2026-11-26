from fastapi.testclient import TestClient

from backend.app import main as main_mod
from backend.app.schemas.bulletin import (
    Bulletin,
    InsightFact,
    SourceArticle,
    StoryRundown,
)


def _sample_bulletin():
    return Bulletin(
        bulletin_id="b-api-1",
        title="Evening Bulletin",
        generated_at="2026-11-26T10:00:00Z",
        language="ur",
        total_duration_sec=12.0,
        stories=[
            StoryRundown(
                story_id="story_1",
                category="National",
                anchor="Anchor_A",
                language="ur",
                spoken_script="ڈان کے مطابق اہم خبر۔",
                headline="اہم خبر",
                ticker_text="بریکنگ نیوز",
                source=SourceArticle(
                    title="Story",
                    publisher="Dawn",
                    source_url="https://dawn.com/1",
                ),
                insight_panel=[
                    InsightFact(key="شعبہ", value="قومی"),
                    InsightFact(key="مقام", value="اسلام آباد"),
                    InsightFact(key="ماخذ", value="ڈان"),
                ],
                start_time_sec=0.0,
                duration_sec=12.0,
                audio_url="/media/audio/s1.mp3",
            )
        ],
    )


def test_latest_bulletin_endpoint_reads_ready_bulletin(monkeypatch):
    monkeypatch.setattr(
        main_mod, "get_latest_ready_bulletin", lambda language="ur": _sample_bulletin()
    )
    client = TestClient(main_mod.app)
    resp = client.get("/api/v1/bulletin/latest?language=ur")
    assert resp.status_code == 200
    assert resp.json()["bulletin_id"] == "b-api-1"


def test_latest_bulletin_endpoint_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(main_mod, "get_latest_ready_bulletin", lambda language="ur": None)
    client = TestClient(main_mod.app)
    resp = client.get("/api/v1/bulletin/latest")
    assert resp.status_code == 404


def test_trigger_pipeline_run_and_list_runs(monkeypatch):
    triggered = {}
    monkeypatch.setattr(main_mod, "start_run", lambda: "run-xyz")
    monkeypatch.setattr(
        main_mod,
        "run_pipeline",
        lambda stories=4, dry_run=False, existing_run_id=None: triggered.update(
            {"stories": stories, "dry_run": dry_run, "run_id": existing_run_id}
        ),
    )
    monkeypatch.setattr(
        main_mod,
        "list_recent_runs",
        lambda limit=10: [{"id": "run-xyz", "status": "success"}],
    )

    client = TestClient(main_mod.app)
    post_resp = client.post("/api/v1/pipeline/run?stories=3")
    assert post_resp.status_code == 200
    assert post_resp.json() == {"run_id": "run-xyz", "status": "running"}
    assert triggered == {"stories": 3, "dry_run": False, "run_id": "run-xyz"}

    runs_resp = client.get("/api/v1/pipeline/runs?limit=5")
    assert runs_resp.status_code == 200
    assert runs_resp.json()["count"] == 1
    assert runs_resp.json()["runs"][0]["id"] == "run-xyz"


def test_old_generating_get_routes_removed():
    client = TestClient(main_mod.app)
    assert client.get("/api/v1/news/latest-raw").status_code == 404
    assert client.get("/api/v1/news/clusters").status_code == 404
    assert client.post("/api/v1/bulletin/generate").status_code == 404
