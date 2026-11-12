import feedparser
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re

# Verified RSS feeds from top Pakistani & International publishers
NEWS_FEEDS = {
    "Dawn": "https://www.dawn.com/feeds/home",
    "Express Tribune": "https://tribune.com.pk/feed/latest",
    "Reuters World": "https://www.reutersagency.com/feed/?taxonomy=markets&post_type=reuters_media"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_html(raw_html: str) -> str:
    """Removes HTML tags, scripts, and excessive whitespace."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r'\s+', ' ', text)
    return text

def scrape_full_article_body(url: str, publisher: str) -> Optional[str]:
    """
    Attempts to fetch the full body text of the article from the source website.
    If scraping fails or times out, gracefully returns None to fallback to RSS summary.
    """
    try:
        with httpx.Client(headers=HEADERS, timeout=6.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            paragraphs = []
            
            if publisher == "Dawn":
                content_div = soup.find("div", class_=re.compile(r"story__content|story-content"))
                if content_div:
                    paragraphs = [p.get_text(strip=True) for p in content_div.find_all("p")]
            elif publisher == "Express Tribune":
                content_div = soup.find("div", class_=re.compile(r"story-text|story__content"))
                if content_div:
                    paragraphs = [p.get_text(strip=True) for p in content_div.find_all("p")]
            
            # Generic fallback if publisher-specific selectors didn't find paragraphs
            if not paragraphs:
                article_tag = soup.find("article")
                if article_tag:
                    paragraphs = [p.get_text(strip=True) for p in article_tag.find_all("p")]
                else:
                    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
            
            # Filter out boilerplate, short navigation text, or ads
            meaningful_paras = [p for p in paragraphs if len(p) > 40 and not p.startswith("Copyright")]
            if meaningful_paras:
                return " ".join(meaningful_paras[:6]) # Keep top 6 paragraphs for summarization
    except Exception as e:
        print(f"[Collector Scraper Warning] Could not scrape full body for {url}: {e}")
        
    return None

def fetch_rss_articles(limit_per_feed: int = 5, fetch_full_body: bool = True) -> List[Dict]:
    """
    Fetches raw news stories from verified RSS feeds.
    Free, rate-limit friendly, and guaranteed to have direct publisher attribution.
    """
    collected_articles = []
    
    for publisher, feed_url in NEWS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:limit_per_feed]:
                title = clean_html(getattr(entry, "title", "No Title"))
                summary = clean_html(getattr(entry, "summary", ""))
                link = getattr(entry, "link", "")
                published_at = getattr(entry, "published", "")
                
                body_text = summary
                if fetch_full_body and link:
                    full_body = scrape_full_article_body(link, publisher)
                    if full_body and len(full_body) > len(summary):
                        body_text = full_body
                
                article = {
                    "title": title,
                    "summary": summary,
                    "body_text": body_text,
                    "source_url": link,
                    "published_at": published_at,
                    "publisher": publisher
                }
                collected_articles.append(article)
        except Exception as e:
            print(f"[Collector Error] {publisher} ({feed_url}): {e}")
            
    return collected_articles

if __name__ == "__main__":
    print("Testing Collector with Full Article Scraping...")
    articles = fetch_rss_articles(limit_per_feed=2, fetch_full_body=True)
    print(f"\nSuccessfully collected {len(articles)} articles:")
    for i, art in enumerate(articles, 1):
        print(f"\n[{i}] [{art['publisher']}] {art['title']}")
        print(f"    URL: {art['source_url']}")
        print(f"    Body Sample: {art['body_text'][:160]}...")
