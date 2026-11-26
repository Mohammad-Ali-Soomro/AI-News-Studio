-- Explicit role privileges for Supabase Postgres tables created via SQL Editor
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON TABLE public.articles, public.pipeline_runs, public.bulletins, public.stories TO service_role;
GRANT SELECT ON TABLE public.bulletins, public.stories TO anon;
