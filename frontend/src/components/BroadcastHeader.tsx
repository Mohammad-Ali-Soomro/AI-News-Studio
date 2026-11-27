import { useEffect, useState } from "react";
import { Pause, Play, Radio, SkipBack, SkipForward } from "lucide-react";
import { STUDIO_CONFIG } from "../config/studio";
import { formatSeconds } from "../lib/timeline";

interface BroadcastHeaderProps {
  isPlaying: boolean;
  isDemoMode: boolean;
  currentTime: number;
  totalDuration: number;
  activeIndex: number;
  totalStories: number;
  hasStarted: boolean;
  onPlayPause: () => void;
  onNext: () => void;
  onPrevious: () => void;
  onSeek: (timeSec: number) => void;
}

function formatPakistanClock(date: Date): { time: string; date: string } {
  const time = new Intl.DateTimeFormat("en-PK", {
    timeZone: "Asia/Karachi",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  }).format(date);

  const day = new Intl.DateTimeFormat("en-PK", {
    timeZone: "Asia/Karachi",
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);

  return { time, date: day };
}

export function BroadcastHeader({
  isPlaying,
  isDemoMode,
  currentTime,
  totalDuration,
  activeIndex,
  totalStories,
  hasStarted,
  onPlayPause,
  onNext,
  onPrevious,
  onSeek,
}: BroadcastHeaderProps) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const pk = formatPakistanClock(now);
  const maxDuration = totalDuration > 0 ? totalDuration : 1;

  return (
    <header className="border-b border-slate-800/80 bg-slate-950/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        {/* Left: Channel identity & LIVE badge */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-emerald-500 text-slate-950 shadow-lg shadow-cyan-500/20">
            <Radio className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-base font-bold tracking-wide text-white sm:text-lg">
                {STUDIO_CONFIG.channelName}
              </h1>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-500/40 bg-rose-500/15 px-2.5 py-0.5 text-[11px] font-semibold tracking-wider text-rose-300">
                <span
                  className={`h-2 w-2 rounded-full bg-rose-500 ${
                    isPlaying ? "animate-pulse" : ""
                  }`}
                />
                LIVE
              </span>
              {isDemoMode && (
                <span className="rounded-full border border-amber-500/40 bg-amber-500/15 px-2 py-0.5 text-[11px] font-medium text-amber-300">
                  DEMO
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              {pk.date} | {pk.time} PKT
            </p>
          </div>
        </div>

        {/* Center/Right: Transport controls & timeline scrubber */}
        <div className="flex flex-1 flex-wrap items-center justify-end gap-3 sm:max-w-md">
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={onPrevious}
              disabled={!hasStarted || activeIndex <= 0}
              aria-label="Previous story"
              className="rounded-lg border border-slate-700/80 bg-slate-900 p-2 text-slate-200 transition hover:border-cyan-500/60 hover:text-cyan-300 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <SkipBack className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={onPlayPause}
              aria-label={isPlaying ? "Pause broadcast" : "Play broadcast"}
              className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-500 px-3.5 py-2 text-xs font-semibold text-slate-950 transition hover:bg-cyan-400"
            >
              {isPlaying ? (
                <>
                  <Pause className="h-4 w-4" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Play
                </>
              )}
            </button>
            <button
              type="button"
              onClick={onNext}
              disabled={!hasStarted || activeIndex >= totalStories - 1}
              aria-label="Next story"
              className="rounded-lg border border-slate-700/80 bg-slate-900 p-2 text-slate-200 transition hover:border-cyan-500/60 hover:text-cyan-300 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <SkipForward className="h-4 w-4" />
            </button>
          </div>

          <div className="flex min-w-[160px] flex-1 items-center gap-2 text-xs text-slate-400">
            <span className="tabular-nums">{formatSeconds(currentTime)}</span>
            <input
              type="range"
              min={0}
              max={maxDuration}
              step={0.1}
              value={Math.min(currentTime, maxDuration)}
              onChange={(e) => onSeek(Number(e.target.value))}
              aria-label="Broadcast progress"
              className="h-1.5 w-full cursor-pointer accent-cyan-400"
            />
            <span className="tabular-nums">{formatSeconds(totalDuration)}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
