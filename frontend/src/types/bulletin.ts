export interface SourceArticle {
  title: string;
  publisher: string;
  source_url: string;
  published_at?: string | null;
  summary?: string | null;
}

export interface InsightFact {
  key: string;
  value: string;
}

export interface StoryRundown {
  story_id: string;
  category: string;
  anchor: string;
  language: string;

  // Broadcast scripts
  spoken_script: string;
  headline: string;
  ticker_text: string;

  // Media and presentation assets
  source: SourceArticle;
  insight_panel: InsightFact[];
  image_url?: string | null;

  // Timing contract (Generated after TTS/video synthesis)
  start_time_sec: number;
  duration_sec: number;
  audio_url?: string | null;
  video_url?: string | null;
}

export interface Bulletin {
  bulletin_id: string;
  title: string;
  generated_at: string;
  language: string;
  total_duration_sec: number;
  stories: StoryRundown[];
}
