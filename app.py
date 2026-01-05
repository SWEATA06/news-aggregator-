import streamlit as st
import streamlit.components.v1 as components
import json
import os
from datetime import datetime
from utils.user_profile import UserProfile
from utils.recommender import NewsRecommender

# Page config
st.set_page_config(
    page_title="News Aggregator",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = UserProfile()
    
if 'recommender' not in st.session_state:
    st.session_state.recommender = NewsRecommender()

# Load news data
def load_news_data():
    try:
        with open('data/sample_news.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading news data: {e}")
        return []

# Main app
def main():
    st.title("📰 Personalized News Aggregator")
    
    # Navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Preferences", "Topic Tracking", "Recommendations"])
    
    # Load news data
    news_data = load_news_data()
    
    # Display the selected page
    if page == "Home":
        show_home(news_data)
    elif page == "Preferences":
        show_preferences()
    elif page == "Topic Tracking":
        show_topic_tracking()
    elif page == "Recommendations":
        show_recommendations(news_data)

def show_home(news_data):
    st.header("Your Personalized News Feed")
    
    # Filter options
    col1, col2 = st.columns([2, 1])
    with col1:
        filter_option = st.radio("Filter by:", ["For You", "Recent", "Trending"])
    with col2:
        category = st.selectbox("Category", ["All"] + list(set(article["category"] for article in news_data)))
    
    # Display articles
    st.subheader("Latest News")
    
    # Filter articles
    filtered_articles = news_data
    if category != "All":
        filtered_articles = [a for a in filtered_articles if a["category"] == category]
    
    # Sort based on filter
    if filter_option == "Recent":
        filtered_articles.sort(key=lambda x: x["published_at"], reverse=True)
    elif filter_option == "Trending":
        filtered_articles.sort(key=lambda x: x.get("views", 0), reverse=True)
    else:  # For You
        recommended = st.session_state.recommender.get_recommendations(
            filtered_articles, 
            st.session_state.user_profile
        )
        # If no recommendations, show popular articles as fallback
        if recommended:
            filtered_articles = recommended
        else:
            # Fallback to popular articles if no personalized recommendations
            filtered_articles = sorted(
                filtered_articles, 
                key=lambda x: (x.get("views", 0), x.get("published_at", "")), 
                reverse=True
            )[:10]
    
    # Display articles
    for article in filtered_articles[:10]:  # Show top 10 articles
        with st.expander(f"{article['title']} - {article['source']}"):
            st.write(article["summary"])
            st.caption(f"Published: {article['published_at']} | Category: {article['category']}")
            
            # Get article URL
            article_url = article.get("url", "")
            
            # Track article view when expander is opened
            if article["id"] not in st.session_state.get("viewed_articles", set()):
                if "viewed_articles" not in st.session_state:
                    st.session_state.viewed_articles = set()
                st.session_state.viewed_articles.add(article["id"])
                st.session_state.user_profile.track_article_view(article["id"])
                st.session_state.recommender.update_user_preferences(
                    article,
                    st.session_state.user_profile
                )
            
            # Open link to real news article
            if article_url:
                # Use components.html with a button that has onclick
                button_html = f'''
                <div style="margin: 10px 0;">
                    <button onclick="window.open('{article_url}', '_blank')" 
                            style="background-color: #FF4B4B; color: white; 
                                   padding: 0.5rem 1.5rem; border: none; 
                                   border-radius: 0.25rem; font-weight: bold; 
                                   cursor: pointer; font-size: 14px;">
                        📖 Read full article
                    </button>
                </div>
                '''
                components.html(button_html, height=60)
            else:
                st.warning("Article URL not available")

def show_preferences():
    st.header("Your Preferences")
    
    # Interest categories
    st.subheader("Select your interests")
    interests = ["Technology", "Business", "Sports", "Entertainment", "Health", "Science", "Environment"]
    
    # Get saved interests and filter to only include valid options
    saved_interests = st.session_state.user_profile.preferences.get("interests", [])
    valid_interests = [i for i in saved_interests if i in interests]
    
    selected_interests = st.multiselect(
        "Choose topics you're interested in:",
        interests,
        default=valid_interests
    )
    
    # Preferred sources
    st.subheader("Preferred News Sources")
    sources = ["CNN", "BBC", "Reuters", "The New York Times", "The Guardian"]
    
    # Get saved sources and filter to only include valid options
    saved_sources = st.session_state.user_profile.preferences.get("sources", [])
    valid_sources = [s for s in saved_sources if s in sources]
    
    selected_sources = st.multiselect(
        "Select your preferred news sources:",
        sources,
        default=valid_sources
    )
    
    # Save preferences
    if st.button("Save Preferences"):
        st.session_state.user_profile.update_preferences({
            "interests": selected_interests,
            "sources": selected_sources
        })
        st.success("Preferences saved successfully!")

def show_topic_tracking():
    st.header("Topic Tracking")
    
    # Followed topics
    st.subheader("Your Followed Topics")
    
    # Display followed topics
    if st.session_state.user_profile.followed_topics:
        for topic in st.session_state.user_profile.followed_topics:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"🔍 {topic}")
            with col2:
                if st.button(f"Unfollow {topic}"):
                    st.session_state.user_profile.unfollow_topic(topic)
                    st.experimental_rerun()
    else:
        st.info("You're not following any topics yet.")
    
    # Available topics to follow
    st.subheader("Available Topics")
    all_topics = ["AI", "Blockchain", "Climate Change", "Space Exploration", "Cybersecurity"]
    
    # Filter out already followed topics
    available_topics = [t for t in all_topics if t not in st.session_state.user_profile.followed_topics]
    
    if available_topics:
        selected_topic = st.selectbox("Select a topic to follow:", available_topics)
        if st.button("Follow Topic"):
            st.session_state.user_profile.follow_topic(selected_topic)
            st.experimental_rerun()
    else:
        st.info("You're already following all available topics!")

def show_recommendations(news_data):
    st.header("Recommended For You")
    
    # Get personalized recommendations
    recommended_articles = st.session_state.recommender.get_recommendations(
        news_data,
        st.session_state.user_profile,
        n_recommendations=5
    )
    
    if not recommended_articles:
        st.info("We need more information to provide personalized recommendations. Please interact with some articles first!")
        st.subheader("Popular Articles")
        # Show popular articles as fallback
        popular_articles = sorted(news_data, key=lambda x: x.get("views", 0), reverse=True)[:5]
        recommended_articles = popular_articles
    
    for article in recommended_articles:
        with st.expander(f"{article['title']} - {article['source']}"):
            st.write(article["summary"])
            st.caption(f"Published: {article['published_at']} | Category: {article['category']}")
            
            # Get article URL
            article_url = article.get("url", "")
            
            # Track article view when expander is opened
            if article["id"] not in st.session_state.get("viewed_articles", set()):
                if "viewed_articles" not in st.session_state:
                    st.session_state.viewed_articles = set()
                st.session_state.viewed_articles.add(article["id"])
                st.session_state.user_profile.track_article_view(article["id"])
            
            # Open link to real news article
            if article_url:
                # Use components.html with a button that has onclick
                button_html = f'''
                <div style="margin: 10px 0;">
                    <button onclick="window.open('{article_url}', '_blank')" 
                            style="background-color: #FF4B4B; color: white; 
                                   padding: 0.5rem 1.5rem; border: none; 
                                   border-radius: 0.25rem; font-weight: bold; 
                                   cursor: pointer; font-size: 14px;">
                        📖 Read full article
                    </button>
                </div>
                '''
                components.html(button_html, height=60)
            else:
                st.warning("Article URL not available")

if __name__ == "__main__":
    main()
