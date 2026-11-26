from types import SimpleNamespace

import pytest

from backend.app.core.config import Settings
from backend.app.schemas.bulletin import (
    Bulletin,
    InsightFact,
    SourceArticle,
    StoryRundown,
)
from backend.app.services import supabase_client


class FakeQueryBuilder:
    def __init__(self, tables, table_name):
        self.tables = tables
        self.table_name = table_name
        self._op = None
        self._payload = None
        self._on_conflict = None
        self._filters = []
        self._in_filters = []
        self._order_col = None
        self._order_desc = False
        self._limit = None
        self._counter = len(tables[table_name])

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload if isinstance(payload, list) else [payload]
        return self

    def upsert(self, payload, on_conflict=None):
        self._op = "upsert"
        self._payload = payload if isinstance(payload, list) else [payload]
        self._on_conflict = on_conflict
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    def select(self, _cols="*"):
        self._op = "select"
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def in_(self, col, vals):
        self._in_filters.append((col, set(vals)))
        return self

    def order(self, col, desc=False):
        self._order_col = col
        self._order_desc = desc
        return self

    def limit(self, count):
        self._limit = count
        return self

    def _matches(self, row):
        for col, val in self._filters:
            if row.get(col) != val:
                return False
        for col, vals in self._in_filters:
            if row.get(col) not in vals:
                return False
        return True

    def execute(self):
        rows = self.tables[self.table_name]
        if self._op == "insert":
            inserted = []
            for item in self._payload:
                row = dict(item)
                if "id" not in row:
                    self._counter += 1
                    row["id"] = f"{self.table_name}-{self._counter}"
                rows.append(row)
                inserted.append(row)
            return SimpleNamespace(data=inserted)

        if self._op == "upsert":
            out = []
            key = self._on_conflict
            for item in self._payload:
                existing = next(
                    (r for r in rows if key and r.get(key) == item.get(key)), None
                )
                if existing is not None:
                    existing.update(item)
                    out.append(existing)
                else:
                    row = dict(item)
                    if "id" not in row:
                        self._counter += 1
                        row["id"] = f"{self.table_name}-{self._counter}"
                    rows.append(row)
                    out.append(row)
            return SimpleNamespace(data=out)

        if self._op == "update":
            updated = []
            for row in rows:
                if self._matches(row):
                    row.update(self._payload)
                    updated.append(row)
            return SimpleNamespace(data=updated)

        if self._op == "delete":
            kept = []
            removed = []
            for row in rows:
                if self._matches(row):
                    removed.append(row)
                else:
                    kept.append(row)
            self.tables[self.table_name] = kept
            # Cascade delete stories when deleting bulletins
            if self.table_name == "bulletins" and removed:
                removed_ids = {r["id"] for r in removed}
                self.tables["stories"] = [
                    s
                    for s in self.tables["stories"]
                    if s.get("bulletin_id") not in removed_ids
                ]
            return SimpleNamespace(data=removed)

        if self._op == "select":
            matched = [dict(r) for r in rows if self._matches(r)]
            if self._order_col:
                matched.sort(
                    key=lambda r: (
                        r.get(self._order_col) is None,
                        r.get(self._order_col),
                    ),
                    reverse=self._order_desc,
                )
            if self._limit is not None:
                matched = matched[: self._limit]
            return SimpleNamespace(data=matched)

        return SimpleNamespace(data=[])


class FakeBucket:
    def __init__(self, bucket_name, files):
        self.bucket_name = bucket_name
        self.files = files

    def upload(self, path, file, file_options=None):
        self.files[path] = {"bytes": file, "options": file_options}
        return {"path": path}

    def get_public_url(self, path):
        return f"https://example.supabase.co/storage/v1/object/public/{self.bucket_name}/{path}"

    def remove(self, paths):
        for p in paths:
            self.files.pop(p, None)
        return paths


class FakeStorage:
    def __init__(self):
        self.buckets = {}

    def from_(self, bucket_name):
        if bucket_name not in self.buckets:
            self.buckets[bucket_name] = {}
        return FakeBucket(bucket_name, self.buckets[bucket_name])


class FakeSupabaseClient:
    def __init__(self):
        self.tables = {
            "articles": [],
            "pipeline_runs": [],
            "bulletins": [],
            "stories": [],
        }
        self.storage = FakeStorage()

    def table(self, name):
        return FakeQueryBuilder(self.tables, name)


