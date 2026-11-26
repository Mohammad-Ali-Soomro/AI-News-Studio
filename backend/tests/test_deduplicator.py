from backend.app.pipeline.deduplicator import cluster_and_deduplicate


def test_clustering_groups_near_duplicates_and_separates_unrelated_story():
    articles = [
        {
            "title": "State Bank of Pakistan cuts policy interest rate by 100 basis points",
            "summary": "The State Bank of Pakistan announced a 100 basis points cut in the policy interest rate today.",
            "body_text": "State Bank of Pakistan monetary policy committee lowered the interest rate.",
            "source_url": "https://www.dawn.com/news/1",
            "published_at": "2026-11-26T08:00:00Z",
            "publisher": "Dawn",
        },
        {
            "title": "State Bank of Pakistan lowers policy interest rate by 100 basis points",
            "summary": "Today the State Bank of Pakistan reduced the policy interest rate by 100 basis points.",
            "body_text": "Monetary policy decision by State Bank of Pakistan lowers rate.",
            "source_url": "https://tribune.com.pk/story/2",
            "published_at": "2026-11-26T08:15:00Z",
            "publisher": "Express Tribune",
        },
        {
            "title": "Lahore cricket stadium hosts floodlit T20 exhibition match",
            "summary": "Thousands of fans gathered in Lahore for the weekend T20 cricket exhibition match.",
            "body_text": "Cricket teams played a T20 match at Gaddafi Stadium in Lahore.",
            "source_url": "https://www.dawn.com/news/3",
            "published_at": "2026-11-26T09:00:00Z",
            "publisher": "Dawn",
        },
    ]

    clusters = cluster_and_deduplicate(articles, similarity_threshold=0.35)

    assert len(clusters) == 2
    assert clusters[0]["article_count"] == 2
    assert set(clusters[0]["publishers"]) == {"Dawn", "Express Tribune"}
    assert clusters[1]["article_count"] == 1
    assert "cricket" in clusters[1]["title"].lower()
