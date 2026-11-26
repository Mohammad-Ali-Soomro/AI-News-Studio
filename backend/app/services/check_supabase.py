"""
Verification script for Supabase connectivity, RLS-bypassing backend writes,
and Storage uploads into the public 'media' bucket.

Usage:
    python -m backend.app.services.check_supabase
"""

from pathlib import Path
import sys
import tempfile
import uuid

from backend.app.services.supabase_client import (
    MEDIA_BUCKET,
    finish_run,
    get_client,
    is_supabase_configured,
    start_run,
    upload_audio,
)


def main() -> int:
    if not is_supabase_configured():
        print(
            "ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in backend/.env."
        )
        return 1

    client = get_client()
    assert client is not None

    run_id = None
    remote_path = f"checks/check_{uuid.uuid4().hex[:8]}.txt"
    tmp_file = None

    try:
        print("1. Inserting test row into pipeline_runs...")
        run_id = start_run(client=client)
        finish_run(run_id, status="success", stats={"check": True}, client=client)

        read_back = (
            client.table("pipeline_runs")
            .select("id, status, stats")
            .eq("id", run_id)
            .execute()
        )
        if not read_back.data:
            print("ERROR: Could not read back inserted pipeline_runs row.")
            return 1
        print(f"   Read back row id={run_id}, status={read_back.data[0]['status']}")

        print(f"2. Uploading tiny text file to bucket '{MEDIA_BUCKET}'...")
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".txt", delete=False
        ) as handle:
            handle.write(b"ai-news-studio-supabase-check\n")
            tmp_file = Path(handle.name)

        public_url = upload_audio(tmp_file, remote_path, client=client)
        print(f"   Public URL: {public_url}")

        print("3. Cleaning up test artifacts...")
        client.storage.from_(MEDIA_BUCKET).remove([remote_path])
        client.table("pipeline_runs").delete().eq("id", run_id).execute()
        run_id = None
        print("SUCCESS: Supabase database and media storage check passed.")
        return 0
    except Exception as exc:
        print(f"ERROR: Supabase check failed: {exc}")
        return 1
    finally:
        if tmp_file is not None:
            tmp_file.unlink(missing_ok=True)
        if run_id is not None:
            try:
                client.table("pipeline_runs").delete().eq("id", run_id).execute()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
