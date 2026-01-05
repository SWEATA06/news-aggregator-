from typing import List, Dict, Any, Set
import random
from datetime import datetime, timedelta
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .user_profile import UserProfile

class NewsRecommender:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.article_vectors = None
        self.article_ids = []
        self.last_trained = None
    
    def _get_article_features(self, article: Dict[str, Any]) -> str:
        """Extract features from an article for vectorization."""
        features = []
        features.append(article.get('title', ''))
        features.append(article.get('summary', ''))
        features.append(article.get('category', ''))
        features.append(' '.join(article.get('tags', [])))
        return ' '.join(features)
    
    def train(self, articles: List[Dict[str, Any]]) -> None:
        """Train the recommender on a list of articles."""
        if not articles:
            return
            
        self.article_ids = [a['id'] for a in articles]
        article_texts = [self._get_article_features(a) for a in articles]
        
        try:
            self.article_vectors = self.vectorizer.fit_transform(article_texts)
            self.last_trained = datetime.now()
        except Exception as e:
            print(f"Error training recommender: {e}")
    
    def get_recommendations(
        self, 
        articles: List[Dict[str, Any]], 
        user_profile: UserProfile,
        n_recommendations: int = 10
    ) -> List[Dict[str, Any]]:
        """Get personalized article recommendations for a user."""
        if not articles:
            return []
        
        # Filter out already viewed articles
        unviewed_articles = [a for a in articles if a['id'] not in user_profile.viewed_articles]
        
        # If all articles are viewed, use all articles (don't filter out viewed ones)
        if not unviewed_articles:
            unviewed_articles = articles
        
        # Apply user preferences
        filtered_articles = self._filter_by_preferences(unviewed_articles, user_profile)
        
        # If preference filtering returns nothing, use unviewed articles
        if not filtered_articles:
            candidates = unviewed_articles
        # If we have enough articles after filtering, use them; otherwise, fall back to unviewed
        elif len(filtered_articles) >= n_recommendations:
            candidates = filtered_articles
        else:
            candidates = filtered_articles + [a for a in unviewed_articles if a not in filtered_articles]
        
        # If we have user history, use content-based filtering
        if user_profile.reading_history and len(candidates) > 1:
            try:
                # Get recently viewed articles
                recent_article_ids = user_profile.get_recently_viewed(min(5, len(user_profile.reading_history)))
                recent_articles = [a for a in articles if a['id'] in recent_article_ids]
                
                if recent_articles:
                    # Train on all articles if not already done
                    if self.article_vectors is None or self.last_trained is None or \
                       (datetime.now() - self.last_trained) > timedelta(hours=1):
                        self.train(articles)
                    
                    if self.article_vectors is not None:
                        # Get vectors for recent articles
                        recent_indices = [i for i, a in enumerate(articles) if a['id'] in recent_article_ids]
                        recent_vectors = self.article_vectors[recent_indices]
                        
                        # Get vectors for candidate articles
                        candidate_indices = [i for i, a in enumerate(articles) if a in candidates]
                        candidate_vectors = self.article_vectors[candidate_indices]
                        
                        # Calculate similarity between recent articles and candidates
                        similarity_matrix = cosine_similarity(recent_vectors, candidate_vectors)
                        
                        # Get average similarity for each candidate
                        avg_similarities = similarity_matrix.mean(axis=0)
                        
                        # Sort candidates by similarity (descending)
                        sorted_indices = np.argsort(avg_similarities)[::-1]
                        
                        # Get top N recommendations
                        top_indices = sorted_indices[:min(n_recommendations, len(sorted_indices))]
                        recommended_articles = [candidates[i] for i in top_indices]
                        
                        return recommended_articles
            except Exception as e:
                print(f"Error in content-based filtering: {e}")
                # Fall through to popularity-based if there's an error
        
        # Fallback: Sort by popularity/recency if we don't have enough data for personalization
        return self._get_popular_articles(candidates, n_recommendations)
    
    def _filter_by_preferences(
        self, 
        articles: List[Dict[str, Any]], 
        user_profile: UserProfile
    ) -> List[Dict[str, Any]]:
        """Filter articles based on user preferences."""
        if not articles:
            return []
        
        filtered = articles.copy()
        
        # Filter by followed topics
        if user_profile.followed_topics:
            filtered = [a for a in filtered if 
                       any(topic.lower() in a.get('title', '').lower() or 
                           topic.lower() in ' '.join(a.get('tags', [])).lower()
                           for topic in user_profile.followed_topics)]
        
        # Filter out muted topics
        if user_profile.muted_topics:
            filtered = [a for a in filtered if 
                       not any(topic.lower() in a.get('title', '').lower() or 
                              topic.lower() in ' '.join(a.get('tags', [])).lower()
                              for topic in user_profile.muted_topics)]
        
        # Filter by preferred sources
        if user_profile.preferences.get('sources'):
            preferred_sources = [s.lower() for s in user_profile.preferences['sources']]
            filtered = [a for a in filtered if a.get('source', '').lower() in preferred_sources]
        
        # Filter by reading time preferences
        min_time = user_profile.preferences.get('min_reading_time', 1)
        max_time = user_profile.preferences.get('max_reading_time', 60)
        filtered = [a for a in filtered if 
                   min_time <= a.get('reading_time', 5) <= max_time]
        
        return filtered
    
    def _get_popular_articles(
        self, 
        articles: List[Dict[str, Any]], 
        n: int = 10
    ) -> List[Dict[str, Any]]:
        """Get popular articles based on views and recency."""
        if not articles:
            return []
        
        # Sort by popularity (views) and recency
        sorted_articles = sorted(
            articles,
            key=lambda x: (
                x.get('views', 0),
                x.get('published_at', '')
            ),
            reverse=True
        )
        
        return sorted_articles[:min(n, len(sorted_articles))]
    
    def update_user_preferences(
        self, 
        article: Dict[str, Any], 
        user_profile: UserProfile
    ) -> None:
        """Update user preferences based on article interaction."""
        # This is a simplified example - in a real app, you might want to:
        # 1. Update user's interest scores based on categories/tags
        # 2. Adjust source preferences
        # 3. Update reading time preferences
        
        # For now, we'll just update the user's followed topics based on article tags
        if 'tags' in article and len(article['tags']) > 0:
            # Get the first tag as a potential topic
            new_topic = article['tags'][0]
            
            # If the user doesn't follow this topic yet, suggest it
            if (new_topic not in user_profile.followed_topics and 
                new_topic not in user_profile.muted_topics):
                # In a real app, you might want to ask the user if they want to follow this topic
                # For now, we'll just add it to followed topics
                user_profile.follow_topic(new_topic)
