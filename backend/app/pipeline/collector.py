import logging
import re
from typing import Dict, List, Optional

import feedparser
import httpx
from bs4 import BeautifulSoup

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

# Verified RSS feed registry for Pakistani news publishers
NEWS_FEEDS: Dict[str, str] = {
    "Dawn": "https://www.dawn.com/feeds/home",
    "Express Tribune": "https://tribune.com.pk/feed/latest",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

FEED_TIMEOUT_SEC = 10.0
SCRAPE_TIMEOUT_SEC = 6.0


def clean_html(raw_html: str) -> str:
    """Remove HTML tags, scripts, and excessive whitespace."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text)


def scrape_full_article_body(url: str, publisher: str) -> Optional[str]:
    """
    Attempt to fetch the full body text of an article from the source website.
    Returns None on error or timeout so callers fall back to the RSS summary.
    """
    try:
        with httpx.Client(
            headers=HEADERS, timeout=SCRAPE_TIMEOUT_SEC, follow_redirects=True
        ) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            paragraphs: List[str] = []

            if publisher == "Dawn":
                content_div = soup.find(
                    "div", class_=re.compile(r"story__content|story-content")
                )
                if content_div:
                    paragraphs = [
                        p.get_text(strip=True) for p in content_div.find_all("p")
                    ]
            elif publisher == "Express Tribune":
                content_div = soup.find(
                    "div", class_=re.compile(r"story-text|story__content")
                )
                if content_div:
                    paragraphs = [
                        p.get_text(strip=True) for p in content_div.find_all("p")
                    ]

            if not paragraphs:
                article_tag = soup.find("article")
                if article_tag:
                    paragraphs = [
                        p.get_text(strip=True) for p in article_tag.find_all("p")
                    ]
                else:
                    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]

            meaningful_paras = [
                p
                for p in paragraphs
                if len(p) > 40 and not p.startswith("Copyright")
            ]
            if meaningful_paras:
                return " ".join(meaningful_paras[:6])
    except Exception as exc:
        logger.warning("Could not scrape full body for %s: %s", url, exc)

    return None


def fetch_feed_entries(publisher: str, feed_url: str) -> List:
    """Fetch an RSS feed with a 10-second timeout via httpx and parse entries."""
    with httpx.Client(
        headers=HEADERS, timeout=FEED_TIMEOUT_SEC, follow_redirects=True
    ) as client:
        resp = client.get(feed_url)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.text)
        if getattr(parsed, "bozo", False) and not parsed.entries:
            raise ValueError(f"Malformed RSS feed for {publisher}: {parsed.bozo_exception}")
        return list(parsed.entries)


def fetch_rss_articles(
    limit_per_feed: Optional[int] = None,
    fetch_full_body: bool = True,
    feeds: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    """
    Fetch raw news stories from the configured RSS feeds.
    A failure in one feed is logged and does not stop the remaining feeds.
    """
    if limit_per_feed is None:
        limit_per_feed = get_settings().MAX_ARTICLES_PER_FEED

    feed_registry = feeds if feeds is not None else NEWS_FEEDS
    collected_articles: List[Dict] = []

    for publisher, feed_url in feed_registry.items():
        try:
            entries = fetch_feed_entries(publisher, feed_url)
            feed_articles: List[Dict] = []

            for entry in entries[:limit_per_feed]:
                title = clean_html(getattr(entry, "title", "No Title"))
                summary = clean_html(getattr(entry, "summary", ""))
                link = getattr(entry, "link", "")
                published_at = getattr(entry, "published", "")

                body_text = summary
                if fetch_full_body and link:
                    full_body = scrape_full_article_body(link, publisher)
                    if full_body and len(full_body) > len(summary):
                        body_text = full_body

                feed_articles.append(
                    {
                        "title": title,
                        "summary": summary,
                        "body_text": body_text,
                        "source_url": link,
                        "published_at": published_at,
                        "publisher": publisher,
                    }
                )

            collected_articles.extend(feed_articles)
            logger.info(
                "Feed '%s' returned %d article(s).", publisher, len(feed_articles)
            )
        except Exception as exc:
            logger.error("Feed '%s' (%s) failed: %s", publisher, feed_url, exc)

    return collected_articles


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    print("Testing Collector with Full Article Scraping...")
    articles = fetch_rss_articles(limit_per_feed=2, fetch_full_body=True)
    print(f"\nSuccessfully collected {len(articles)} articles:")
    for i, art in enumerate(articles, 1):
        print(f"\n[{i}] [{art['publisher']}] {art['title']}")
        print(f"    URL: {art['source_url']}")
        print(f"    Body Sample: {art['body_text'][:160]}...")