def _sample_bulletin(bulletin_id="b-1", generated_at="2026-11-26T10:00:00Z"):
    return Bulletin(
        bulletin_id=bulletin_id,
        title="Evening Urdu Bulletin",
        generated_at=generated_at,
        language="ur",
        total_duration_sec=25.0,
        stories=[
            StoryRundown(
                story_id="story_2",
                category="Economy",
                anchor="Anchor_A",
                language="ur",
                spoken_script="دوسری خبر معیشت کے بارے میں ہے۔",
                headline="معاشی پیش رفت",
                ticker_text="بریکنگ نیوز: معاشی اعداد و شمار جاری",
                source=SourceArticle(
                    title="Economic update",
                    publisher="Dawn",
                    source_url="https://www.dawn.com/news/2",
                ),
                insight_panel=[
                    InsightFact(key="شعبہ", value="معیشت"),
                    InsightFact(key="مقام", value="اسلام آباد"),
                    InsightFact(key="ماخذ", value="ڈان"),
                ],
                start_time_sec=12.0,
                duration_sec=13.0,
                audio_url="https://example.supabase.co/storage/v1/object/public/media/b-1/story_2.mp3",
            ),
            StoryRundown(
                story_id="story_1",
                category="National",
                anchor="Anchor_A",
                language="ur",
                spoken_script="پہلی خبر قومی امور کے بارے میں ہے۔",
                headline="قومی خبر",
                ticker_text="اہم خبر: قومی اسمبلی کا اجلاس",
                source=SourceArticle(
                    title="National update",
                    publisher="Express Tribune",
                    source_url="https://tribune.com.pk/story/1",
                ),
                insight_panel=[
                    InsightFact(key="شعبہ", value="قومی"),
                    InsightFact(key="مقام", value="اسلام آباد"),
                    InsightFact(key="ماخذ", value="ایکسپریس ٹریبیون"),
                ],
                start_time_sec=0.0,
                duration_sec=12.0,
                audio_url="https://example.supabase.co/storage/v1/object/public/media/b-1/story_1.mp3",
            ),
        ],
    )


def test_fake_client_run_articles_bulletin_and_prune(tmp_path):
    fake = FakeSupabaseClient()

    # Articles upsert deduplicates by URL
    saved_count = supabase_client.save_articles(
        [
            {"publisher": "Dawn", "title": "A", "source_url": "https://dawn.com/1"},
            {"publisher": "Dawn", "title": "A2", "source_url": "https://dawn.com/1"},
            {"publisher": "Express Tribune", "title": "B", "url": "https://tribune.com.pk/2"},
        ],
        client=fake,
    )
    assert saved_count == 2
    assert len(fake.tables["articles"]) == 2

    # Runs lifecycle
    run_id = supabase_client.start_run(client=fake)
    assert fake.tables["pipeline_runs"][0]["status"] == "running"
    supabase_client.finish_run(
        run_id, status="success", stats={"kept": 2}, client=fake
    )
    assert fake.tables["pipeline_runs"][0]["status"] == "success"
    assert fake.tables["pipeline_runs"][0]["stats"] == {"kept": 2}

    # Upload audio
    audio_file = tmp_path / "story_1.mp3"
    audio_file.write_bytes(b"fake-mp3-bytes")
    public_url = supabase_client.upload_audio(
        audio_file, "b-1/story_1.mp3", client=fake
    )
    assert public_url.endswith("/media/b-1/story_1.mp3")
    assert "b-1/story_1.mp3" in fake.storage.buckets["media"]

    # Save bulletins and verify latest ready retrieval
    b1 = _sample_bulletin("b-1", "2026-11-26T09:00:00Z")
    b2 = _sample_bulletin("b-2", "2026-11-26T10:00:00Z")
    supabase_client.save_bulletin(b1, run_id=run_id, model_name="gemini-test", client=fake)
    supabase_client.save_bulletin(b2, run_id=run_id, model_name="gemini-test", client=fake)

    latest = supabase_client.get_latest_ready_bulletin(language="ur", client=fake)
    assert latest is not None
    assert latest.bulletin_id == "b-2"
    assert [s.story_id for s in latest.stories] == ["story_2", "story_1"]

    # Prune keeping newest 1 should remove b-1 and its audio
    pruned = supabase_client.prune_old_bulletins(keep=1, client=fake)
    assert pruned == 1
    assert len(fake.tables["bulletins"]) == 1
    assert fake.tables["bulletins"][0]["bulletin_key"] == "b-2"
    assert "b-1/story_1.mp3" not in fake.storage.buckets["media"]


def test_local_json_fallback_when_unconfigured(monkeypatch, tmp_path):
    monkeypatch.setattr(
        supabase_client,
        "get_settings",
        lambda: Settings(_env_file=None, SUPABASE_URL="", SUPABASE_SERVICE_ROLE_KEY=""),
    )
    monkeypatch.setattr(supabase_client, "get_data_dir", lambda: tmp_path)

    assert supabase_client.get_client() is None

    run_id = supabase_client.start_run()
    supabase_client.finish_run(run_id, status="success", stats={"offline": True})

    audio_src = tmp_path / "temp.mp3"
    audio_src.write_bytes(b"mp3data")
    local_url = supabase_client.upload_audio(audio_src, "b-local/story_1.mp3")
    assert local_url == "/media/b-local/story_1.mp3"
    assert (tmp_path / "media" / "b-local" / "story_1.mp3").exists()

    bulletin = _sample_bulletin("b-local")
    supabase_client.save_bulletin(bulletin, run_id=run_id)
    loaded = supabase_client.get_latest_ready_bulletin("ur")
    assert loaded is not None
    assert loaded.bulletin_id == "b-local"
    assert len(loaded.stories) == 2


def test_finish_run_rejects_invalid_status():
    fake = FakeSupabaseClient()
    with pytest.raises(ValueError, match="Invalid status"):
        supabase_client.finish_run("run-1", status="unknown", client=fake)
