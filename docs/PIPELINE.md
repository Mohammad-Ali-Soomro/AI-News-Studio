# AI News Studio Pipeline Architecture

This document describes the end-to-end batch job implemented in `backend/app/jobs/run_pipeline.py` and the FastAPI endpoints in `backend/app/main.py`.

## Flow Diagram

```text
[1. start_run]
      |
      v
[2. collect] ------------> Dawn + Express Tribune RSS (10s timeout + body scrape fallback)
      |
      v
[3. save_articles] ------> Upsert into Supabase `articles` (skipped in --dry-run)
      |
      v
[4. deduplicate] --------> TF-IDF + cosine similarity story clustering
      |
      v
[5. select_top_clusters] -> Prefer multi-publisher clusters, then newest timestamp (top N)
      |
      v
[6. script_generation] --> Single Gemini structured JSON call + Urdu/faithfulness validators
      |                     (retries failed story once; drops unvalidated; stale backup on outage)
      v
[7. tts_upload] ---------> edge-tts (ur-PK-UzmaNeural) + mutagen durations + 0.6s gap timeline
      |                     -> upload MP3s to Supabase `media` bucket (skipped in --dry-run)
      v
[8. save_bulletin] ------> Draft upsert -> replace stories -> mark status='ready'
      |
      v
[9. prune_old_bulletins] -> Keep newest 10 bulletins and delete older audio files
      |
      v
[10. finish_run] ---------> Record status ('success', 'partial', or 'failed') + stage timings
```

## CLI Usage

Run from the repository root:

```powershell
# Full run (writes to Supabase Postgres and Storage)
python -m backend.app.jobs.run_pipeline --stories 4

# Dry run (runs collection, Gemini, and TTS locally without touching Supabase)
python -m backend.app.jobs.run_pipeline --stories 4 --dry-run
```

## Failure Handling

- **Single-feed outage:** `collector.py` isolates each feed so one failed URL does not block the other feed.
- **Single-story script/TTS failure:** Invalid scripts are retried once and dropped if still invalid; permanent TTS failures skip only that story. The run is recorded as `partial` when any story is dropped or the stale backup is used.
- **Pipeline exception:** Any fatal failure calls `finish_run(run_id, status="failed", stats=stats, error=...)` and exits with status code `1`.

## FastAPI Endpoints

- `GET /api/v1/bulletin/latest?language=ur`: Reads the latest `ready` bulletin from Supabase (or `local_json` fallback). Never generates on request.
- `POST /api/v1/pipeline/run?stories=4`: Creates a `running` row in `pipeline_runs`, schedules `run_pipeline` in a background task, and returns `{ "run_id": "...", "status": "running" }`.
- `GET /api/v1/pipeline/runs?limit=10`: Lists recent pipeline runs with status, timestamps, stats, and any errors.
