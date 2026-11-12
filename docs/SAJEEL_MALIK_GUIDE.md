# 📺 Sajeel Malik — Web Studio Player & Timeline Synchronization Guide
**Role:** Lead Frontend & Broadcast Studio Systems Engineer  
**Branch:** `sajeel-malik`  
**Teammates:** Muhammad Ali (Lead/Pipeline), Hassan Khalid (Audio/Avatar)  
**Supervisor:** Dr. Qammar Abbas | **Department:** FCSE, GIK Institute  

---

## 🌟 1. The Big Picture: Where You Fit in the Project

In **AI News Studio**, Muhammad Ali builds the news scraping & script engine, and Hassan Khalid synthesizes the neural audio and avatar video clips. 

**Your mission is to build the visual presentation layer that the panel interacts with:**
1. You build a **Studio Broadcast Web Player** that looks indistinguishable from a major professional television network (like *Dawn News*, *Geo*, or *BBC World*).
2. You engineer the **Timeline Synchronization Engine**: making the Anchor Video, Insight Panel, and Live Ticker transition in sub-second synchrony.
3. You implement the **Producer Master Control Room (MCR)**: a control dashboard where the news editor (or the defense panel) can inspect ingested news, view the NLP clusters, toggle between Urdu and English, and trigger a live bulletin.
4. You ensure high-quality **Pakistani Urdu Typography (Nastaleeq RTL)** with proper right-to-left layout and broadcast chyrons.

```
====================================================================================================
                               THE BROADCAST INTERFACE YOU WILL BUILD
====================================================================================================

 ┌───────────────────────────────────────────────────┬──────────────────────────────────────────────┐
 │ [LIVE 🔴]  AI NEWS STUDIO • شام 7 بجے کا بلیٹن   │                INSIGHT PANEL                 │
 ├───────────────────────────────────────────────────┼──────────────────────────────────────────────┤
 │                                                   │  ┌─────────────────────────────────────────┐ │
 │                   AI ANCHOR BOX                   │  │ 📌 اہم ترین خبر                         │ │
 │       <video src={activeStory.video_url} />       │  │ پاکستان میں معاشی استحکام کا نیا پیکج   │ │
 │                                                   │  ├─────────────────────────────────────────┤ │
 │   Dual Anchors:                                   │  │ 📊 اہم اعداد و شمار: 1.2 ارب ڈالر        │ │
 │   • Uzma (Anchor A) - National Headlines          │  │ 📍 مقام: اسلام آباد                     │ │
 │   • Asad (Anchor B) - Economy & Technology        │  │ 🏢 مصدقہ ماخذ: ڈان نیوز                 │ │
 │                                                   │  ├─────────────────────────────────────────┤ │
 │   [ Lower-Third Chyron: علی اسد • سٹوڈیو اینکر ]  │  │ 🔗 [اصل خبر پڑھیں - Dawn News] ↗        │ │
 │                                                   │  └─────────────────────────────────────────┘ │
 ├───────────────────────────────────────────────────┴──────────────────────────────────────────────┤
 │ 🔴 بریکنگ نیوز (RTL ◄◄◄): وفاقی کابینہ کا اہم ترین اجلاس، نئے برآمدی پیکیج کی باضابطہ منظوری...      │
 └──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 2. Tech Stack & Recommended Libraries

| Subsystem | Tool | Purpose |
| :--- | :--- | :--- |
| **Framework** | Next.js 14+ (App Router) or Vite + React (TypeScript) | Fast, responsive, component-driven client |
| **Styling** | Tailwind CSS | Rapid, dark-mode broadcast graphics & glassy studio HUDs |
| **Animation** | Framer Motion | Smooth 3D card flips for Insight Panel & breaking news flashes |
| **Icons** | Lucide React | Studio controls (Play, Pause, Mute, Language, Fullscreen) |
| **Urdu Font** | Google Fonts `Noto Nastaliq Urdu` or `Jameel Noori Nastaleeq` | Flawless Urdu broadcast typography |
| **API Client** | `axios` or standard `fetch` | Communicating with Muhammad Ali's FastAPI backend |

---

## 📦 3. Your Module Directory Structure

Everything you build lives inside the `frontend/` directory:

```text
frontend/
├── src/
│   ├── components/
│   │   ├── studio/
│   │   │   ├── AnchorPlayer.tsx       # Anchor video/audio player with live lower-third
│   │   │   ├── InsightPanel.tsx       # Real-time fact cards with publisher attribution badge
│   │   │   ├── LiveTicker.tsx         # Hardware-accelerated RTL Urdu & LTR English ticker
│   │   │   └── BroadcastHeader.tsx    # Live badge, date/time in PKT, language toggle
│   │   └── mcr/
│   │       ├── FeedMonitor.tsx        # Raw article inspector (Dawn, Tribune)
│   │       ├── ClusterViewer.tsx      # Visual representation of NLP story clusters
│   │       └── RundownEditor.tsx      # Bulletin trigger & language selector
│   ├── hooks/
│   │   └── useBroadcastTimeline.ts    # <-- THE HEART: Coordinates time sync
│   ├── types/
│   │   └── bulletin.ts                # TypeScript interfaces matching backend Pydantic models
│   ├── styles/
│   │   └── globals.css                # Nastaleeq font imports & custom animations
│   ├── App.tsx                        # Main dashboard & view switcher
│   └── main.tsx
├── package.json
└── tailwind.config.js
```

---

## 🚀 4. Step-by-Step Implementation Guide

### Step 4.1: Setting Up Your Branch Locally
Clone the repository and checkout your designated branch:
```bash
git clone https://github.com/Mohammad-Ali-Soomro/AI-News-Studio.git
cd "AI-News-Studio"
git checkout sajeel-malik
git pull origin sajeel-malik
```

Initialize your React / Next.js project inside `frontend/`:
```bash
cd frontend
# Recommended: Fast Vite + React + TypeScript setup
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install lucide-react framer-motion axios
```

Configure `tailwind.config.js` to support Urdu Nastaleeq font and RTL:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        urdu: ['"Noto Nastaliq Urdu"', 'serif'],
        sans: ['Inter', 'sans-serif'],
      },
      colors: {
        studio: {
          dark: '#0B0F19',
          card: '#161F30',
          accent: '#E11D48', // Broadcast Red
          gold: '#F59E0B',
          cyan: '#06B6D4',
        }
      }
    },
  },
  plugins: [],
}
```

