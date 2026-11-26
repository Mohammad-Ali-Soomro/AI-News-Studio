-- AI News Studio: Initial Supabase Postgres Schema and RLS Policies
-- Storage note: Create a bucket named 'media' in Supabase Storage and mark it Public
-- (public read access; writes are performed only by the backend using the service role / secret key).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Raw ingested articles
CREATE TABLE IF NOT EXISTS public.articles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    publisher text NOT NULL,
    title text NOT NULL,
    url text NOT NULL UNIQUE,
    summary text,
    published_at text,
    fetched_at timestamptz NOT NULL DEFAULT now()
);

-- 2. Pipeline execution runs
CREATE TABLE IF NOT EXISTS public.pipeline_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'success', 'partial', 'failed')),
    stats jsonb NOT NULL DEFAULT '{}'::jsonb,
    error text
);

-- 3. Broadcast bulletins
CREATE TABLE IF NOT EXISTS public.bulletins (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bulletin_key text NOT NULL UNIQUE,
    title text NOT NULL,
    language text NOT NULL DEFAULT 'ur',
    status text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'ready', 'failed')),
    total_duration_sec numeric NOT NULL DEFAULT 0,
    model_name text,
    generated_at timestamptz NOT NULL DEFAULT now(),
    run_id uuid REFERENCES public.pipeline_runs(id) ON DELETE SET NULL
);

-- 4. Stories belonging to a bulletin
CREATE TABLE IF NOT EXISTS public.stories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bulletin_id uuid NOT NULL REFERENCES public.bulletins(id) ON DELETE CASCADE,
    position int NOT NULL,
    story_key text NOT NULL,
    category text NOT NULL,
    anchor text NOT NULL,
    headline text NOT NULL,
    ticker_text text NOT NULL,
    spoken_script text NOT NULL,
    insight jsonb NOT NULL DEFAULT '[]'::jsonb,
    source jsonb NOT NULL DEFAULT '{}'::jsonb,
    sources jsonb NOT NULL DEFAULT '[]'::jsonb,
    audio_path text,
    audio_url text,
    start_time_sec numeric NOT NULL DEFAULT 0,
    duration_sec numeric NOT NULL DEFAULT 0
);

-- Indexes for fast latest-bulletin lookup and ordered story retrieval
CREATE INDEX IF NOT EXISTS idx_bulletins_status_generated_at
    ON public.bulletins (status, generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_stories_bulletin_position
    ON public.stories (bulletin_id, position);

-- Row Level Security (RLS)
ALTER TABLE public.articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bulletins ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stories ENABLE ROW LEVEL SECURITY;

-- Public (anon) read-only access ONLY to ready bulletins and their stories.
-- No anon insert, update, or delete policies exist on any table.
-- The backend uses SUPABASE_SERVICE_ROLE_KEY (or sb_secret key), which bypasses RLS.
DROP POLICY IF EXISTS "Public read ready bulletins" ON public.bulletins;
CREATE POLICY "Public read ready bulletins"
    ON public.bulletins
    FOR SELECT
    TO anon
    USING (status = 'ready');

DROP POLICY IF EXISTS "Public read stories for ready bulletins" ON public.stories;
CREATE POLICY "Public read stories for ready bulletins"
    ON public.stories
    FOR SELECT
    TO anon
    USING (
        EXISTS (
            SELECT 1
            FROM public.bulletins b
            WHERE b.id = stories.bulletin_id
              AND b.status = 'ready'
        )
    );
