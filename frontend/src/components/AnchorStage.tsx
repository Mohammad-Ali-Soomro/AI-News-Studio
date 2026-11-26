import { Mic, RotateCcw, Volume2 } from "lucide-react";
import type { StoryRundown } from "../types/bulletin";

interface AnchorStageProps {
  activeStory: StoryRundown | null;
  activeIndex: number;
  totalStories: number;
  isPlaying: boolean;
  hasStarted: boolean;
  ended: boolean;
  onStartBroadcast: () => void;
}

export function AnchorStage({
  activeStory,
  activeIndex,
  totalStories,
  isPlaying,
  hasStarted,
  ended,
  onStartBroadcast,
}: AnchorStageProps) {
  return (
    <section className="relative flex min-h-[340px] flex-col justify-between overflow-hidden rounded-2xl border border-slate-800/90 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 p-5 shadow-2xl sm:min-h-[420px]">
      {/* Subtle studio backdrop grid & glow */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,rgba(6,182,212,0.16),transparent_60%)]" />

      {/* Top HUD bar inside stage */}
      <div className="relative z-10 flex items-center justify-between gap-2">
        <span className="rounded-md border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-cyan-300">
          {activeStory?.category ?? "Bulletin"}
        </span>
        <span className="rounded-md border border-slate-700/80 bg-slate-900/80 px-2.5 py-1 text-xs text-slate-300">
          Story {totalStories > 0 ? activeIndex + 1 : 0} of {totalStories}
        </span>
      </div>

      {/* Center placeholder where 3D VRM anchor will live in Phase 7 */}
      <div className="relative z-10 my-auto flex flex-col items-center justify-center py-6 text-center">
        <div
          className={`mb-4 flex h-24 w-24 items-center justify-center rounded-full border-2 transition-all duration-300 ${
            isPlaying
              ? "border-cyan-400 bg-cyan-500/15 shadow-[0_0_35px_rgba(34,211,238,0.35)]"
              : "border-slate-700 bg-slate-900/90"
          }`}
        >
          {isPlaying ? (
            <Volume2 className="h-10 w-10 animate-pulse text-cyan-300" />
          ) : (
            <Mic className="h-10 w-10 text-slate-400" />
          )}
        </div>

        <p className="text-xs font-semibold uppercase tracking-widest text-cyan-400">
          3D Anchor Stage (Phase 7 Ready)
        </p>
        <h2 className="mt-1 text-xl font-bold text-white">
          {activeStory?.anchor === "Anchor_A" ? "Uzma (Anchor A)" : activeStory?.anchor ?? "Anchor"}
        </h2>
        <p className="mt-2 max-w-md text-xs text-slate-400">
          {isPlaying
            ? "Speaking Urdu bulletin audio in real time"
            : ended
            ? "Bulletin complete. Click below to replay."
            : "Press Start Broadcast to begin Urdu audio playback."}
        </p>

        {/* Browser autoplay start overlay */}
        {(!hasStarted || ended) && (
          <button
            type="button"
            onClick={onStartBroadcast}
            className="mt-6 inline-flex items-center gap-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 px-6 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-500/25 transition hover:brightness-110"
          >
            {ended ? (
              <>
                <RotateCcw className="h-4 w-4" />
                Replay Broadcast
              </>
            ) : (
              <>
                <PlayIcon />
                <span>Start Broadcast</span>
                <span dir="rtl" className="font-urdu text-sm font-semibold leading-normal">
                  نشریات شروع کریں
                </span>
              </>
            )}
          </button>
        )}
      </div>

      {/* Desk edge bar */}
      <div className="relative z-10 h-1.5 w-full rounded-full bg-gradient-to-r from-transparent via-cyan-500/60 to-transparent" />
    </section>
  );
}

function PlayIcon() {
  return (
    <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}
