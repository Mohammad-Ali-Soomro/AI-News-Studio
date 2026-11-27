export interface AnchorMotionConfig {
  mouthGain: number;
  smoothing: number;
  swayAmount: number;
  noiseFloor: number;
  blinkIntervalMinSec: number;
  blinkIntervalMaxSec: number;
  blinkDurationSec: number;
  nodDurationSec: number;
  nodAmplitudeRad: number;
}

export const ANCHOR_MOTION_CONFIG: AnchorMotionConfig = {
  mouthGain: 2.6,
  smoothing: 0.45,
  swayAmount: 1.0,
  noiseFloor: 0.018,
  blinkIntervalMinSec: 2.4,
  blinkIntervalMaxSec: 5.2,
  blinkDurationSec: 0.16,
  nodDurationSec: 0.65,
  nodAmplitudeRad: 0.06,
};

export const MODEL_CANDIDATES = [
  { url: "/models/anchor.glb", kind: "glb" as const },
  { url: "/models/anchor.vrm", kind: "vrm" as const },
];
