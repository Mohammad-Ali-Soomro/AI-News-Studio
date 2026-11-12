# AI News Studio 🎙️📺
### An Automated Bilingual AI Anchor News Presentation System
**Final Year Project (2025–2026)**  
**Faculty of Computer Sciences and Engineering (FCSE)**  
**Ghulam Ishaq Khan Institute of Engineering Sciences and Technology (GIKI)**

---

## 👥 Project Team & Supervision
- **Muhammad Ali** (Reg: 2023326) — *Lead, Pipeline Architecture & Scripting*
- **Hassan Khalid** (Reg: 2023242) — *Speech Synthesis (TTS) & Anchor Avatar Engine*
- **Sajeel Malik** (Reg: 2023633) — *Frontend Studio Player & Timeline Synchronization*
- **Supervisor:** Dr. Qammar Abbas

---

## 🎯 Executive Summary
**AI News Studio** is an automated end-to-end news processing and presentation system. It ingests verified, authentic reporting from trusted Pakistani and global news publishers (such as *Dawn*, *The Express Tribune*, *Reuters*), resolves duplicates, generates bilingual anchor bulletins (Urdu & English), synthesizes realistic voice, and presents the news in a synchronized TV newsroom simulation player featuring:
1. **AI Anchor Presenter** (Urdu & English lip-synced audio/video).
2. **Dynamic Insight Panel** (Key figures, dates, bullet points, charts/imagery).
3. **Live Ticker** (Bilingual scrolling ticker: right-to-left for Urdu, left-to-right for English).
4. **Publisher Credit & Attribution** (Traceable source links, preventing unverified hallucinations).

---

## 🏗️ System Architecture & Workflow

```
[ News Sources (Dawn, Tribune, Reuters RSS) ]
                     │
                     ▼
       ┌───────────────────────────┐
       │     Source Collector      │  (Automated RSS Ingestion)
       └─────────────┬─────────────┘
                     │
                     ▼
       ┌───────────────────────────┐
       │   Deduplication & Merge   │  (Semantic Clustering)
       └─────────────┬─────────────┘
                     │
                     ▼
       ┌───────────────────────────┐
       │   Bilingual Script Engine │  (LLM: Story Rundown, Urdu/EN Scripts)
       └─────────────┬─────────────┘
                     │
                     ▼
       ┌───────────────────────────┐
       │    Audio & Video Engine   │  (Free Neural TTS + Talking Avatar)
       └─────────────┬─────────────┘
                     │
                     ▼
       ┌───────────────────────────┐
       │ Timeline JSON Contract    │  (Sync timestamps for audio, cards, ticker)
       └─────────────┬─────────────┘
                     │
                     ▼
       ┌───────────────────────────┐
       │   Simulated Studio Player │  (Next.js / React Broadcasting Interface)
       └───────────────────────────┘
```

---

## 🌿 Git Branching Strategy
To ensure smooth parallel development across our 3-member team:

| Branch Name | Primary Owner | Module Focus |
| :--- | :--- | :--- |
| `main` | Production / Milestone releases | Fully integrated and tested codebase |
| `muhammad-ali` | Muhammad Ali | Backend, News Collector, Deduplication, LLM Prompts & Pipeline |
| `hassan-khalid` | Hassan Khalid | TTS Engine (Urdu/English), Audio Processing, Avatar Lip-sync |
| `sajeel-malik` | Sajeel Malik | Frontend Studio Player, Ticker, Insight Panel, Timeline Sync |

### Workflow:
1. Work exclusively inside your designated feature branch:
   ```bash
   git checkout <your-branch-name>
   git pull origin <your-branch-name>
   ```
2. Once a milestone is verified, create a Pull Request (PR) or merge into `main`.

---

## 🚀 Tech Stack (100% Free & Open-Source)
- **Backend:** Python 3.10+, FastAPI, SQLite / PostgreSQL.
- **News Extraction:** Feedparser (RSS), BeautifulSoup4, Newspaper4k.
- **LLM & NLP:** Google Gemini API (Free tier: 15 RPM / 1M tokens/min) or Groq / HuggingFace.
- **Speech Synthesis (TTS):** `edge-tts` (Microsoft Edge Neural Voices: `ur-PK-UzmaNeural`, `ur-PK-AsadNeural`, `en-US-AndrewMultilingualNeural`).
- **Avatar Simulation:** Wav2Lip / SadTalker (offline rendering) or Web-based TalkingHead.
- **Frontend Studio:** React / Next.js, Tailwind CSS, Lucide Icons, Framer Motion.

---

## 📁 Repository Structure
```text
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI route handlers
│   │   ├── core/            # App configuration & DB setup
│   │   ├── pipeline/        # Collection, script generation & media pipeline
│   │   ├── schemas/         # Pydantic models & JSON contracts
│   │   └── main.py          # FastAPI server entry point
│   ├── media/               # Local generated audio/video storage (gitignored)
│   ├── requirements.txt     # Python backend dependencies
│   └── .env.example         # Template for environment keys
├── frontend/                # React / Next.js Web News Studio
├── docs/                    # Technical architecture, timeline contracts, guides
└── README.md                # Project documentation
```

---

## 📜 Academic Disclaimer
This project is an academic research and software engineering prototype for demonstration purposes at GIK Institute. All scraped articles are credited with live URLs to their respective primary publishers.
