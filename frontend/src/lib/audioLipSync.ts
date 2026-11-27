import type { AnchorMotionConfig } from "../config/avatar";

export interface AudioAnalyserHandle {
  context: AudioContext;
  source: MediaElementAudioSourceNode;
  analyser: AnalyserNode;
  timeData: Uint8Array<ArrayBuffer>;
  freqData: Uint8Array<ArrayBuffer>;
}

export interface MouthWeights {
  aa: number;
  oh: number;
  ee: number;
  smoothedLoudness: number;
}

// Module-level WeakMap guarantees one MediaElementAudioSourceNode per HTMLAudioElement
// even across React StrictMode double mounts.
const analyserCache = new WeakMap<HTMLAudioElement, AudioAnalyserHandle>();

export function ensureAudioAnalyser(
  audioElement: HTMLAudioElement | null
): AudioAnalyserHandle | null {
  if (!audioElement || typeof window === "undefined") {
    return null;
  }

  const existing = analyserCache.get(audioElement);
  if (existing) {
    if (existing.context.state === "suspended") {
      void existing.context.resume().catch(() => undefined);
    }
    return existing;
  }

  const AudioCtx =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext })
      .webkitAudioContext;
  if (!AudioCtx) {
    return null;
  }

  try {
    const context = new AudioCtx();
    const source = context.createMediaElementSource(audioElement);
    const analyser = context.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.6;

    source.connect(analyser);
    analyser.connect(context.destination);

    const handle: AudioAnalyserHandle = {
      context,
      source,
      analyser,
      timeData: new Uint8Array(new ArrayBuffer(analyser.fftSize)),
      freqData: new Uint8Array(new ArrayBuffer(analyser.frequencyBinCount)),
    };
    analyserCache.set(audioElement, handle);
    if (context.state === "suspended") {
      void context.resume().catch(() => undefined);
    }
    return handle;
  } catch {
    return null;
  }
}

function clamp01(val: number): number {
  return Math.max(0, Math.min(1, val));
}

export function computeMouthShapes(
  timeData: Uint8Array,
  freqData: Uint8Array,
  prevSmoothed: number,
  config: Pick<AnchorMotionConfig, "mouthGain" | "smoothing" | "noiseFloor">,
  isPlaying: boolean
): MouthWeights {
  if (!isPlaying || timeData.length === 0) {
    const decayed = prevSmoothed * 0.65;
    if (decayed < 0.01) {
      return { aa: 0, oh: 0, ee: 0, smoothedLoudness: 0 };
    }
    return {
      aa: decayed * 0.7,
      oh: decayed * 0.15,
      ee: decayed * 0.1,
      smoothedLoudness: decayed,
    };
  }

  let sumSq = 0;
  for (let i = 0; i < timeData.length; i += 1) {
    const centered = (timeData[i] - 128) / 128;
    sumSq += centered * centered;
  }
  const rms = Math.sqrt(sumSq / timeData.length);
  const gated = Math.max(0, rms - config.noiseFloor);
  const target = clamp01(gated * config.mouthGain);

  const alpha = clamp01(config.smoothing);
  const smoothed = prevSmoothed * alpha + target * (1 - alpha);

  if (smoothed < 0.015) {
    return { aa: 0, oh: 0, ee: 0, smoothedLoudness: 0 };
  }

  // Cheap spectral band ratio: low-mid energy vs high-mid energy
  let lowMid = 0;
  let highMid = 0;
  const split = Math.max(2, Math.floor(freqData.length * 0.25));
  const upperLimit = Math.max(split + 1, Math.floor(freqData.length * 0.65));
  for (let i = 1; i < freqData.length; i += 1) {
    if (i < split) {
      lowMid += freqData[i];
    } else if (i < upperLimit) {
      highMid += freqData[i];
    }
  }
  const ratio = highMid / (lowMid + highMid + 1);

  const aa = clamp01(smoothed * (0.72 + (1 - ratio) * 0.28));
  const oh = clamp01(smoothed * Math.max(0, 0.35 - ratio * 0.45));
  const ee = clamp01(smoothed * Math.max(0, ratio * 0.65));

  return { aa, oh, ee, smoothedLoudness: smoothed };
}