Import Google's Urdu Font in `src/styles/globals.css`:
```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;600;700&display=swap');
@tailwind base;
@tailwind components;
@tailwind utilities;
```

---

### Step 4.2: The TypeScript Schema (`types/bulletin.ts`)
Create `src/types/bulletin.ts` matching the backend JSON schema:

```typescript
export interface SourceArticle {
  title: string;
  publisher: string;
  source_url: string;
  published_at?: string;
}

export interface InsightFact {
  key: string;
  value: string;
}

export interface StoryRundown {
  story_id: string;
  category: string;
  anchor: "Anchor_A" | "Anchor_B";
  language: "ur" | "en";
  spoken_script: string;
  headline: string;
  ticker_text: string;
  source: SourceArticle;
  insight_panel: InsightFact[];
  start_time_sec: number;
  duration_sec: number;
  audio_url?: string;
  video_url?: string;
}

export interface Bulletin {
  bulletin_id: string;
  title: string;
  generated_at: string;
  language: "ur" | "en";
  total_duration_sec: number;
  stories: StoryRundown[];
}
```

---

### Step 4.3: The Heart: Timeline Synchronization Hook (`hooks/useBroadcastTimeline.ts`)
This hook guarantees that all elements on screen stay in 100% sync with the audio/video player:

```typescript
import { useState, useEffect, useRef } from "react";
import { Bulletin, StoryRundown } from "../types/bulletin";

export function useBroadcastTimeline(bulletin: Bulletin | null) {
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [activeStoryIndex, setActiveStoryIndex] = useState<number>(0);
  const mediaRef = useRef<HTMLVideoElement | HTMLAudioElement | null>(null);

  // Update active story based on current playback time
  useEffect(() => {
    if (!bulletin || !bulletin.stories.length) return;

    const foundIndex = bulletin.stories.findIndex((story) => {
      const start = story.start_time_sec;
      const end = story.start_time_sec + story.duration_sec;
      return currentTime >= start && currentTime < end;
    });

    if (foundIndex !== -1 && foundIndex !== activeStoryIndex) {
      setActiveStoryIndex(foundIndex);
    }
  }, [currentTime, bulletin]);

  const activeStory: StoryRundown | null =
    bulletin && bulletin.stories.length > 0
      ? bulletin.stories[activeStoryIndex] || bulletin.stories[0]
      : null;

  return {
    currentTime,
    setCurrentTime,
    isPlaying,
    setIsPlaying,
    activeStory,
    activeStoryIndex,
    mediaRef,
  };
}
```

---

### Step 4.4: Building the Core Studio Components

#### Component 1: `InsightPanel.tsx`
Renders the facts and verified source link. Uses Framer Motion so the cards flip dynamically when the active story changes:

