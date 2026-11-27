import type { StoryRundown } from "../types/bulletin";

export function clampTime(timeSec: number, totalDurationSec: number): number {
  if (!Number.isFinite(timeSec) || timeSec <= 0) {
    return 0;
  }
  if (!Number.isFinite(totalDurationSec) || totalDurationSec <= 0) {
    return 0;
  }
  return Math.min(timeSec, totalDurationSec);
}

/**
 * Determine the active story index for a global timeline timestamp (seconds).
 * During an inter-story gap, keeps the story whose start_time_sec was most recently reached
 * so UI cards and lower-thirds stay stable.
 */
export function findStoryIndexAtTime(stories: StoryRundown[], timeSec: number): number {
  if (stories.length === 0) {
    return -1;
  }
  const safeTime = Number.isFinite(timeSec) ? Math.max(0, timeSec) : 0;

  let candidateIndex = 0;
  for (let i = 0; i < stories.length; i += 1) {
    const story = stories[i];
    const end = story.start_time_sec + Math.max(0, story.duration_sec);
    if (safeTime >= story.start_time_sec && safeTime < end) {
      return i;
    }
    if (safeTime >= story.start_time_sec) {
      candidateIndex = i;
    }
  }
  return candidateIndex;
}

export function mapGlobalTimeToStoryPosition(
  stories: StoryRundown[],
  globalTimeSec: number
): { index: number; offsetSec: number } {
  const index = findStoryIndexAtTime(stories, globalTimeSec);
  if (index < 0) {
    return { index: -1, offsetSec: 0 };
  }
  const story = stories[index];
  const rawOffset = Math.max(0, globalTimeSec - story.start_time_sec);
  const offsetSec = Math.min(rawOffset, Math.max(0, story.duration_sec));
  return { index, offsetSec };
}

export function computeGlobalTime(
  stories: StoryRundown[],
  index: number,
  localTimeSec: number,
  totalDurationSec?: number
): number {
  if (index < 0 || index >= stories.length) {
    return 0;
  }
  const story = stories[index];
  const safeLocal = Number.isFinite(localTimeSec) ? Math.max(0, localTimeSec) : 0;
  const globalTime = story.start_time_sec + safeLocal;
  if (typeof totalDurationSec === "number" && totalDurationSec > 0) {
    return clampTime(globalTime, totalDurationSec);
  }
  return globalTime;
}

export function formatSeconds(sec: number): string {
  const safe = Number.isFinite(sec) && sec > 0 ? Math.floor(sec) : 0;
  const mins = Math.floor(safe / 60);
  const rem = safe % 60;
  return `${String(mins).padStart(2, "0")}:${String(rem).padStart(2, "0")}`;
}
