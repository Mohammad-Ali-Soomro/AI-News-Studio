from abc import ABC, abstractmethod
import argparse
import asyncio
import logging
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import edge_tts
from mutagen.mp3 import MP3

from backend.app.core.config import get_settings
from backend.app.pipeline.timeline import (
    DEFAULT_STORY_GAP_SEC,
    compute_bulletin_timeline,
)
from backend.app.schemas.bulletin import Bulletin
from backend.app.services.supabase_client import (
    is_supabase_configured,
    upload_audio,
)

logger = logging.getLogger(__name__)

DEFAULT_URDU_VOICE = "ur-PK-UzmaNeural"
ALT_URDU_VOICE = "ur-PK-AsadNeural"

VOICE_MAP = {
    ("ur", "Anchor_A"): DEFAULT_URDU_VOICE,
    ("ur", "Anchor_B"): ALT_URDU_VOICE,
    ("en", "Anchor_A"): "en-US-AvaNeural",
    ("en", "Anchor_B"): "en-US-AndrewNeural",
}

# Extend this dictionary to customize how abbreviations are spoken in Urdu TTS.
ABBREVIATIONS: Dict[str, str] = {
    "IBOs": "انٹیلی جنس بیسڈ آپریشنز",
    "IBO": "انٹیلی جنس بیسڈ آپریشن",
    "JUI-F": "جے یو آئی ایف",
    "PML-N": "مسلم لیگ ن",
    "NADRA": "نادرا",
    "WAPDA": "واپڈا",
    "ISPR": "آئی ایس پی آر",
    "CPEC": "سی پیک",
    "SBP": "اسٹیٹ بینک آف پاکستان",
    "IMF": "آئی ایم ایف",
    "ECP": "الیکشن کمیشن آف پاکستان",
    "FBR": "ایف بی آر",
    "FIA": "ایف آئی اے",
    "GDP": "جی ڈی پی",
    "PKR": "پاکستانی روپے",
    "USD": "امریکی ڈالر",
    "ATC": "انسداد دہشت گردی عدالت",
    "PCB": "پاکستان کرکٹ بورڈ",
    "PIA": "پی آئی اے",
    "PTI": "پی ٹی آئی",
    "PPP": "پیپلز پارٹی",
    "PM": "وزیر اعظم",
    "UN": "اقوام متحدہ",
    "MNA": "رکن قومی اسمبلی",
}

DIGIT_TRANSLATION_TABLE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


class TTSProvider(ABC):
    """Abstract text-to-speech provider interface."""

    @abstractmethod
    async def synthesize(self, text: str, voice: str, out_path: Path | str) -> None:
        """Synthesize spoken audio from text and write it to out_path."""


class EdgeTTSProvider(TTSProvider):
    """Free Microsoft Edge Neural TTS provider using edge-tts."""

    async def synthesize(self, text: str, voice: str, out_path: Path | str) -> None:
        target = Path(out_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(target))


class AzureSpeechProvider(TTSProvider):
    """Backup Azure Cognitive Services Speech stub (not implemented)."""

    async def synthesize(self, text: str, voice: str, out_path: Path | str) -> None:
        raise NotImplementedError(
            "AzureSpeechProvider is a backup stub. Implement with azure-cognitiveservices-speech if edge-tts is unavailable."
        )


def clean_text_for_tts(
    text: str, abbreviations: Optional[Dict[str, str]] = None
) -> str:
    """
    Prepare Urdu broadcast text for natural TTS pronunciation:
    - Strip markdown artifacts
    - Normalize Urdu/Arabic digits to standard digits and remove numeric commas
    - Expand common English abbreviations into spoken Urdu forms
    - Normalize Urdu punctuation and whitespace
    """
    if not text:
        return ""

    cleaned = re.sub(r"[*_`~]+", "", text.strip())

    # Convert Urdu/Eastern Arabic digits to ASCII digits for consistent TTS reading
    cleaned = cleaned.translate(DIGIT_TRANSLATION_TABLE)
    # Remove thousands separator commas inside numbers (e.g. 1,200 -> 1200)
    cleaned = re.sub(r"(?<=\d),(?=\d)", "", cleaned)

    # Expand abbreviations (longest keys first)
    abbr_map = abbreviations if abbreviations is not None else ABBREVIATIONS
    for abbr in sorted(abbr_map.keys(), key=len, reverse=True):
        replacement = abbr_map[abbr]
        pattern = re.compile(
            rf"(?<![A-Za-z0-9]){re.escape(abbr)}(?![A-Za-z0-9])",
            flags=re.IGNORECASE,
        )
        cleaned = pattern.sub(replacement, cleaned)

    # Ensure spacing between numbers and adjacent Urdu script characters
    cleaned = re.sub(r"([\u0600-\u06FF])(\d)", r"\1 \2", cleaned)
    cleaned = re.sub(r"(\d)([\u0600-\u06FF])", r"\1 \2", cleaned)

    # Normalize Urdu punctuation (collapse repeats, space after sentence/clause marks)
    cleaned = re.sub(r"۔+", "۔", cleaned)
    cleaned = re.sub(r"،+", "،", cleaned)
    cleaned = re.sub(r"؟+", "؟", cleaned)
    cleaned = re.sub(r"([۔،؟])(?=\S)", r"\1 ", cleaned)

    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def measure_mp3_duration(mp3_path: Path | str) -> float:
    """Measure exact MP3 duration in seconds using mutagen."""
    audio = MP3(str(mp3_path))
    return float(audio.info.length)


