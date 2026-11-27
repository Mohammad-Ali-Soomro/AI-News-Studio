import { useCallback, useEffect, useRef, useState } from "react";
import { STUDIO_CONFIG } from "../config/studio";
import {
  computeGlobalTime,
  findStoryIndexAtTime,
  mapGlobalTimeToStoryPosition,
} from "../lib/timeline";
import type { Bulletin, StoryRundown } from "../types/bulletin";

export interface BroadcastTimelineState {
  activeStory: StoryRundown | null;
  activeIndex: number;
  currentTime: number;
  isPlaying: boolean;
  ended: boolean;
  audioElement: HTMLAudioElement | null;
  play: () => Promise<void>;
  pause: () => void;
  next: () => void;
  previous: () => void;
  seek: (globalTimeSec: number) => void;
}

export function useBroadcastTimeline(bulletin: Bulletin | null): BroadcastTimelineState {
  const stories = bulletin?.stories ?? [];
  const totalDuration = bulletin?.total_duration_sec ?? 0;

  const [activeIndex, setActiveIndex] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [ended, setEnded] = useState(false);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const gapTimerRef = useRef<number | null>(null);
  const activeIndexRef = useRef(0);
  const isPlayingRef = useRef(false);
  const pendingSeekOffsetRef = useRef<number | null>(null);
  const loadedSrcRef = useRef<string>("");

  activeIndexRef.current = activeIndex;
  isPlayingRef.current = isPlaying;

  const clearGapTimer = useCallback(() => {
    if (gapTimerRef.current !== null) {
      window.clearTimeout(gapTimerRef.current);
      gapTimerRef.current = null;
    }
  }, []);

  // Create one persistent HTMLAudioElement so Web Audio AnalyserNode (Phase 7) can attach once.
  useEffect(() => {
    const audio = new Audio();
    audio.crossOrigin = "anonymous";
    audio.preload = "auto";
    audioRef.current = audio;
    setAudioElement(audio);

    return () => {
      clearGapTimer();
      audio.pause();
      audio.src = "";
      audioRef.current = null;
      setAudioElement(null);
    };
  }, [clearGapTimer]);

  // Reset timeline when a new bulletin loads
  useEffect(() => {
    clearGapTimer();
    setActiveIndex(0);
    setCurrentTime(0);
    setIsPlaying(false);
    setEnded(false);
    loadedSrcRef.current = "";
    pendingSeekOffsetRef.current = null;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.removeAttribute("src");
      audioRef.current.load();
    }
  }, [bulletin?.bulletin_id, clearGapTimer]);

  const loadAndPlayIndex = useCallback(
    async (index: number, offsetSec = 0, autoPlay = true) => {
      const audio = audioRef.current;
      if (!audio || index < 0 || index >= stories.length) {
        return;
      }
      const story = stories[index];
      const src = story.audio_url ?? "";
      setActiveIndex(index);
      setEnded(false);
      setCurrentTime(computeGlobalTime(stories, index, offsetSec, totalDuration));

      if (!src) {
        setIsPlaying(false);
        return;
      }

      if (loadedSrcRef.current !== src) {
        pendingSeekOffsetRef.current = offsetSec;
        loadedSrcRef.current = src;
        audio.src = src;
        audio.load();
      } else {
        audio.currentTime = offsetSec;
      }

      if (autoPlay) {
        try {
          await audio.play();
          setIsPlaying(true);
        } catch {
          setIsPlaying(false);
        }
      }
    },
    [stories, totalDuration]
  );

  // Wire HTMLAudioElement events
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) {
      return;
    }

    const onLoadedMetadata = () => {
      if (pendingSeekOffsetRef.current !== null) {
        audio.currentTime = pendingSeekOffsetRef.current;
        pendingSeekOffsetRef.current = null;
      }
    };

    const onTimeUpdate = () => {
      const idx = activeIndexRef.current;
      const globalSec = computeGlobalTime(stories, idx, audio.currentTime, totalDuration);
      setCurrentTime(globalSec);
    };

    const onEnded = () => {
      const idx = activeIndexRef.current;
      if (idx + 1 < stories.length) {
        clearGapTimer();
        gapTimerRef.current = window.setTimeout(() => {
          void loadAndPlayIndex(idx + 1, 0, true);
        }, STUDIO_CONFIG.storyGapMs);
      } else {
        setIsPlaying(false);
        setEnded(true);
        setCurrentTime(totalDuration);
      }
    };

    const onError = () => {
      const idx = activeIndexRef.current;
      if (isPlayingRef.current && idx + 1 < stories.length) {
        void loadAndPlayIndex(idx + 1, 0, true);
      } else {
        setIsPlaying(false);
      }
    };

    audio.addEventListener("loadedmetadata", onLoadedMetadata);
    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("ended", onEnded);
    audio.addEventListener("error", onError);

    return () => {
      audio.removeEventListener("loadedmetadata", onLoadedMetadata);
      audio.removeEventListener("timeupdate", onTimeUpdate);
      audio.removeEventListener("ended", onEnded);
      audio.removeEventListener("error", onError);
    };
  }, [clearGapTimer, loadAndPlayIndex, stories, totalDuration]);

  const play = useCallback(async () => {
    if (stories.length === 0) {
      return;
    }
    clearGapTimer();
    if (ended) {
      await loadAndPlayIndex(0, 0, true);
      return;
    }
    const audio = audioRef.current;
    if (!audio) {
      return;
    }
    const currentStory = stories[activeIndexRef.current];
    if (!loadedSrcRef.current && currentStory?.audio_url) {
      await loadAndPlayIndex(activeIndexRef.current, 0, true);
      return;
    }
    try {
      await audio.play();
      setIsPlaying(true);
    } catch {
      setIsPlaying(false);
    }
  }, [clearGapTimer, ended, loadAndPlayIndex, stories]);

  const pause = useCallback(() => {
    clearGapTimer();
    audioRef.current?.pause();
    setIsPlaying(false);
  }, [clearGapTimer]);

  const next = useCallback(() => {
    if (stories.length === 0) {
      return;
    }
    clearGapTimer();
    const nextIdx = Math.min(stories.length - 1, activeIndexRef.current + 1);
    void loadAndPlayIndex(nextIdx, 0, isPlayingRef.current);
  }, [clearGapTimer, loadAndPlayIndex, stories.length]);

  const previous = useCallback(() => {
    if (stories.length === 0) {
      return;
    }
    clearGapTimer();
    const prevIdx = Math.max(0, activeIndexRef.current - 1);
    void loadAndPlayIndex(prevIdx, 0, isPlayingRef.current);
  }, [clearGapTimer, loadAndPlayIndex, stories.length]);

  const seek = useCallback(
    (globalTimeSec: number) => {
      if (stories.length === 0) {
        return;
      }
      clearGapTimer();
      const { index, offsetSec } = mapGlobalTimeToStoryPosition(stories, globalTimeSec);
      if (index < 0) {
        return;
      }
      void loadAndPlayIndex(index, offsetSec, isPlayingRef.current);
    },
    [clearGapTimer, loadAndPlayIndex, stories]
  );

  // Derive activeStory from currentTime/activeIndex consistently
  const derivedIndex =
    stories.length === 0
      ? -1
      : activeIndex >= 0 && activeIndex < stories.length
      ? activeIndex
      : findStoryIndexAtTime(stories, currentTime);
  const activeStory = derivedIndex >= 0 ? stories[derivedIndex] : null;

  return {
    activeStory,
    activeIndex: derivedIndex,
    currentTime,
    isPlaying,
    ended,
    audioElement,
    play,
    pause,
    next,
    previous,
    seek,
  };
}
