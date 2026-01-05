from datetime import datetime
from typing import Dict, List, Set, Any
import json
import os

class UserProfile:
    def __init__(self):
        # Initialize with default preferences
        self.preferences = {
            "interests": [],
            "sources": [],
            "min_reading_time": 1,
            "max_reading_time": 10
        }
        self.viewed_articles = set()  # Track viewed article IDs
        self.reading_history = []     # Track reading history with timestamps
        self.followed_topics = set()  # Topics the user is following
        self.muted_topics = set()     # Topics the user wants to mute
        
        # Load user data if exists
        self.load_user_data()
    
    def update_preferences(self, new_prefs: Dict[str, Any]) -> None:
        """Update user preferences with new values."""
        for key, value in new_prefs.items():
            if key in self.preferences:
                self.preferences[key] = value
        self.save_user_data()
    
    def track_article_view(self, article_id: str) -> None:
        """Record that the user has viewed an article."""
        if article_id not in self.viewed_articles:
            self.viewed_articles.add(article_id)
            self.reading_history.append({
                "article_id": article_id,
                "timestamp": datetime.now().isoformat()
            })
            # Keep only the last 1000 history items
            if len(self.reading_history) > 1000:
                self.reading_history = self.reading_history[-1000:]
            self.save_user_data()
    
    def follow_topic(self, topic: str) -> None:
        """Add a topic to the user's followed topics."""
        self.followed_topics.add(topic)
        if topic in self.muted_topics:
            self.muted_topics.remove(topic)
        self.save_user_data()
    
    def unfollow_topic(self, topic: str) -> None:
        """Remove a topic from the user's followed topics."""
        if topic in self.followed_topics:
            self.followed_topics.remove(topic)
        self.save_user_data()
    
    def mute_topic(self, topic: str) -> None:
        """Add a topic to the muted topics."""
        self.muted_topics.add(topic)
        if topic in self.followed_topics:
            self.followed_topics.remove(topic)
        self.save_user_data()
    
    def save_user_data(self) -> None:
        """Save user data to a JSON file."""
        user_data = {
            "preferences": self.preferences,
            "viewed_articles": list(self.viewed_articles),
            "reading_history": self.reading_history,
            "followed_topics": list(self.followed_topics),
            "muted_topics": list(self.muted_topics)
        }
        
        os.makedirs('user_data', exist_ok=True)
        with open('user_data/user_profile.json', 'w') as f:
            json.dump(user_data, f, indent=2)
    
    def load_user_data(self) -> None:
        """Load user data from a JSON file if it exists."""
        try:
            if os.path.exists('user_data/user_profile.json'):
                with open('user_data/user_profile.json', 'r') as f:
                    data = json.load(f)
                    
                    self.preferences = data.get('preferences', self.preferences)
                    self.viewed_articles = set(data.get('viewed_articles', []))
                    self.reading_history = data.get('reading_history', [])
                    self.followed_topics = set(data.get('followed_topics', []))
                    self.muted_topics = set(data.get('muted_topics', []))
        except Exception as e:
            print(f"Error loading user data: {e}")
            # If there's an error, just continue with default values
    
    def get_recently_viewed(self, n: int = 5) -> List[str]:
        """Get the most recently viewed article IDs."""
        return [item['article_id'] for item in reversed(self.reading_history[-n:])]
    
    def get_view_count_by_category(self, category: str) -> int:
        """Get the number of articles viewed in a specific category."""
        # Note: This would need access to article data to get categories
        # For now, return 0 as a placeholder
        return 0
    
    def get_top_categories(self, n: int = 3) -> List[str]:
        """Get the top n categories the user has shown interest in."""
        # Note: This would need access to article data to get categories
        # For now, return the user's selected interests
        return self.preferences.get('interests', [])[:n]
