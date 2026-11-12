# Timeline Synchronization Contract

## Overview
One of the most praised aspects of the AI News Studio architecture is the **Synchronized Presentation Layer**:
The anchor voice, avatar video, insight panel cards, and live news ticker are all anchored to a single timeline contract.

```
ANCHOR VOICE:     |--- Story 1 (Anchor A) ---|--- Story 2 (Anchor B) ---|
INSIGHT PANEL:    |--- Facts for Story 1 ----|--- Facts for Story 2 ----|
TICKER:           |--- Ticker Headline 1 ----|--- Ticker Headline 2 ----|
TIMELINE:        t0                         t1                         t2
```

## JSON Schema Example
```json
{
  "bulletin_id": "bulletin-2026-11-12-001",
  "language": "ur",
  "total_duration_sec": 45.2,
  "stories": [
    {
      "story_id": "story-01",
      "category": "National",
      "anchor": "Anchor_A",
      "headline": "پاکستان میں معاشی اصلاحات کا نیا پیکج",
      "ticker_text": "بریکنگ نیوز: اقتصادی کونسل کا اہم اجلاس، معاشی پیکج کی منظوری",
      "spoken_script": "السلام علیکم، نیوز سٹوڈیو میں خوش آمدید۔ حکومت نے آج نئے معاشی اصلاحات پیکج کا اعلان کر دیا ہے...",
      "source": {
        "title": "Govt approves comprehensive economic package",
        "publisher": "Dawn",
        "source_url": "https://www.dawn.com/news/..."
      },
      "insight_panel": [
        {"key": "حجم", "value": "1.2 ارب ڈالر"},
        {"key": "شعبہ", "value": "صنعت اور تجارت"},
        {"key": "ماخذ", "value": "ڈان نیوز"}
      ],
      "start_time_sec": 0.0,
      "duration_sec": 22.5,
      "audio_url": "/media/audio_story_01.mp3",
      "video_url": "/media/avatar_story_01.mp4"
    }
  ]
}
```

## How the Web Player Syncs
1. The web audio/video player broadcasts `timeupdate` events (or current playback time in seconds).
2. The UI computes the active story:
   ```javascript
   const activeStory = bulletin.stories.find(
     (s) => currentTime >= s.start_time_sec && currentTime < (s.start_time_sec + s.duration_sec)
   );
   ```
3. The **Insight Panel** and **Ticker** automatically render the data of `activeStory`.
4. When `activeStory` changes, smooth CSS/Framer-Motion transitions swap the panels without lag.
