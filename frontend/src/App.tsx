import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { AnchorStage } from "./components/studio/AnchorStage";
import { BroadcastHeader } from "./components/BroadcastHeader";
import { InsightPanel } from "./components/InsightPanel";
import { LiveTicker } from "./components/LiveTicker";
import { LowerThird } from "./components/LowerThird";
import { STUDIO_CONFIG } from "./config/studio";
import { useBroadcastTimeline } from "./hooks/useBroadcastTimeline";
import { fetchLatestBulletin, type BulletinLoadResult } from "./lib/api";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: BulletinLoadResult };

export function App() {
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });
  const [hasStarted, setHasStarted] = useState(false);

  const loadBulletin = useCallback(async () => {
    setLoadState({ status: "loading" });
    try {
      const result = await fetchLatestBulletin(STUDIO_CONFIG.defaultLanguage);
      setLoadState({ status: "ready", data: result });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load broadcast bulletin.";
      setLoadState({ status: "error", message });
    }
  }, []);

  useEffect(() => {
    void loadBulletin();
  }, [loadBulletin]);

  const bulletin = loadState.status === "ready" ? loadState.data.bulletin : null;
  const isDemoMode = loadState.status === "ready" ? loadState.data.isDemoMode : false;

  const timeline = useBroadcastTimeline(bulletin);

  const handleStartOrReplay = useCallback(() => {
    setHasStarted(true);
    void timeline.play();
  }, [timeline]);

  const handlePlayPause = useCallback(() => {
    if (!hasStarted) {
      setHasStarted(true);
    }
    if (timeline.isPlaying) {
      timeline.pause();
    } else {
      void timeline.play();
    }
  }, [hasStarted, timeline]);

  if (loadState.status === "loading") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-4 text-center">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-800 border-t-cyan-400" />
        <p className="mt-4 text-sm font-medium text-slate-300">
          Loading {STUDIO_CONFIG.channelName} bulletin...
        </p>
      </div>
    );
  }

  if (loadState.status === "error") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-4 text-center">
        <div className="max-w-md rounded-2xl border border-rose-500/30 bg-slate-900 p-6">
          <AlertTriangle className="mx-auto h-10 w-10 text-rose-400" />
          <h2 className="mt-3 text-lg font-bold text-white">
            Unable to load bulletin
          </h2>
          <p className="mt-2 text-sm text-slate-400">{loadState.message}</p>
          <button
            type="button"
            onClick={() => void loadBulletin()}
            className="mt-5 inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 pb-20 text-slate-100">
      <BroadcastHeader
        isPlaying={timeline.isPlaying}
        isDemoMode={isDemoMode}
        currentTime={timeline.currentTime}
        totalDuration={bulletin?.total_duration_sec ?? 0}
        activeIndex={timeline.activeIndex}
        totalStories={bulletin?.stories.length ?? 0}
        hasStarted={hasStarted}
        onPlayPause={handlePlayPause}
        onNext={timeline.next}
        onPrevious={timeline.previous}
        onSeek={timeline.seek}
      />

      <main className="mx-auto max-w-7xl space-y-5 px-4 py-5">
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <AnchorStage
              activeStory={timeline.activeStory}
              activeIndex={timeline.activeIndex}
              totalStories={bulletin?.stories.length ?? 0}
              isPlaying={timeline.isPlaying}
              hasStarted={hasStarted}
              ended={timeline.ended}
              audioElement={timeline.audioElement}
              onStartBroadcast={handleStartOrReplay}
            />
          </div>
          <div className="lg:col-span-4">
            <InsightPanel story={timeline.activeStory} />
          </div>
        </div>

        <LowerThird story={timeline.activeStory} />

        {/* Story selector strip for quick inspection */}
        {bulletin && bulletin.stories.length > 0 && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {bulletin.stories.map((story, idx) => {
              const isActive = idx === timeline.activeIndex;
              return (
                <button
                  key={story.story_id}
                  type="button"
                  onClick={() => {
                    setHasStarted(true);
                    timeline.seek(story.start_time_sec);
                  }}
                  dir="rtl"
                  className={`rounded-xl border px-4 py-3 text-right transition ${
                    isActive
                      ? "border-cyan-500/70 bg-cyan-500/10"
                      : "border-slate-800 bg-slate-900/60 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span>{story.source.publisher}</span>
                    <span>#{idx + 1}</span>
                  </div>
                  <p className="font-urdu mt-1 text-sm font-semibold text-slate-100 line-clamp-2">
                    {story.headline}
                  </p>
                </button>
              );
            })}
          </div>
        )}
      </main>

      <LiveTicker
        stories={bulletin?.stories ?? []}
        activeStory={timeline.activeStory}
      />
    </div>
  );
}

export default App;
