from dataclasses import dataclass, field
import re
from typing import Any, Dict, List

from backend.app.pipeline.prompts import ALLOWED_CATEGORIES
from backend.app.schemas.bulletin import StoryRundown

MIN_SCRIPT_WORDS = 35
MAX_SCRIPT_WORDS = 60
MIN_URDU_LETTER_RATIO = 0.80
REQUIRED_INSIGHT_COUNT = 3
MIN_TICKER_CHARS = 15
MAX_TICKER_CHARS = 180

# Urdu/Eastern Arabic digits -> ASCII digits
DIGIT_TRANSLATION_TABLE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

# Match numbers including optional commas/decimals like 1,200 or 3.5
NUMBER_PATTERN = re.compile(r"\d+(?:,\d+)*(?:\.\d+)?")
# Match capitalized English words/acronyms of 2+ characters
CAPITALIZED_ENTITY_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9\-]{1,}\b")


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


def normalize_digits(text: str) -> str:
    """Convert Urdu and Arabic-Indic digits to standard ASCII digits."""
    return (text or "").translate(DIGIT_TRANSLATION_TABLE)


def extract_numbers(text: str) -> List[str]:
    """Extract normalized numeric tokens (stripping thousands commas)."""
    normalized = normalize_digits(text)
    raw_matches = NUMBER_PATTERN.findall(normalized)
    return [m.replace(",", "") for m in raw_matches]


def extract_capitalized_entities(text: str) -> List[str]:
    """Extract capitalized Latin tokens (proper nouns, acronyms)."""
    return CAPITALIZED_ENTITY_PATTERN.findall(text or "")


def compute_urdu_letter_ratio(text: str) -> float:
    """
    Compute the ratio of Urdu/Arabic script letters to all alphabetic characters.
    Digits, spaces, and punctuation are ignored.
    """
    urdu_letters = 0
    total_letters = 0
    for ch in text or "":
        code = ord(ch)
        is_urdu_char = (
            (0x0600 <= code <= 0x06FF)
            or (0x0750 <= code <= 0x077F)
            or (0xFB50 <= code <= 0xFDFF)
            or (0xFE70 <= code <= 0xFEFF)
        )
        if is_urdu_char and ch.isalpha():
            urdu_letters += 1
            total_letters += 1
        elif ch.isalpha():
            total_letters += 1

    if total_letters == 0:
        return 0.0
    return urdu_letters / total_letters


def build_source_corpus(cluster: Dict) -> str:
    """Combine all available source fields of a cluster for faithfulness checking."""
    parts = [
        cluster.get("title", ""),
        cluster.get("aggregated_body", ""),
    ]
    for src in cluster.get("sources", []):
        parts.append(src.get("title", ""))
        parts.append(src.get("publisher", ""))
    for pub in cluster.get("publishers", []):
        parts.append(pub)
    return " ".join(p for p in parts if p)


def validate_story(story: StoryRundown, cluster: Dict) -> ValidationResult:
    """
    Validate one generated Urdu story against broadcast length, script ratio,
    faithfulness (numbers and English entities), insight count, and ticker rules.
    """
    errors: List[str] = []

    words = story.spoken_script.strip().split()
    word_count = len(words)
    if word_count < MIN_SCRIPT_WORDS or word_count > MAX_SCRIPT_WORDS:
        errors.append(
            f"Word count {word_count} outside required {MIN_SCRIPT_WORDS}-{MAX_SCRIPT_WORDS} range."
        )

    urdu_ratio = compute_urdu_letter_ratio(story.spoken_script)
    if urdu_ratio < MIN_URDU_LETTER_RATIO:
        errors.append(
            f"Urdu script ratio {urdu_ratio:.2f} is below required {MIN_URDU_LETTER_RATIO:.2f}."
        )

    if len(story.insight_panel) != REQUIRED_INSIGHT_COUNT:
        errors.append(
            f"Expected {REQUIRED_INSIGHT_COUNT} insight facts, got {len(story.insight_panel)}."
        )
    elif any(
        not fact.key.strip() or not fact.value.strip() for fact in story.insight_panel
    ):
        errors.append("Insight facts must have non-empty key and value.")

    ticker_len = len(story.ticker_text.strip())
    if ticker_len < MIN_TICKER_CHARS or ticker_len > MAX_TICKER_CHARS:
        errors.append(
            f"Ticker length {ticker_len} chars outside {MIN_TICKER_CHARS}-{MAX_TICKER_CHARS} range."
        )

    if story.category not in ALLOWED_CATEGORIES:
        errors.append(
            f"Category '{story.category}' must be one of {ALLOWED_CATEGORIES}."
        )

    # Faithfulness check across script, headline, ticker, and insight panel
    source_text = build_source_corpus(cluster)
    source_numbers = set(extract_numbers(source_text))
    # Also allow substring matching for numbers embedded in tokens (e.g. "2024-25" or "12th")
    source_normalized = normalize_digits(source_text).replace(",", "")

    generated_fragments = [
        story.spoken_script,
        story.headline,
        story.ticker_text,
    ]
    for fact in story.insight_panel:
        generated_fragments.append(fact.key)
        generated_fragments.append(fact.value)
    generated_text = " ".join(generated_fragments)

    missing_numbers = []
    for num in extract_numbers(generated_text):
        if num not in source_numbers and not re.search(
            rf"(?<!\d){re.escape(num)}(?!\d)", source_normalized
        ):
            missing_numbers.append(num)
    if missing_numbers:
        errors.append(
            f"Invented or unverified number(s) not in source: {sorted(set(missing_numbers))}."
        )

    missing_entities = []
    for entity in extract_capitalized_entities(generated_text):
        if not re.search(rf"\b{re.escape(entity)}\b", source_text, re.IGNORECASE):
            missing_entities.append(entity)
    if missing_entities:
        errors.append(
            f"Unverified English entity/entities not in source: {sorted(set(missing_entities))}."
        )

    metrics = {
        "word_count": word_count,
        "urdu_ratio": round(urdu_ratio, 3),
        "insight_count": len(story.insight_panel),
        "ticker_chars": ticker_len,
        "missing_numbers": sorted(set(missing_numbers)),
        "missing_entities": sorted(set(missing_entities)),
    }

    return ValidationResult(is_valid=(len(errors) == 0), errors=errors, metrics=metrics)
