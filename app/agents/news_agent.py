"""
Flora OS — News Agent
Fetches articles, AI-summarizes them, scores importance per-user.
"""

from app.services.news_service import fetch_all_news
from app.services.ai_service import generate_json, summarize, score_importance
from app.utils.logger import get_logger

logger = get_logger("agents.news")


def run(user_id: int, preferences: dict) -> list[dict]:
    """
    Fetch and process news for a user.

    preferences keys used:
      - news_categories: list[str]
      - tech_stack: list[str]
      - interests_summary: str

    Returns a list of enriched article dicts ready to save.
    """
    categories = preferences.get("news_categories") or [
        "AI", "Technology", "World News", "Indian News"
    ]
    user_interests = categories + (preferences.get("tech_stack") or [])

    logger.info("NewsAgent running for user_id=%s, categories=%s", user_id, categories)

    raw_articles = fetch_all_news(categories, max_per_category=8)
    enriched = []

    for article in raw_articles:
        title = article.get("title", "")
        raw_summary = article.get("summary", "")

        if not title:
            continue

        # AI-generate a clean 30-word summary if raw is too long/noisy
        if len(raw_summary) > 200 or len(raw_summary) < 30:
            ai_summary = summarize(f"{title}. {raw_summary}", max_words=35)
        else:
            ai_summary = raw_summary

        # Importance score personalized to user
        importance = score_importance(title, ai_summary, user_interests)

        # Estimate read time (avg 200 words/min, articles ~600 words)
        read_time = max(1, len(raw_summary.split()) // 200 + 1)

        enriched.append({
            **article,
            "summary": ai_summary,
            "importance_score": importance,
            "read_time_minutes": read_time,
            "user_id": user_id,
        })

    # Sort by importance descending
    enriched.sort(key=lambda x: x["importance_score"], reverse=True)
    logger.info("NewsAgent produced %s enriched articles for user_id=%s", len(enriched), user_id)
    return enriched
