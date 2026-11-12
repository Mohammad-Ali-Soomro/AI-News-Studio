from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict
import numpy as np

class StoryCluster:
    def __init__(self, cluster_id: str, primary_article: Dict):
        self.cluster_id = cluster_id
        self.primary_article = primary_article
        self.articles: List[Dict] = [primary_article]
        self.publishers: set = {primary_article["publisher"]}

    def add_article(self, article: Dict):
        self.articles.append(article)
        self.publishers.add(article["publisher"])

    def to_dict(self) -> Dict:
        return {
            "cluster_id": self.cluster_id,
            "title": self.primary_article["title"],
            "category": "National",
            "publishers": list(self.publishers),
            "article_count": len(self.articles),
            "primary_source_url": self.primary_article["source_url"],
            "aggregated_body": " ".join([a["body_text"] for a in self.articles]),
            "sources": [
                {
                    "title": a["title"],
                    "publisher": a["publisher"],
                    "url": a["source_url"],
                    "published_at": a.get("published_at", "")
                }
                for a in self.articles
            ]
        }

def cluster_and_deduplicate(articles: List[Dict], similarity_threshold: float = 0.35) -> List[Dict]:
    """
    Groups incoming news articles into distinct story clusters using TF-IDF and Cosine Similarity.
    Detects cross-publisher duplicate reporting (e.g., both Dawn and Tribune covering the same event).
    """
    if not articles:
        return []

    if len(articles) == 1:
        cluster = StoryCluster("cluster_1", articles[0])
        return [cluster.to_dict()]

    # Combine title and snippet for semantic comparison
    corpus = [f"{a['title']} {a['summary']}" for a in articles]
    
    vectorizer = TfidfVectorizer(stop_words="english", max_features=500)
    tfidf_matrix = vectorizer.fit_transform(corpus)
    
    # Pairwise cosine similarity matrix
    sim_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)
    
    assigned = [False] * len(articles)
    clusters: List[StoryCluster] = []
    
    for i in range(len(articles)):
        if assigned[i]:
            continue
            
        cluster_id = f"cluster_{len(clusters) + 1}"
        current_cluster = StoryCluster(cluster_id, articles[i])
        assigned[i] = True
        
        # Check remaining articles for similarity
        for j in range(i + 1, len(articles)):
            if not assigned[j] and sim_matrix[i][j] >= similarity_threshold:
                current_cluster.add_article(articles[j])
                assigned[j] = True
                
        clusters.append(current_cluster)
        
    return [c.to_dict() for c in clusters]

if __name__ == "__main__":
    from collector import fetch_rss_articles
    
    print("Testing Semantic Clustering & Deduplication...")
    raw_articles = fetch_rss_articles(limit_per_feed=3, fetch_full_body=False)
    print(f"Ingested {len(raw_articles)} raw articles.")
    
    story_clusters = cluster_and_deduplicate(raw_articles, similarity_threshold=0.30)
    print(f"\nDeduplicated into {len(story_clusters)} distinct story clusters:")
    
    for cluster in story_clusters:
        print(f"\n- Cluster ID: {cluster['cluster_id']}")
        print(f"  Title: {cluster['title']}")
        print(f"  Publishers: {', '.join(cluster['publishers'])} (Articles: {cluster['article_count']})")
