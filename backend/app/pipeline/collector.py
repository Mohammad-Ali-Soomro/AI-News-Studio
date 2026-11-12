import feedparser
from typing import List, Dict

# Verified RSS feeds from top Pakistani & International publishers
NEWS_FEEDS = {
    "Dawn": "https://www.dawn.com/feeds/home",
    "Express Tribune": "https://tribune.com.pk/feed/latest",
    "Reuters World": "https://www.reutersagency.com/feed/?taxonomy=markets&post_type=reuters_media"
}

def fetch_rss_articles(limit_per_feed: int = 5) -> List[Dict]:
    """
    Fetches raw news stories from verified RSS feeds.
    Free, rate-limit friendly, and guaranteed to have direct publisher attribution.
    """
    collected_articles = []
    
    for publisher, feed_url in NEWS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:limit_per_feed]:
                article = {
                    "title": getattr(entry, "title", "No Title"),
                    "summary": getattr(entry, "summary", ""),
                    "source_url": getattr(entry, "link", ""),
                    "published_at": getattr(entry, "published", ""),
                    "publisher": publisher
                }
                collected_articles.append(article)
        except Exception as e:
            print(f"Error fetching from {publisher} ({feed_url}): {e}")
            
    return collected_articles

if __name__ == "__main__":
    articles = fetch_rss_articles(limit_per_feed=2)
    print(f"Collected {len(articles)} articles.")
    for art in articles:
        print(f"[{art['publisher']}] {art['title']}")
