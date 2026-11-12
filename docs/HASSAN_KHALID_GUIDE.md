# 🎙️ Hassan Khalid — Audio, Speech (TTS) & Avatar Engine Guide
**Role:** Lead Audio & Avatar Engineer  
**Branch:** `hassan-khalid`  
**Teammates:** Muhammad Ali (Lead/Pipeline), Sajeel Malik (Frontend/Studio)  
**Supervisor:** Dr. Qammar Abbas | **Department:** FCSE, GIK Institute  

---

## 🌟 1. The Big Picture: Where You Fit in the Project

In **AI News Studio**, Muhammad Ali builds the news scraper and script generator. Ali produces a structured `Bulletin` containing story headlines, facts, and **written anchor scripts** (in Urdu and English). 

**Your mission is to bring those scripts to life:**
1. Turn Ali's written scripts into **studio-quality spoken voice** (Pakistani Urdu and English) using zero-cost neural TTS.
2. Calculate the exact duration of each audio clip down to the millisecond to build the **Timeline Synchronization Contract**.
3. Drive a **photorealistic talking avatar (Anchor A & Anchor B)** lip-synced to that audio using open-source tools (`Wav2Lip` / `SadTalker`).
4. Output finished `.mp3` and `.mp4` media files into `backend/media/` and update the bulletin with live media URLs.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           HASSAN'S PIPELINE WORKFLOW                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   Ali's Written Script (Urdu/EN)                                                │
│                 │                                                               │
│                 ▼                                                               │
│   [ 1. tts_engine.py (edge-tts) ] ──► Generates 'story_01_audio.mp3'            │
│                 │                                                               │
│                 ├─────────────────────┐                                         │
│                 ▼                     ▼                                         │
│     Extract Millisecond Duration   [ 2. avatar_engine.py (Wav2Lip) ]            │
│     (e.g., duration = 21.4s)          Anchor Photo/Video + Spoken Audio         │
│                 │                     ▼                                         │
│                 │                  Generates 'story_01_avatar.mp4'              │
│                 ▼                     │                                         │
│   [ 3. Update Timeline Contract ] ◄───┘                                         │
│     • start_time_sec = 0.0                                                      │
│     • duration_sec = 21.4                                                       │
│     • audio_url = "/media/audio/story_01.mp3"                                   │
│     • video_url = "/media/video/story_01.mp4"                                   │
│                 │                                                               │
│                 ▼                                                               │
│   Consumed by Sajeel's Web Studio Player                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 2. Tech Stack & Tools (100% Free)

| Subsystem | Tool | Purpose | Cost |
| :--- | :--- | :--- | :--- |
| **Neural TTS** | `edge-tts` (Python) | High-quality Pakistani Urdu & English voices with natural cadence | **$0** (No API keys needed) |
| **Audio Processing** | `mutagen` / `pydub` / `wave` | Measuring audio duration down to milliseconds | **$0** |
| **Avatar Lip-Sync** | `Wav2Lip` / `SadTalker` | Animating anchor faces to match spoken audio | **$0** (Run on local GPU or Google Colab T4) |
| **Media Composition**| `FFmpeg` | Stitching audio, intro stingers, and video clips | **$0** |

---

## 📦 3. Your Module Directory Structure

Work inside `backend/app/pipeline/` and create test scripts in `backend/app/audio_avatar/`:

```text
backend/
├── app/
│   ├── pipeline/
│   │   ├── tts_engine.py         # <-- YOUR PRIMARY FILE: Generates speech & timings
│   │   └── avatar_engine.py      # <-- YOUR PRIMARY FILE: Lip-sync orchestrator
│   └── schemas/
│       └── bulletin.py           # Contains the Pydantic schema you update
├── media/                        # Where your generated files live (gitignored)
│   ├── audio/                    # Output .mp3 files
│   ├── video/                    # Output .mp4 lip-synced clips
│   └── anchors/                  # Base high-res photos/videos of Anchor A and B
└── colab/
    └── wav2lip_news_studio.ipynb # Free Google Colab notebook for rendering avatars
```

---

## 🚀 4. Step-by-Step Implementation Guide

### Step 4.1: Setting Up Your Branch Locally
Clone the repository and checkout your designated branch:
```bash
git clone https://github.com/Mohammad-Ali-Soomro/AI-News-Studio.git
cd "AI-News-Studio"
git checkout hassan-khalid
git pull origin hassan-khalid
```

Install dependencies:
```bash
pip install -r backend/requirements.txt
pip install mutagen pydub
```

---

### Step 4.2: Mastering `edge-tts` for Pakistani Anchors
Microsoft Edge Neural TTS has built-in voices specifically for Pakistan.

#### The Voice Configuration:
- **Urdu Female Anchor (Anchor A - Uzma):** `"ur-PK-UzmaNeural"`
- **Urdu Male Anchor (Anchor B - Asad):** `"ur-PK-AsadNeural"`
- **English Female Anchor (Anchor A - Ava):** `"en-US-AvaNeural"`
- **English Male Anchor (Anchor B - Andrew):** `"en-US-AndrewMultilingualNeural"`

#### Enhancing `backend/app/pipeline/tts_engine.py`:
Open `backend/app/pipeline/tts_engine.py` and implement the production speech synthesizer:

