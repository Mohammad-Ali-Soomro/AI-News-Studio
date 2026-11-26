from typing import Dict, List

ALLOWED_CATEGORIES = ("National", "Economy", "World", "Sports", "Technology")

PUBLISHER_URDU_NAMES = {
    "Dawn": "ڈان",
    "Express Tribune": "ایکسپریس ٹریبیون",
}


def _format_cluster_block(idx: int, cluster: Dict) -> str:
    publishers = cluster.get("publishers", [])
    urdu_pubs = [PUBLISHER_URDU_NAMES.get(p, p) for p in publishers]
    source_text = (cluster.get("aggregated_body") or "").strip()
    if len(source_text) > 1200:
        source_text = source_text[:1200]
    return (
        f"Story #{idx}:\n"
        f"- Cluster ID: {cluster.get('cluster_id', f'cluster_{idx}')}\n"
        f"- Headline: {cluster.get('title', '')}\n"
        f"- Publishers: {', '.join(publishers)} (Urdu attribution: {', '.join(urdu_pubs)})\n"
        f"- Primary URL: {cluster.get('primary_source_url', '')}\n"
        f"- Source Text: {source_text}\n"
    )


def build_bulletin_prompt(clusters: List[Dict], language: str = "ur") -> str:
    """
    Build the single-call broadcast prompt for 3 to 5 story clusters.
    Prompts live here rather than inline in script_generator.py.
    """
    stories_context = "\n".join(
        _format_cluster_block(i, c) for i, c in enumerate(clusters, 1)
    )
    total = len(clusters)

    if language != "ur":
        return (
            "You are the Executive Producer for AI News Studio.\n"
            "Transform the source stories below into an objective English TV news bulletin.\n"
            "Rules:\n"
            "- If the source does not say it, do not say it.\n"
            "- Spoken script: 35 to 60 words per story.\n"
            "- Assign anchor 'Anchor_A' to every story.\n"
            f"- Category must be one of: {', '.join(ALLOWED_CATEGORIES)}.\n"
            "- Exactly 3 insight_panel facts per story.\n\n"
            f"RAW SOURCE STORIES ({total} total):\n{stories_context}"
        )

    return f"""You are the Executive Producer for AI News Studio, a formal Pakistani Urdu television news channel.
Transform the {total} source stories below into one broadcast bulletin in formal Pakistani TV news Urdu.

STRICT JOURNALISTIC RULES:
1. Grounding ("if the source does not say it, do not say it"):
   - Use ONLY facts, names, locations, dates, and numbers explicitly present in that story's Source Text or Headline.
   - Never invent numbers, statistics, quotes, causes, or background claims.
   - Keep numbers written accurately and matching the source values (use standard digits or Urdu digits matching the exact number in the source).
   - Keep proper nouns accurate. Write natural, idiomatic broadcast Urdu (avoid awkward literal transliterations like "چارج کیا گیا" or "کنٹری ہوم"; use natural Urdu equivalents like "فرد جرم عائد کی گئی" or "رہائش گاہ").
   - Use clear punctuation (، and ۔) and short, crisp clauses so the anchor speaks with natural pauses rather than run-on sentences.
   - At least 80 percent of letters in spoken_script must be Urdu script.
   - No opinions, speculation, or editorializing.
2. Broadcast Structure and Word Count:
   - Total stories: {total}, preserving the exact order (Story #1 to Story #{total}).
   - Each story's spoken_script MUST be between 35 and 60 Urdu words (count space-separated words carefully).
   - Opening greeting ONLY in Story #1 (for example: "السلام علیکم، اے آئی نیوز اسٹوڈیو میں خوش آمدید۔"). Do NOT put greetings in Story #2 through Story #{total}.
   - Short closing ONLY at the end of Story #{total} (for example: "یہ تھا اب تک کا خبرنامہ، مزید خبروں کے لیے ہمارے ساتھ رہیے۔").
   - Attribute each story naturally to its publisher in Urdu (for example: "ڈان کے مطابق" or "ایکسپریس ٹریبیون کے مطابق").
3. Fields per Story:
   - story_id: "story_1", "story_2", ...
   - category: one of {", ".join(ALLOWED_CATEGORIES)}
   - anchor: always "Anchor_A"
   - language: "ur"
   - headline: concise Urdu news headline (5 to 12 words).
   - ticker_text: concise Urdu breaking-news ticker line (8 to 18 words, around 40 to 130 characters).
   - spoken_script: 35 to 60 words of formal broadcast Urdu.
   - insight_panel: EXACTLY 3 key-value facts in Urdu extracted strictly from the source (for example keys: "اہم نکتہ", "مقام", "ماخذ"). Every number or English entity in insight_panel must exist in the source text.
   - source: keep the exact title, publisher, and source_url from the input story.

RAW SOURCE STORIES:
{stories_context}
"""


def build_story_retry_prompt(
    cluster: Dict,
    position: int,
    total_stories: int,
    failure_reasons: List[str],
) -> str:
    """
    Build a targeted single-story retry prompt explaining why validation failed.
    """
    story_block = _format_cluster_block(position, cluster)
    reasons_text = "\n".join(f"- {reason}" for reason in failure_reasons)

    greeting_rule = (
        'Include a brief opening greeting ("السلام علیکم، اے آئی نیوز اسٹوڈیو میں خوش آمدید۔") at the start.'
        if position == 1
        else "Do NOT include any opening greeting."
    )
    closing_rule = (
        'Include a brief closing line ("یہ تھا اب تک کا خبرنامہ، مزید خبروں کے لیے ہمارے ساتھ رہیے۔") at the end.'
        if position == total_stories
        else "Do NOT include a closing sign-off."
    )

    return f"""Fix and regenerate ONLY Story #{position} (out of {total_stories}) in formal Pakistani TV news Urdu.

The previous draft FAILED validation for these reasons:
{reasons_text}

REQUIREMENTS TO SATISFY:
- If the source does not say it, do not say it.
- spoken_script MUST be strictly between 35 and 60 Urdu words.
- At least 80 percent of alphabetic characters in spoken_script must be Urdu script (avoid English words unless a proper noun from the source requires it).
- Every digit/number and every English capitalized entity in spoken_script, headline, ticker_text, or insight_panel MUST appear in the Source Text below.
- Attribute the report to its publisher in Urdu ("ڈان کے مطابق" or "ایکسپریس ٹریبیون کے مطابق").
- {greeting_rule}
- {closing_rule}
- Return anchor "Anchor_A", language "ur", category from ({", ".join(ALLOWED_CATEGORIES)}), ticker_text of 8 to 18 words, and EXACTLY 3 Urdu insight_panel items.

SOURCE STORY:
{story_block}
"""