```tsx
import React from "react";
import { StoryRundown } from "../../types/bulletin";
import { motion, AnimatePresence } from "framer-motion";
import { ExternalLink, CheckCircle2 } from "lucide-react";

interface Props {
  story: StoryRundown | null;
  language: "ur" | "en";
}

export const InsightPanel: React.FC<Props> = ({ story, language }) => {
  if (!story) return null;
  const isUrdu = language === "ur";

  return (
    <div className={`bg-studio-card/80 backdrop-blur-md border border-slate-800 rounded-xl p-5 shadow-2xl ${isUrdu ? 'font-urdu text-right' : 'text-left'}`}>
      <div className="flex items-center justify-between pb-3 border-b border-slate-700/60 mb-4">
        <span className="text-xs uppercase tracking-widest text-studio-cyan font-bold flex items-center gap-1.5">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          {isUrdu ? "مصدقہ خبر و اعداد و شمار" : "Verified Source & Facts"}
        </span>
        <span className="text-xs bg-slate-800 text-slate-300 px-2.5 py-0.5 rounded-full">
          {story.category}
        </span>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={story.story_id}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -15 }}
          transition={{ duration: 0.35 }}
        >
          <h3 className="text-lg font-bold text-white mb-4 leading-relaxed">
            {story.headline}
          </h3>

          {/* Key Facts */}
          <div className="space-y-3 mb-5">
            {story.insight_panel.map((fact, idx) => (
              <div key={idx} className="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80 flex justify-between items-center">
                <span className="text-sm text-slate-400">{fact.key}</span>
                <span className="text-sm font-semibold text-amber-300">{fact.value}</span>
              </div>
            ))}
          </div>

          {/* Source Attribution Badge */}
          <div className="pt-3 border-t border-slate-700/40 flex items-center justify-between text-xs text-slate-400">
            <span>{isUrdu ? `ماخذ: ${story.source.publisher}` : `Source: ${story.source.publisher}`}</span>
            <a
              href={story.source.source_url}
              target="_blank"
              rel="noreferrer"
              className="text-studio-cyan hover:underline flex items-center gap-1"
            >
              {isUrdu ? "اصل خبر دیکھیں" : "View Article"}
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
};
```

---

#### Component 2: `LiveTicker.tsx`
A smooth, hardware-accelerated ticker bar:
- Right-to-Left (دائیں سے بائیں) for Urdu.
- Left-to-Right for English.

```tsx
import React from "react";

interface Props {
  text: string;
  language: "ur" | "en";
}

export const LiveTicker: React.FC<Props> = ({ text, language }) => {
  const isUrdu = language === "ur";

  return (
    <div className="w-full bg-red-700 text-white flex items-center h-12 shadow-inner overflow-hidden border-t-2 border-red-500">
      <div className="bg-red-900 px-4 h-full flex items-center font-bold text-xs uppercase tracking-wider z-10 shadow-md">
        {isUrdu ? "بریکنگ نیوز" : "BREAKING NEWS"}
      </div>
      <div className="flex-1 overflow-hidden relative">
        <div className={`whitespace-nowrap inline-block animate-marquee ${isUrdu ? 'font-urdu text-right text-base' : 'text-sm font-semibold'}`}>
          {text} &nbsp;&nbsp;&nbsp; • &nbsp;&nbsp;&nbsp; {text}
        </div>
      </div>
    </div>
  );
};
```

Add the CSS keyframes in `globals.css`:
```css
@keyframes marquee {
  0% { transform: translateX(100%); }
  100% { transform: translateX(-100%); }
}
.animate-marquee {
  display: inline-block;
  animation: marquee 25s linear infinite;
}
```

---

### Step 4.5: Connecting to Ali's Backend API
The FastAPI backend runs on `http://localhost:8000`.

To fetch the latest bulletin:
```typescript
import axios from 'axios';

export async function fetchLatestBulletin(lang: "ur" | "en" = "ur") {
  const response = await axios.get(`http://localhost:8000/api/v1/bulletin/latest?language=${lang}`);
  return response.data;
}

export async function generateNewBulletin(lang: "ur" | "en" = "ur") {
  const response = await axios.post(`http://localhost:8000/api/v1/bulletin/generate?language=${lang}`);
  return response.data;
}
```

---

## 🧪 5. Testing & Verification Checklist

- [ ] `npm run dev` starts the frontend locally with zero errors.
- [ ] Connects to `http://localhost:8000/api/v1/bulletin/latest` and displays real stories.
- [ ] Urdu Nastaleeq font renders beautifully with correct RTL alignment.
- [ ] Playing the video/audio automatically transitions the Insight Panel when `currentTime` reaches the next story.
- [ ] Ticker displays the active story headline.
- [ ] Clicking the publisher link opens Dawn / Tribune in a new tab.

---

## 🌿 6. Git Workflow for Sajeel

Stay on your branch while working:
```bash
# Check status
git status
git branch

# Commit your UI work
git add src/
git commit -m "feat(sajeel): implement TV studio layout, ticker, and timeline sync hook"

# Push to your remote branch
git push origin sajeel-malik
```

When your frontend prototype is tested and ready to merge with Ali's pipeline, notify Ali to initiate the PR into `main`!