```python
import asyncio
import os
import edge_tts
from mutagen.mp3 import MP3
from typing import Dict, Tuple

VOICE_MAP = {
    ("ur", "Anchor_A"): "ur-PK-UzmaNeural",   # Female Urdu Anchor
    ("ur", "Anchor_B"): "ur-PK-AsadNeural",   # Male Urdu Anchor
    ("en", "Anchor_A"): "en-US-AvaNeural",    # Female English Anchor
    ("en", "Anchor_B"): "en-US-AndrewMultilingualNeural", # Male English Anchor
}

async def synthesize_speech_file(
    text: str,
    language: str,
    anchor: str,
    output_filename: str
) -> Tuple[str, float]:
    """
    Synthesizes speech using edge-tts and computes its exact millisecond duration.
    Returns: (file_path, duration_in_seconds)
    """
    media_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "media", "audio"))
    os.makedirs(media_dir, exist_ok=True)
    
    file_path = os.path.join(media_dir, output_filename)
    voice = VOICE_MAP.get((language, anchor), "ur-PK-UzmaNeural" if language == "ur" else "en-US-AvaNeural")
    
    # Generate MP3
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(file_path)
    
    # Read exact audio duration using mutagen
    audio = MP3(file_path)
    duration_sec = round(audio.info.length, 2)
    
    return file_path, duration_sec
```

Test it immediately by running:
```bash
python backend/app/pipeline/tts_engine.py
```
Check `backend/media/audio/` and listen to the crystal-clear Urdu neural speech.

---

### Step 4.3: Generating the Timeline Timestamps
Once you have the durations for each story, update the `Bulletin` object:

```python
def process_bulletin_audio(bulletin):
    current_time = 0.0
    for story in bulletin.stories:
        filename = f"{bulletin.bulletin_id}_{story.story_id}.mp3"
        
        # 1. Synthesize audio
        filepath, duration = asyncio.run(
            synthesize_speech_file(
                text=story.spoken_script,
                language=story.language,
                anchor=story.anchor,
                output_filename=filename
            )
        )
        
        # 2. Tag timing boundaries
        story.start_time_sec = current_time
        story.duration_sec = duration
        story.audio_url = f"/media/audio/{filename}"
        
        # Advance timeline
        current_time += duration
        
    bulletin.total_duration_sec = round(current_time, 2)
    return bulletin
```
**Why this is crucial:** Sajeel's player relies on `start_time_sec` and `duration_sec` to know the exact split second to change the Insight Panel facts and Ticker lines!

---

### Step 4.4: The Avatar Lip-Sync Engine (`avatar_engine.py`)
This is where the magic happens that will stun your evaluation committee.

#### How It Works:
1. **Anchor Persona Setup:**
   - Choose or generate 2 photorealistic portrait photos or 5-second idling loop videos of Pakistani anchors seated at a modern studio desk:
     - `backend/media/anchors/anchor_a.png` (Female professional anchor)
     - `backend/media/anchors/anchor_b.png` (Male professional anchor)
2. **Lip-Sync via `Wav2Lip`:**
   - `Wav2Lip` takes:
     - Input 1: The Face Image / Video (`anchor_a.png`)
     - Input 2: The Generated Speech Audio (`story_01_audio.mp3`)
   - It outputs: `story_01_avatar.mp4` where the anchor's lips move in perfect sync with the Urdu/English words!

#### Running on Free Google Colab:
If your local laptop doesn't have an Nvidia RTX GPU, create a Colab notebook with a free T4 GPU:
```python
# Colab Cell 1: Clone Wav2Lip
!git clone https://github.com/Rudrabha/Wav2Lip.git
!cd Wav2Lip && pip install -r requirements.txt
!wget -O Wav2Lip/checkpoints/wav2lip_gan.pth "https://huggingface.co/Akumzy/wav2lip-gan/resolve/main/wav2lip_gan.pth"

# Colab Cell 2: Run Lip-sync for a story
!python Wav2Lip/inference.py \
    --checkpoint_path Wav2Lip/checkpoints/wav2lip_gan.pth \
    --face "anchor_a.png" \
    --audio "story_01_audio.mp3" \
    --outfile "story_01_avatar.mp4"
```

Save the generated `.mp4` into `backend/media/video/` and set `story.video_url = "/media/video/story_01_avatar.mp4"`.

---

## 🧪 5. Testing & Verification Checklist

Before pushing to your branch or requesting a merge into `main`:
- [ ] Run `python backend/app/pipeline/tts_engine.py`: Audio file is created without error.
- [ ] Verify both `ur-PK-UzmaNeural` and `ur-PK-AsadNeural` sound natural.
- [ ] Verify audio duration is correctly tagged in seconds (e.g. `24.5` sec).
- [ ] Test a sample video generation with Wav2Lip on Colab or locally.
- [ ] Check that `backend/media/` outputs are not committed to git (kept in `.gitignore`).

---

## 🌿 6. Git Workflow for Hassan

Always stay in your branch while developing:
```bash
# Check branch status
git status
git branch

# Add and commit your changes
git add backend/app/pipeline/tts_engine.py backend/app/pipeline/avatar_engine.py
git commit -m "feat(hassan): integrate edge-tts audio synthesis and duration calculation"

# Push to your remote branch
git push origin hassan-khalid
```

When you are ready to integrate with Ali and Sajeel, let Ali know to test and merge into `main`!
