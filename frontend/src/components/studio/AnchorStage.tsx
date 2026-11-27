import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { VRM, VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";
import { Mic, RotateCcw, SlidersHorizontal, Volume2 } from "lucide-react";
import {
  ANCHOR_MOTION_CONFIG,
  MODEL_CANDIDATES,
  type AnchorMotionConfig,
} from "../../config/avatar";
import { STUDIO_CONFIG } from "../../config/studio";
import {
  computeMouthShapes,
  ensureAudioAnalyser,
  type AudioAnalyserHandle,
} from "../../lib/audioLipSync";
import type { StoryRundown } from "../../types/bulletin";

interface AnchorStageProps {
  activeStory: StoryRundown | null;
  activeIndex: number;
  totalStories: number;
  isPlaying: boolean;
  hasStarted: boolean;
  ended: boolean;
  audioElement: HTMLAudioElement | null;
  onStartBroadcast: () => void;
}

type ModelStatus =
  | { state: "loading" }
  | { state: "ready"; format: "GLB" | "VRM" }
  | { state: "fallback"; reason: string };

interface MorphTargetBinding {
  mesh: THREE.Mesh;
  dict: Record<string, number>;
}

interface RigBones {
  head?: THREE.Object3D;
  neck?: THREE.Object3D;
  spine?: THREE.Object3D;
  headBaseRotX: number;
  headBaseRotY: number;
  spineBaseRotZ: number;
}

function createBackdropTexture(): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = 1024;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");

  if (ctx) {
    const grad = ctx.createLinearGradient(0, 0, 1024, 512);
    grad.addColorStop(0, "#050b18");
    grad.addColorStop(0.5, "#0b1930");
    grad.addColorStop(1, "#040914");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 1024, 512);

    ctx.strokeStyle = "rgba(34, 211, 238, 0.14)";
    ctx.lineWidth = 1;
    for (let x = 0; x <= 1024; x += 64) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, 512);
      ctx.stroke();
    }
    for (let y = 0; y <= 512; y += 64) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(1024, y);
      ctx.stroke();
    }

    ctx.fillStyle = "rgba(34, 211, 238, 0.12)";
    ctx.beginPath();
    ctx.arc(512, 240, 160, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "rgba(226, 232, 240, 0.78)";
    ctx.font = "bold 46px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(STUDIO_CONFIG.channelName.toUpperCase(), 512, 240);

    ctx.fillStyle = "rgba(16, 185, 129, 0.85)";
    ctx.font = "600 20px Inter, sans-serif";
    ctx.fillText("LIVE STUDIO BROADCAST", 512, 278);
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

async function checkModelExists(url: string): Promise<boolean> {
  try {
    const res = await fetch(url, { method: "HEAD", cache: "no-store" });
    if (!res.ok) {
      return false;
    }
    const contentType = res.headers.get("content-type") ?? "";
    // Avoid Vite SPA HTML fallback masquerading as a 200 OK binary file
    if (contentType.toLowerCase().includes("text/html")) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

function collectMorphBindings(root: THREE.Object3D): MorphTargetBinding[] {
  const bindings: MorphTargetBinding[] = [];
  root.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (mesh.isMesh && mesh.morphTargetDictionary && mesh.morphTargetInfluences) {
      bindings.push({ mesh, dict: mesh.morphTargetDictionary });
    }
  });
  return bindings;
}

function collectRigBones(root: THREE.Object3D, vrm: VRM | null): RigBones {
  if (vrm?.humanoid) {
    const head = vrm.humanoid.getNormalizedBoneNode("head") ?? undefined;
    const neck = vrm.humanoid.getNormalizedBoneNode("neck") ?? undefined;
    const spine = vrm.humanoid.getNormalizedBoneNode("upperChest")
      ?? vrm.humanoid.getNormalizedBoneNode("chest")
      ?? vrm.humanoid.getNormalizedBoneNode("spine")
      ?? undefined;
    return {
      head,
      neck,
      spine,
      headBaseRotX: head?.rotation.x ?? 0,
      headBaseRotY: head?.rotation.y ?? 0,
      spineBaseRotZ: spine?.rotation.z ?? 0,
    };
  }

  let head: THREE.Object3D | undefined;
  let neck: THREE.Object3D | undefined;
  let spine: THREE.Object3D | undefined;

  root.traverse((obj) => {
    const name = obj.name.toLowerCase();
    if (!head && (name === "head" || name.includes("mixamorighead") || name.endsWith("_head"))) {
      head = obj;
    } else if (!neck && (name === "neck" || name.includes("mixamorigneck"))) {
      neck = obj;
    } else if (!spine && (name === "spine2" || name === "chest" || name === "spine1" || name === "spine")) {
      spine = obj;
    }
  });

  return {
    head,
    neck,
    spine,
    headBaseRotX: head?.rotation.x ?? 0,
    headBaseRotY: head?.rotation.y ?? 0,
    spineBaseRotZ: spine?.rotation.z ?? 0,
  };
}

function setMorphByNames(
  bindings: MorphTargetBinding[],
  names: string[],
  value: number
): void {
  for (const { mesh, dict } of bindings) {
    const influences = mesh.morphTargetInfluences;
    if (!influences) {
      continue;
    }
    for (const name of names) {
      const idx = dict[name];
      if (idx !== undefined) {
        influences[idx] = value;
      }
    }
  }
}

function frameAvatarBehindDesk(
  avatarRoot: THREE.Object3D,
  bones: RigBones,
  camera: THREE.PerspectiveCamera
): void {
  avatarRoot.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(avatarRoot);
  const height = box.max.y - box.min.y;
  if (height > 0.1) {
    const targetHeight = 1.7;
    const scale = targetHeight / height;
    avatarRoot.scale.multiplyScalar(scale);
    avatarRoot.updateMatrixWorld(true);
  }

  const scaledBox = new THREE.Box3().setFromObject(avatarRoot);
  const centerX = (scaledBox.min.x + scaledBox.max.x) / 2;
  avatarRoot.position.x -= centerX;
  avatarRoot.position.y -= scaledBox.min.y;
  avatarRoot.position.z = -0.35;
  avatarRoot.updateMatrixWorld(true);

  let focusY = 1.44;
  if (bones.head) {
    const headPos = new THREE.Vector3();
    bones.head.getWorldPosition(headPos);
    focusY = headPos.y - 0.05;
  } else {
    const finalBox = new THREE.Box3().setFromObject(avatarRoot);
    focusY = finalBox.max.y - 0.22;
  }

  camera.position.set(0, focusY + 0.05, 1.38);
  camera.lookAt(0, focusY - 0.04, -0.35);
}

export function AnchorStage({
  activeStory,
  activeIndex,
  totalStories,
  isPlaying,
  hasStarted,
  ended,
  audioElement,
  onStartBroadcast,
}: AnchorStageProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatus>({ state: "loading" });
  const [debugOpen, setDebugOpen] = useState(false);
  const [config, setConfig] = useState<AnchorMotionConfig>(() => ({ ...ANCHOR_MOTION_CONFIG }));
  const [liveLoudness, setLiveLoudness] = useState(0);

  const configRef = useRef(config);
  configRef.current = config;

  const isPlayingRef = useRef(isPlaying);
  isPlayingRef.current = isPlaying;

  const analyserRef = useRef<AudioAnalyserHandle | null>(null);
  const nodEndTimeRef = useRef<number>(0);

  // Trigger a small head nod whenever the active story changes
  useEffect(() => {
    if (hasStarted && activeStory) {
      nodEndTimeRef.current = performance.now() + configRef.current.nodDurationSec * 1000;
    }
  }, [activeStory?.story_id, hasStarted, activeStory]);

  // Wire Web Audio AnalyserNode once after user gesture starts playback
  useEffect(() => {
    if (!hasStarted || !audioElement) {
      return;
    }
    const handle = ensureAudioAnalyser(audioElement);
    if (handle) {
      analyserRef.current = handle;
    }
  }, [hasStarted, audioElement, isPlaying]);

  // Toggle debug panel with key 'D'
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const tag = (event.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
        return;
      }
      if (event.key === "d" || event.key === "D") {
        setDebugOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Build Three.js studio scene and load /models/anchor.glb or /models/anchor.vrm
  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    } catch {
      setModelStatus({ state: "fallback", reason: "WebGL is unavailable in this browser." });
      return;
    }

    let disposed = false;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(container.clientWidth || 640, container.clientHeight || 420);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#040914");
    scene.fog = new THREE.Fog("#040914", 4.0, 9.5);

    const camera = new THREE.PerspectiveCamera(
      30,
      (container.clientWidth || 640) / (container.clientHeight || 420),
      0.1,
      25
    );
    camera.position.set(0, 1.48, 1.38);
    camera.lookAt(0, 1.38, -0.35);

    // Studio lighting: key, cool fill, warm rim
    const ambient = new THREE.HemisphereLight(0xdbeafe, 0x0f172a, 0.85);
    scene.add(ambient);

    const keyLight = new THREE.DirectionalLight(0xfff7ed, 2.1);
    keyLight.position.set(1.6, 2.5, 2.2);
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.75);
    fillLight.position.set(-2.0, 1.7, 1.4);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0x34d399, 0.9);
    rimLight.position.set(0.4, 2.4, -2.1);
    scene.add(rimLight);

    // Studio floor
    const floorGeo = new THREE.PlaneGeometry(12, 12);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x070d1a,
      roughness: 0.28,
      metalness: 0.45,
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    scene.add(floor);

    // Studio backdrop screen wall
    const backdropTex = createBackdropTexture();
    const wallGeo = new THREE.PlaneGeometry(5.6, 2.8);
    const wallMat = new THREE.MeshStandardMaterial({
      map: backdropTex,
      emissive: new THREE.Color(0x0c4a6e),
      emissiveMap: backdropTex,
      emissiveIntensity: 0.45,
      roughness: 0.6,
    });
    const wall = new THREE.Mesh(wallGeo, wallMat);
    wall.position.set(0, 1.55, -2.2);
    scene.add(wall);

    // Curved broadcast news desk
    const deskGeo = new THREE.CylinderGeometry(1.45, 1.5, 0.78, 48, 1, false, -Math.PI * 0.36, Math.PI * 0.72);
    const deskMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.25,
      metalness: 0.65,
    });
    const desk = new THREE.Mesh(deskGeo, deskMat);
    desk.position.set(0, 0.39, -0.78);
    scene.add(desk);

    const deskTopGeo = new THREE.CylinderGeometry(1.49, 1.49, 0.04, 48, 1, false, -Math.PI * 0.37, Math.PI * 0.74);
    const deskTopMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      roughness: 0.15,
      metalness: 0.8,
    });
    const deskTop = new THREE.Mesh(deskTopGeo, deskTopMat);
    deskTop.position.set(0, 0.8, -0.78);
    scene.add(deskTop);

    const trimGeo = new THREE.TorusGeometry(1.49, 0.012, 12, 48, Math.PI * 0.72);
    const trimMat = new THREE.MeshStandardMaterial({
      color: 0x22d3ee,
      emissive: 0x22d3ee,
      emissiveIntensity: 1.5,
    });
    const trim = new THREE.Mesh(trimGeo, trimMat);
    trim.rotation.x = Math.PI / 2;
    trim.rotation.z = Math.PI * 0.14;
    trim.position.set(0, 0.785, -0.78);
    scene.add(trim);

    let vrmInstance: VRM | null = null;
    let avatarScene: THREE.Object3D | null = null;
    let morphBindings: MorphTargetBinding[] = [];
    let rigBones: RigBones = { headBaseRotX: 0, headBaseRotY: 0, spineBaseRotZ: 0 };

    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));

    async function loadAvatar() {
      setModelStatus({ state: "loading" });

      for (const candidate of MODEL_CANDIDATES) {
        if (disposed) {
          return;
        }
        const exists = await checkModelExists(candidate.url);
        if (!exists) {
          continue;
        }
        try {
          const gltf = await loader.loadAsync(candidate.url);
          if (disposed) {
            return;
          }
          const loadedVrm = (gltf.userData as { vrm?: VRM }).vrm ?? null;
          if (loadedVrm) {
            VRMUtils.rotateVRM0(loadedVrm);
            vrmInstance = loadedVrm;
            avatarScene = loadedVrm.scene;
            if (loadedVrm.lookAt) {
              loadedVrm.lookAt.target = camera;
            }
          } else {
            avatarScene = gltf.scene;
          }

          scene.add(avatarScene);
          morphBindings = collectMorphBindings(avatarScene);
          rigBones = collectRigBones(avatarScene, vrmInstance);
          frameAvatarBehindDesk(avatarScene, rigBones, camera);

          setModelStatus({
            state: "ready",
            format: vrmInstance ? "VRM" : "GLB",
          });
          return;
        } catch (err) {
          console.warn(`Failed loading ${candidate.url}:`, err);
        }
      }

      if (!disposed) {
        setModelStatus({
          state: "fallback",
          reason: "Place anchor.glb (Avaturn) or anchor.vrm in frontend/public/models/.",
        });
      }
    }

    void loadAvatar();

    // Resize handling
    const resizeObserver = new ResizeObserver(() => {
      if (disposed || !container) {
        return;
      }
      const w = container.clientWidth || 640;
      const h = container.clientHeight || 420;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });
    resizeObserver.observe(container);

    // Pause rendering when tab is hidden
    let tabHidden = document.hidden;
    const onVisibilityChange = () => {
      tabHidden = document.hidden;
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    let rafId = 0;
    let lastTime = performance.now();
    let smoothedLoudness = 0;
    let nextBlinkAt = performance.now() + 2600;
    let blinkStartAt = -1;
    let frameCounter = 0;

    const animate = (now: number) => {
      if (disposed) {
        return;
      }
      rafId = window.requestAnimationFrame(animate);
      if (tabHidden) {
        lastTime = now;
        return;
      }

      const delta = Math.min(0.1, (now - lastTime) / 1000);
      lastTime = now;
      const cfg = configRef.current;

      // 1. Audio loudness lip-sync
      let aa = 0;
      let oh = 0;
      let ee = 0;
      const analyserHandle = analyserRef.current;
      if (analyserHandle) {
        analyserHandle.analyser.getByteTimeDomainData(analyserHandle.timeData);
        analyserHandle.analyser.getByteFrequencyData(analyserHandle.freqData);
        const shapes = computeMouthShapes(
          analyserHandle.timeData,
          analyserHandle.freqData,
          smoothedLoudness,
          cfg,
          isPlayingRef.current
        );
        aa = shapes.aa;
        oh = shapes.oh;
        ee = shapes.ee;
        smoothedLoudness = shapes.smoothedLoudness;
      } else {
        smoothedLoudness = 0;
      }

      if (frameCounter % 6 === 0) {
        setLiveLoudness(Number(smoothedLoudness.toFixed(2)));
      }
      frameCounter += 1;

      // 2. Random blinking
      let blinkWeight = 0;
      if (blinkStartAt < 0 && now >= nextBlinkAt) {
        blinkStartAt = now;
      }
      if (blinkStartAt >= 0) {
        const elapsed = (now - blinkStartAt) / 1000;
        if (elapsed >= cfg.blinkDurationSec) {
          blinkStartAt = -1;
          const span = cfg.blinkIntervalMaxSec - cfg.blinkIntervalMinSec;
          nextBlinkAt = now + (cfg.blinkIntervalMinSec + Math.random() * span) * 1000;
        } else {
          blinkWeight = Math.sin((elapsed / cfg.blinkDurationSec) * Math.PI);
        }
      }

      // 3. Apply expressions to VRM or GLB morph targets
      if (vrmInstance?.expressionManager) {
        vrmInstance.expressionManager.setValue("aa", aa);
        vrmInstance.expressionManager.setValue("oh", oh);
        vrmInstance.expressionManager.setValue("ee", ee);
        vrmInstance.expressionManager.setValue("blink", blinkWeight);
        vrmInstance.update(delta);
      } else if (morphBindings.length > 0) {
        setMorphByNames(morphBindings, ["jawOpen", "mouthOpen", "viseme_aa"], aa * 0.85);
        setMorphByNames(morphBindings, ["mouthFunnel", "mouthPucker", "viseme_O"], oh * 0.75);
        setMorphByNames(
          morphBindings,
          ["mouthSmileLeft", "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight", "viseme_E"],
          ee * 0.55
        );
        setMorphByNames(morphBindings, ["eyeBlinkLeft", "eyeBlinkRight", "eyesClosed"], blinkWeight);
      }

      // 4. Subtle head/chest idle sway + story-start nod
      const t = now / 1000;
      const swayScale = cfg.swayAmount;
      let nodOffset = 0;
      if (now < nodEndTimeRef.current) {
        const remaining = (nodEndTimeRef.current - now) / (cfg.nodDurationSec * 1000);
        nodOffset = Math.sin((1 - remaining) * Math.PI) * cfg.nodAmplitudeRad;
      }

      if (rigBones.head) {
        rigBones.head.rotation.x =
          rigBones.headBaseRotX + Math.sin(t * 1.1) * 0.015 * swayScale + nodOffset;
        rigBones.head.rotation.y =
          rigBones.headBaseRotY + Math.sin(t * 0.65) * 0.025 * swayScale;
      }
      if (rigBones.spine) {
        rigBones.spine.rotation.z =
          rigBones.spineBaseRotZ + Math.sin(t * 0.8) * 0.012 * swayScale;
      }

      renderer.render(scene, camera);
    };

    rafId = window.requestAnimationFrame(animate);

    return () => {
      disposed = true;
      window.cancelAnimationFrame(rafId);
      resizeObserver.disconnect();
      document.removeEventListener("visibilitychange", onVisibilityChange);

      scene.traverse((obj) => {
        const mesh = obj as THREE.Mesh;
        if (mesh.isMesh) {
          mesh.geometry?.dispose();
          const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          for (const mat of mats) {
            if (mat) {
              mat.dispose();
            }
          }
        }
      });
      backdropTex.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  return (
    <section className="relative flex min-h-[360px] flex-col justify-between overflow-hidden rounded-2xl border border-slate-800/90 bg-slate-950 shadow-2xl sm:min-h-[440px]">
      {/* Three.js canvas host */}
      <div ref={containerRef} className="absolute inset-0 h-full w-full" />

      {/* Fallback 2D studio anchor card when no model exists or WebGL failed */}
      {modelStatus.state === "fallback" && (
        <div className="relative z-10 m-auto flex flex-col items-center justify-center px-6 py-8 text-center">
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
          <h2 className="text-lg font-bold text-white">
            {activeStory?.anchor === "Anchor_A" ? "Uzma (Anchor A)" : activeStory?.anchor ?? "Anchor"}
          </h2>
          <p className="mt-1.5 max-w-md text-xs text-slate-400">
            {modelStatus.reason}
          </p>
        </div>
      )}

      {/* Top HUD bar */}
      <div className="relative z-20 flex items-center justify-between gap-2 p-4">
        <div className="flex items-center gap-2">
          <span className="rounded-md border border-cyan-500/30 bg-slate-950/80 px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-cyan-300 backdrop-blur-sm">
            {activeStory?.category ?? "Bulletin"}
          </span>
          {modelStatus.state === "loading" && (
            <span className="rounded-md border border-slate-700 bg-slate-950/80 px-2.5 py-1 text-[11px] text-slate-300">
              Loading 3D studio...
            </span>
          )}
          {modelStatus.state === "ready" && (
            <span className="rounded-md border border-emerald-500/30 bg-slate-950/80 px-2.5 py-1 text-[11px] text-emerald-300">
              3D {modelStatus.format} Active
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setDebugOpen((prev) => !prev)}
            title="Toggle lip-sync tuner (D)"
            className="inline-flex items-center gap-1 rounded-md border border-slate-700/80 bg-slate-950/80 px-2 py-1 text-[11px] text-slate-300 backdrop-blur-sm hover:border-cyan-500/50 hover:text-cyan-300"
          >
            <SlidersHorizontal className="h-3 w-3" />
            Tune (D)
          </button>
          <span className="rounded-md border border-slate-700/80 bg-slate-950/80 px-2.5 py-1 text-xs text-slate-300 backdrop-blur-sm">
            Story {totalStories > 0 ? activeIndex + 1 : 0} of {totalStories}
          </span>
        </div>
      </div>

      {/* Debug tuning panel (toggle with D key) */}
      {debugOpen && (
        <div className="relative z-30 mx-4 mb-auto max-w-xs rounded-xl border border-cyan-500/40 bg-slate-950/90 p-3.5 text-xs text-slate-200 shadow-xl backdrop-blur-md">
          <div className="mb-2 flex items-center justify-between font-semibold text-cyan-300">
            <span>Anchor Tuning (D)</span>
            <span>Loudness: {liveLoudness.toFixed(2)}</span>
          </div>
          <label className="mb-2 block">
            <span className="flex justify-between text-slate-400">
              <span>Mouth Gain</span>
              <span>{config.mouthGain.toFixed(1)}</span>
            </span>
            <input
              type="range"
              min={0.5}
              max={6.0}
              step={0.1}
              value={config.mouthGain}
              onChange={(e) =>
                setConfig((prev) => ({ ...prev, mouthGain: Number(e.target.value) }))
              }
              className="w-full accent-cyan-400"
            />
          </label>
          <label className="mb-2 block">
            <span className="flex justify-between text-slate-400">
              <span>Smoothing</span>
              <span>{config.smoothing.toFixed(2)}</span>
            </span>
            <input
              type="range"
              min={0.0}
              max={0.85}
              step={0.05}
              value={config.smoothing}
              onChange={(e) =>
                setConfig((prev) => ({ ...prev, smoothing: Number(e.target.value) }))
              }
              className="w-full accent-cyan-400"
            />
          </label>
          <label className="block">
            <span className="flex justify-between text-slate-400">
              <span>Idle Sway</span>
              <span>{config.swayAmount.toFixed(1)}</span>
            </span>
            <input
              type="range"
              min={0.0}
              max={2.5}
              step={0.1}
              value={config.swayAmount}
              onChange={(e) =>
                setConfig((prev) => ({ ...prev, swayAmount: Number(e.target.value) }))
              }
              className="w-full accent-cyan-400"
            />
          </label>
        </div>
      )}

      {/* Browser autoplay Start / Replay overlay */}
      {(!hasStarted || ended) && (
        <div className="relative z-20 mt-auto flex justify-center pb-6">
          <button
            type="button"
            onClick={onStartBroadcast}
            className="inline-flex items-center gap-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 px-6 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-500/25 transition hover:brightness-110"
          >
            {ended ? (
              <>
                <RotateCcw className="h-4 w-4" />
                Replay Broadcast
              </>
            ) : (
              <>
                <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M8 5v14l11-7z" />
                </svg>
                <span>Start Broadcast</span>
                <span dir="rtl" className="font-urdu text-sm font-semibold leading-normal">
                  نشریات شروع کریں
                </span>
              </>
            )}
          </button>
        </div>
      )}
    </section>
  );
}
