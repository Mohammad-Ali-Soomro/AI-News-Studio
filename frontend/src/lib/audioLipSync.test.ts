import { describe, expect, it } from "vitest";
import { ANCHOR_MOTION_CONFIG } from "../config/avatar";
import { computeMouthShapes } from "./audioLipSync";

describe("computeMouthShapes", () => {
  it("closes mouth toward zero when paused or silent", () => {
    const silentTime = new Uint8Array(256).fill(128);
    const silentFreq = new Uint8Array(128).fill(0);

    const paused = computeMouthShapes(
      silentTime,
      silentFreq,
      0.005,
      ANCHOR_MOTION_CONFIG,
      false
    );
    expect(paused.aa).toBe(0);
    expect(paused.oh).toBe(0);
    expect(paused.ee).toBe(0);

    const silentPlaying = computeMouthShapes(
      silentTime,
      silentFreq,
      0,
      ANCHOR_MOTION_CONFIG,
      true
    );
    expect(silentPlaying.aa).toBe(0);
  });

  it("opens mouth proportionally with spectral variation when audio is active", () => {
    const activeTime = new Uint8Array(256);
    for (let i = 0; i < activeTime.length; i += 1) {
      activeTime[i] = i % 2 === 0 ? 190 : 66;
    }
    const lowRichFreq = new Uint8Array(128).fill(10);
    for (let i = 1; i < 16; i += 1) {
      lowRichFreq[i] = 200;
    }

    const lowRes = computeMouthShapes(
      activeTime,
      lowRichFreq,
      0,
      ANCHOR_MOTION_CONFIG,
      true
    );
    expect(lowRes.aa).toBeGreaterThan(0.25);
    expect(lowRes.oh).toBeGreaterThan(0);

    const highRichFreq = new Uint8Array(128).fill(10);
    for (let i = 32; i < 75; i += 1) {
      highRichFreq[i] = 220;
    }
    const highRes = computeMouthShapes(
      activeTime,
      highRichFreq,
      0,
      ANCHOR_MOTION_CONFIG,
      true
    );
    expect(highRes.ee).toBeGreaterThan(lowRes.ee);
  });
});
