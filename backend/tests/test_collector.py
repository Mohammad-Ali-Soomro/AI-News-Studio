import httpx

from backend.app.pipeline import collector

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Pakistan GDP growth outlook improves</title>
      <link>https://example.com/story-1</link>
      <description><![CDATA[<p>Analysts note steady progress in exports.</p>]]></description>
      <pubDate>Thu, 26 Nov 2026 08:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_news_feeds_registry_excludes_reuters():
    assert "Dawn" in collector.NEWS_FEEDS
    assert "Express Tribune" in collector.NEWS_FEEDS
    assert all("reuters" not in name.lower() for name in collector.NEWS_FEEDS)
    assert all("reuters" not in url.lower() for url in collector.NEWS_FEEDS.values())


def test_collector_survives_bad_feed_url(monkeypatch):
    class FakeResponse:
        def __init__(self, text: str, status_code: int = 200):
            self.text = text
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("GET", "https://bad.invalid/rss")
                response = httpx.Response(self.status_code, request=request)
                raise httpx.HTTPStatusError(
                    "Feed error", request=request, response=response
                )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.timeout = kwargs.get("timeout")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url: str):
            if "bad.invalid" in url:
                raise httpx.ConnectError("Connection failed")
            return FakeResponse(SAMPLE_RSS)

    monkeypatch.setattr(collector.httpx, "Client", FakeClient)

    test_feeds = {
        "Broken Feed": "https://bad.invalid/rss",
        "Dawn": "https://www.dawn.com/feeds/home",
    }
    articles = collector.fetch_rss_articles(
        limit_per_feed=2, fetch_full_body=False, feeds=test_feeds
    )

    assert len(articles) == 1
    assert articles[0]["publisher"] == "Dawn"
    assert articles[0]["title"] == "Pakistan GDP growth outlook improves"
    assert articles[0]["source_url"] == "https://example.com/story-1"