async def synthesize_with_retries(
    provider: TTSProvider,
    text: str,
    voice: str,
    out_path: Path,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> None:
    """Synthesize audio retrying up to max_retries times with exponential backoff."""
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            await provider.synthesize(text, voice, out_path)
            return
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                logger.warning(
                    "TTS synthesis failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    max_retries,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc


async def synthesize_bulletin_audio(
    bulletin: Bulletin,
    provider: Optional[TTSProvider] = None,
    default_voice: str = DEFAULT_URDU_VOICE,
    gap_sec: float = DEFAULT_STORY_GAP_SEC,
    upload_to_supabase: bool = True,
    media_dir: Optional[Path | str] = None,
    duration_fn=measure_mp3_duration,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Tuple[Bulletin, Dict[str, Any]]:
    """
    Synthesize MP3 files for each story in a bulletin, measure exact durations,
    upload to Supabase Storage (or serve from /media locally), and compute the timeline.
    Stories whose TTS keeps failing after retries are skipped and logged.
    """
    active_provider = provider if provider is not None else EdgeTTSProvider()
    settings = get_settings()
    base_media = Path(media_dir) if media_dir is not None else Path(settings.MEDIA_STORAGE_DIR)
    audio_dir = base_media / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    use_supabase = upload_to_supabase and is_supabase_configured()
    kept_stories = []
    skipped_reasons: List[Dict[str, str]] = []

    for idx, story in enumerate(bulletin.stories):
        if idx > 0 and base_delay > 0:
            await asyncio.sleep(0.8)
        voice = VOICE_MAP.get((story.language, story.anchor), default_voice)
        filename = f"{bulletin.bulletin_id}_{story.story_id}.mp3"
        out_path = audio_dir / filename
        cleaned_text = clean_text_for_tts(story.spoken_script)

        try:
            await synthesize_with_retries(
                active_provider,
                cleaned_text,
                voice,
                out_path,
                max_retries=max_retries,
                base_delay=base_delay,
            )
            story.duration_sec = round(float(duration_fn(out_path)), 3)
        except Exception as exc:
            reason = f"TTS failed after {max_retries} attempts: {exc}"
            logger.error("Skipping %s: %s", story.story_id, reason)
            skipped_reasons.append({"story_id": story.story_id, "reason": reason})
            continue

        if use_supabase:
            story.audio_url = upload_audio(out_path, f"audio/{filename}")
        else:
            story.audio_url = f"/media/audio/{filename}"

        kept_stories.append(story)

    bulletin.stories = kept_stories
    compute_bulletin_timeline(bulletin, gap_sec=gap_sec)

    report = {
        "synthesized": len(kept_stories),
        "skipped": len(skipped_reasons),
        "skipped_reasons": skipped_reasons,
        "total_duration_sec": bulletin.total_duration_sec,
        "voice": default_voice,
    }
    return bulletin, report


async def list_urdu_voices() -> List[Dict[str, Any]]:
    """Fetch all Urdu voices from edge-tts."""
    voices = await edge_tts.list_voices()
    return [v for v in voices if str(v.get("Locale", "")).lower().startswith("ur")]


async def generate_speech(
    text: str,
    language: str = "ur",
    anchor: str = "Anchor_A",
    output_filepath: str = "output.mp3",
) -> str:
    """Compatibility helper for single-clip synthesis."""
    voice = VOICE_MAP.get(
        (language, anchor),
        DEFAULT_URDU_VOICE if language == "ur" else "en-US-AndrewNeural",
    )
    provider = EdgeTTSProvider()
    cleaned = clean_text_for_tts(text) if language == "ur" else text
    await provider.synthesize(cleaned, voice, output_filepath)
    return output_filepath


async def generate_voice_comparison_samples(
    sample_text: str, media_dir: Optional[Path | str] = None
) -> Dict[str, Path]:
    """Generate short MP3 samples for both Uzma and Asad Urdu voices."""
    settings = get_settings()
    base_media = Path(media_dir) if media_dir is not None else Path(settings.MEDIA_STORAGE_DIR)
    samples_dir = base_media / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    provider = EdgeTTSProvider()
    cleaned = clean_text_for_tts(sample_text)
    outputs = {
        DEFAULT_URDU_VOICE: samples_dir / "sample_uzma.mp3",
        ALT_URDU_VOICE: samples_dir / "sample_asad.mp3",
    }
    for voice, path in outputs.items():
        await synthesize_with_retries(provider, cleaned, voice, path)
    return outputs


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="AI News Studio Urdu TTS and Timeline Engine"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available Urdu voices from edge-tts",
    )
    parser.add_argument(
        "--bulletin",
        type=str,
        help="Path to a bulletin JSON file to synthesize and add timeline fields",
    )
    parser.add_argument(
        "--out",
        type=str,
        help="Optional output path for updated bulletin JSON (defaults to --bulletin)",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=DEFAULT_URDU_VOICE,
        help=f"Override default voice (default: {DEFAULT_URDU_VOICE})",
    )
    parser.add_argument(
        "--gap",
        type=float,
        default=DEFAULT_STORY_GAP_SEC,
        help=f"Gap in seconds between stories (default: {DEFAULT_STORY_GAP_SEC})",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip Supabase upload even if configured (sets local /media/audio URLs)",
    )
    parser.add_argument(
        "--sample-voices",
        action="store_true",
        help="Generate short MP3 samples with both Uzma and Asad voices",
    )

    args = parser.parse_args(argv)

    if args.list:
        voices = asyncio.run(list_urdu_voices())
        short_names = {v.get("ShortName") for v in voices}
        print("Available Urdu voices from edge-tts:")
        for v in voices:
            print(
                f"  - {v.get('ShortName')} | Locale: {v.get('Locale')} | Gender: {v.get('Gender')}"
            )
        print(f"Confirmed {DEFAULT_URDU_VOICE}: {DEFAULT_URDU_VOICE in short_names}")
        print(f"Confirmed {ALT_URDU_VOICE}: {ALT_URDU_VOICE in short_names}")
        return 0

    if args.sample_voices:
        sample_text = (
            "السلام علیکم، اے آئی نیوز اسٹوڈیو میں خوش آمدید۔ "
            "ڈان کے مطابق آج پاکستان کی معاشی صورتحال پر اہم اجلاس منعقد ہوا۔"
        )
        if args.bulletin and Path(args.bulletin).exists():
            b = Bulletin.model_validate_json(
                Path(args.bulletin).read_text(encoding="utf-8")
            )
            if b.stories:
                sample_text = b.stories[0].spoken_script
        paths = asyncio.run(generate_voice_comparison_samples(sample_text))
        for voice, path in paths.items():
            dur = measure_mp3_duration(path)
            print(f"Voice sample [{voice}]: {path} ({dur:.2f}s)")
        return 0

    if args.bulletin:
        bulletin_path = Path(args.bulletin)
        if not bulletin_path.exists():
            print(f"ERROR: Bulletin file not found: {bulletin_path}")
            return 1

        bulletin = Bulletin.model_validate_json(
            bulletin_path.read_text(encoding="utf-8")
        )
        updated, report = asyncio.run(
            synthesize_bulletin_audio(
                bulletin,
                default_voice=args.voice,
                gap_sec=args.gap,
                upload_to_supabase=not args.no_upload,
            )
        )
        out_path = Path(args.out) if args.out else bulletin_path
        out_path.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
        print(f"TTS Report: {report}")
        print(f"Updated bulletin written to: {out_path}")
        for story in updated.stories:
            print(
                f"  {story.story_id}: start={story.start_time_sec}s, "
                f"duration={story.duration_sec}s, audio_url={story.audio_url}"
            )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
