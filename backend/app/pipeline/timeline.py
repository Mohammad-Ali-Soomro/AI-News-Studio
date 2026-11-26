from backend.app.schemas.bulletin import Bulletin

DEFAULT_STORY_GAP_SEC = 0.6


def compute_bulletin_timeline(
    bulletin: Bulletin, gap_sec: float = DEFAULT_STORY_GAP_SEC
) -> Bulletin:
    """
    Compute start_time_sec for each story from story durations and a configurable
    inter-story gap, and update bulletin.total_duration_sec.
    """
    if gap_sec < 0:
        raise ValueError("gap_sec must be non-negative.")

    if not bulletin.stories:
        bulletin.total_duration_sec = 0.0
        return bulletin

    cursor = 0.0
    for story in bulletin.stories:
        duration = max(0.0, float(story.duration_sec))
        story.start_time_sec = round(cursor, 3)
        story.duration_sec = round(duration, 3)
        cursor += duration + gap_sec

    last_story = bulletin.stories[-1]
    bulletin.total_duration_sec = round(
        last_story.start_time_sec + last_story.duration_sec, 3
    )
    return bulletin
