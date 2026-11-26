<div align="center">

![AI News Studio Hero Banner](docs/assets/hero-banner.jpg)

# AI News Studio

**Automated Urdu AI Broadcast Pipeline and 3D Virtual Studio Player**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-4285F4?style=for-the-badge&logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Three.js](https://img.shields.io/badge/Three.js-000000?style=for-the-badge&logo=threedotjs&logoColor=white)](https://threejs.org/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/features/actions)

</div>

---

## Overview

**AI News Studio** is a zero-budget, simulated television newsroom designed for a Pakistani Urdu audience. It ingests verified reporting from Pakistani RSS feeds, removes duplicate coverage across publishers, generates source-grounded Urdu anchor scripts, synthesizes neural speech with exact audio timelines, and presents synchronized bulletins inside a browser-based 3D studio player.

It is an automated broadcast simulation system built on open-source and free-tier tooling, not a live TV channel or GPU video generator.

### Conceptual Studio Interface Preview

<div align="center">
  <img src="docs/assets/studio-preview.jpg" alt="Conceptual AI News Studio Player Preview" width="880" />
</div>

*Target studio layout: 3D VRM news anchor with audio-driven lip sync, synchronized Urdu insight panel, lower-third headline card, and right-to-left breaking news ticker.*

---

## Architecture

```mermaid
flowchart LR
    A["RSS Feeds (Dawn, Express Tribune)"] --> B["Collector (httpx + BeautifulSoup)"]
    B --> C["Deduplicator (TF-IDF + Cosine Similarity)"]
    C --> D["Urdu Script Engine (Gemini Structured JSON + Validators)"]
    D --> E["Speech & Timeline (edge-tts + mutagen)"]
    E --> F["Supabase (Postgres + Public Media Bucket)"]
    F --> G["Web Studio (React + Three.js VRM + Noto Nastaliq Urdu)"]
```

### Key Engineering Guarantees

| Component | Design Choice | Purpose |
| :--- | :--- | :--- |
| **Ingestion & Clustering** | `httpx` + `feedparser` + `TfidfVectorizer` | Merges duplicate Dawn and Express Tribune coverage with graceful summary fallback |
| **Grounded Script Engine** | `google-genai` structured JSON + custom validators | Enforces 35-60 Urdu words, >= 80% Urdu script ratio, 3 insight facts, and zero invented numbers/entities |
| **Speech & Timeline** | `TTSProvider` (`edge-tts`) + `mutagen` | Measures exact MP3 durations and computes cumulative `start_time_sec` with a 0.6s gap |
| **Data & Security** | Supabase Postgres (RLS) + `local_json` fallback | Public `anon` read-only access to `ready` bulletins; backend writes isolated via secret key |
| **3D Studio Player** | Three.js + `@pixiv/three-vrm` + Web Audio API | Real-time loudness-driven mouth expressions in the browser with zero GPU server cost |

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend & API** | ![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) ![Pydantic](https://img.shields.io/badge/Pydantic%20v2-E92063?style=flat-square&logo=pydantic&logoColor=white) |
| **NLP & LLM** | ![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikitlearn&logoColor=white) ![Google Gemini](https://img.shields.io/badge/google--genai-4285F4?style=flat-square&logo=googlegemini&logoColor=white) |
| **Speech & Audio** | `edge-tts` (`ur-PK-UzmaNeural`, `ur-PK-AsadNeural`), `mutagen` |
| **Database & Storage** | ![Supabase](https://img.shields.io/badge/Supabase%20Postgres%20%26%20Storage-3ECF8E?style=flat-square&logo=supabase&logoColor=white) |
| **Frontend Studio** | ![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white) ![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white) ![Tailwind CSS](https://img.shields.io/badge/Tailwind-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white) ![Three.js](https://img.shields.io/badge/Three.js%20%2B%20VRM-000000?style=flat-square&logo=threedotjs&logoColor=white) `Noto Nastaliq Urdu` |
| **Testing & Automation** | ![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white) `ruff` `vitest` ![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white) ![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white) |

---

## Module Status

| Module | Status | Notes |
| :--- | :--- | :--- |
| RSS Collector & TF-IDF Deduplicator | Implemented | Dawn and Express Tribune feeds with 10s timeout and fallback |
| Supabase Schema, RLS & Media Client | Implemented | Migrations, public `media` upload, pruning, and offline JSON fallback |
| Gemini Urdu Script Engine & Validators | Implemented | Single-call generation, retry on failed story, and `sample_bulletin_ur.json` backup |
| Urdu TTS Engine & Timeline Sync | Implemented | `TTSProvider` abstraction, abbreviation cleanup, `mutagen` timing, and Supabase upload |
| End-to-End Batch Job & Cron Automation | Planned | Single-command pipeline runner and scheduled GitHub Actions workflow |
| React Studio Player & 3D VRM Anchor | Planned | RTL Nastaleeq UI, synchronized timeline player, and Web Audio lip-sync |

---

## Repository Structure

```text
├── .github/workflows/          # CI checks (and scheduled pipeline workflow)
├── backend/
│   ├── app/
│   │   ├── core/config.py      # Pydantic settings loaded from backend/.env
│   │   ├── eval/               # Validator pass-rate evaluation scripts
│   │   ├── pipeline/           # Collector, deduplicator, prompts, validators, Gemini, TTS, timeline
│   │   ├── schemas/            # Pydantic data contracts
│   │   ├── services/           # Supabase Postgres/Storage client and health check
│   │   └── main.py             # FastAPI server
│   ├── data/                   # Saved sample Urdu bulletin for offline demo fallback
│   ├── supabase/migrations/    # Postgres tables, indexes, RLS policies, and grants
│   ├── tests/                  # Offline pytest suite
│   ├── requirements.txt
│   └── .env.example
├── docs/assets/                # Repository visuals
└── frontend/                   # React + TypeScript + Three.js studio (upcoming)
```

---

## Run Locally

Run all commands from the repository root.

### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
copy backend\.env.example backend\.env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY, and GEMINI_MODEL

pytest
python -m backend.app.pipeline.collector
python -m backend.app.pipeline.check_gemini
python -m backend.app.services.check_supabase
uvicorn backend.app.main:app --reload
```

### Mac / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY, and GEMINI_MODEL

pytest
python -m backend.app.pipeline.collector
python -m backend.app.pipeline.check_gemini
python -m backend.app.services.check_supabase
uvicorn backend.app.main:app --reload
```

Once the server starts, open `http://localhost:8000/docs` in your browser.

---

## Limitations & Academic Disclaimer

- **Unofficial TTS endpoint:** `edge-tts` relies on Microsoft Edge's online speech service and can experience transient failures; retry logic and the `TTSProvider` interface are in place to support swapping to Azure Speech if needed.
- **Simulated lip sync:** Mouth movement uses Web Audio loudness (`AnalyserNode`) driving VRM blendshapes rather than phoneme-level alignment or GPU face rendering.
- **Source attribution:** All ingested articles remain attributed to their original publishers (`Dawn` and `The Express Tribune`) with direct source URLs. This software is an academic research prototype and does not operate as a licensed broadcast service.
