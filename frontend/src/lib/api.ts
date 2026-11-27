import { getSupabaseClient } from "./supabase";
import type { Bulletin, InsightFact, SourceArticle, StoryRundown } from "../types/bulletin";

export interface BulletinLoadResult {
  bulletin: Bulletin;
  isDemoMode: boolean;
  fallbackReason?: string;
}

interface SupabaseBulletinRow {
  id: string;
  bulletin_key: string;
  title: string;
  language: string;
  total_duration_sec: number | string | null;
  generated_at: string;
}

interface SupabaseStoryRow {
  story_key: string;
  category: string;
  anchor: string;
  headline: string;
  ticker_text: string;
  spoken_script: string;
  insight: InsightFact[] | null;
  source: SourceArticle | null;
  audio_url: string | null;
  start_time_sec: number | string | null;
  duration_sec: number | string | null;
}

export async function loadDemoBulletin(fallbackReason?: string): Promise<BulletinLoadResult> {
  const response = await fetch("/demo/bulletin.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Demo bulletin fetch failed with status ${response.status}`);
  }
  const bulletin = (await response.json()) as Bulletin;
  if (!bulletin.stories || bulletin.stories.length === 0) {
    throw new Error("Demo bulletin contains no stories.");
  }
  return {
    bulletin,
    isDemoMode: true,
    fallbackReason,
  };
}

export async function fetchLatestBulletin(language = "ur"): Promise<BulletinLoadResult> {
  const demoForced = String(import.meta.env.VITE_DEMO_MODE ?? "").toLowerCase() === "true";
  if (demoForced) {
    return loadDemoBulletin("VITE_DEMO_MODE=true");
  }

  const client = getSupabaseClient();
  if (!client) {
    return loadDemoBulletin("Supabase environment variables are not configured.");
  }

  try {
    const { data: bulletinRows, error: bulletinError } = await client
      .from("bulletins")
      .select("id, bulletin_key, title, language, total_duration_sec, generated_at")
      .eq("language", language)
      .eq("status", "ready")
      .order("generated_at", { ascending: false })
      .limit(1);

    if (bulletinError) {
      throw new Error(bulletinError.message);
    }
    if (!bulletinRows || bulletinRows.length === 0) {
      throw new Error("No ready bulletin found in Supabase.");
    }

    const row = bulletinRows[0] as SupabaseBulletinRow;
    const { data: storyRows, error: storiesError } = await client
      .from("stories")
      .select(
        "story_key, category, anchor, headline, ticker_text, spoken_script, insight, source, audio_url, start_time_sec, duration_sec"
      )
      .eq("bulletin_id", row.id)
      .order("position", { ascending: true });

    if (storiesError) {
      throw new Error(storiesError.message);
    }

    const mappedStories: StoryRundown[] = ((storyRows ?? []) as SupabaseStoryRow[]).map((s) => ({
      story_id: s.story_key,
      category: s.category,
      anchor: s.anchor,
      language: row.language,
      spoken_script: s.spoken_script,
      headline: s.headline,
      ticker_text: s.ticker_text,
      source: s.source ?? {
        title: s.headline,
        publisher: "Dawn",
        source_url: "",
      },
      insight_panel: Array.isArray(s.insight) ? s.insight : [],
      start_time_sec: Number(s.start_time_sec ?? 0),
      duration_sec: Number(s.duration_sec ?? 0),
      audio_url: s.audio_url ?? null,
    }));

    if (mappedStories.length === 0) {
      throw new Error("Latest bulletin has zero stories.");
    }

    return {
      bulletin: {
        bulletin_id: row.bulletin_key,
        title: row.title,
        generated_at: row.generated_at,
        language: row.language,
        total_duration_sec: Number(row.total_duration_sec ?? 0),
        stories: mappedStories,
      },
      isDemoMode: false,
    };
  } catch (err) {
    const reason = err instanceof Error ? err.message : "Unknown Supabase error";
    return loadDemoBulletin(reason);
  }
}
