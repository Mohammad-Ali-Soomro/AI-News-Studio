import { describe, expect, it } from "vitest";
import {
  clampTime,
  computeGlobalTime,
  findStoryIndexAtTime,
  formatSeconds,
  mapGlobalTimeToStoryPosition,
} from "./timeline";
import type { StoryRundown } from "../types/bulletin";

function makeStory(story_id: string, start_time_sec: number, duration_sec: number): StoryRundown {
  return {
    story_id,
    category: "National",
    anchor: "Anchor_A",
    language: "ur",
    spoken_script: "خبر",
    headline: "عنوان",
    ticker_text: "ٹکر",
    source: {
      title: "Title",
      publisher: "Dawn",
      source_url: "https://dawn.com/1",
    },
    insight_panel: [
      { key: "ک", value: "و" },
      { key: "م", value: "ق" },
      { key: "ن", value: "ز" },
    ],
    start_time_sec,
    duration_sec,
    audio_url: `/demo/audio/${story_id}.mp3`,
  };
}

const sampleStories: StoryRundown[] = [
  makeStory("story_1", 0.0, 19.752),
  makeStory("story_2", 20.352, 16.176),
  makeStory("story_4", 37.128, 15.456),
];

describe("timeline helpers", () => {
  it("finds active story index within each story window", () => {
    expect(findStoryIndexAtTime(sampleStories, 0)).toBe(0);
    expect(findStoryIndexAtTime(sampleStories, 10.5)).toBe(0);
    expect(findStoryIndexAtTime(sampleStories, 20.352)).toBe(1);
    expect(findStoryIndexAtTime(sampleStories, 30.0)).toBe(1);
    expect(findStoryIndexAtTime(sampleStories, 40.0)).toBe(2);
  });

  it("keeps previous story active during the 0.6s inter-story gap", () => {
    expect(findStoryIndexAtTime(sampleStories, 19.9)).toBe(0);
    expect(findStoryIndexAtTime(sampleStories, 36.8)).toBe(1);
  });

  it("handles empty story arrays safely", () => {
    expect(findStoryIndexAtTime([], 5)).toBe(-1);
    expect(mapGlobalTimeToStoryPosition([], 5)).toEqual({ index: -1, offsetSec: 0 });
    expect(computeGlobalTime([], 0, 3)).toBe(0);
  });

  it("maps global seek timestamp into story index and local audio offset", () => {
    const pos = mapGlobalTimeToStoryPosition(sampleStories, 25.352);
    expect(pos.index).toBe(1);
    expect(pos.offsetSec).toBeCloseTo(5.0, 3);

    const endPos = mapGlobalTimeToStoryPosition(sampleStories, 999);
    expect(endPos.index).toBe(2);
    expect(endPos.offsetSec).toBeCloseTo(15.456, 3);
  });

  it("computes global time clamped to bulletin total duration", () => {
    expect(computeGlobalTime(sampleStories, 1, 4.0, 52.584)).toBeCloseTo(24.352, 3);
    expect(computeGlobalTime(sampleStories, 2, 20.0, 52.584)).toBeCloseTo(52.584, 3);
    expect(clampTime(-5, 50)).toBe(0);
  });

  it("formats seconds as mm:ss", () => {
    expect(formatSeconds(0)).toBe("00:00");
    expect(formatSeconds(66.9)).toBe("01:06");
  });
});
