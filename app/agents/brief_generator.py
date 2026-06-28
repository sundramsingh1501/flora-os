"""
Flora OS — Daily Brief Generator
Assembles all agent outputs into one structured JSON brief.
This is the final product that the UI renders as a newspaper.
"""

from datetime import datetime, timezone
from typing import Optional

from app.models import User
from app.services.ai_service import generate
from app.utils.logger import get_logger

logger = get_logger("agents.brief_generator")


def generate_brief(
    user: User,
    prefs: dict,
    news: list[dict],
    market: dict,
    gmail: dict,
    jobs: list[dict],
    research: dict,
    learning: dict,
    weather: Optional[dict],
    date: str,
) -> dict:
    """
    Assemble all agent outputs into one structured brief dict.
    The UI reads this dict directly — no further AI calls needed at render time.
    """
    logger.info("BriefGenerator assembling for user=%s date=%s", user.id, date)

    # Categorize news articles
    news_by_category: dict[str, list] = {}
    for art in news:
        cat = art.get("category", "General")
        news_by_category.setdefault(cat, []).append(_serialize_article(art))

    # AI executive headline
    headline = _generate_headline(user.name, news, market, weather)

    # Top 3 articles by importance
    top_articles = sorted(news, key=lambda x: x.get("importance_score", 0), reverse=True)[:3]

    brief = {
        "meta": {
            "date": date,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "user_name": user.name,
            "greeting": _get_greeting(user.name),
        },
        "headline": headline,
        "weather": weather,
        "top_stories": [_serialize_article(a) for a in top_articles],
        "news_by_category": news_by_category,
        "market": {
            "stocks": market.get("stocks", []),
            "crypto": market.get("crypto", []),
            "summary": market.get("summary", ""),
            "top_mover": market.get("top_mover"),
        },
        "gmail": {
            "connected": gmail.get("connected", False),
            "summary": gmail.get("summary", ""),
            "total": gmail.get("total", 0),
            "urgent_count": gmail.get("urgent_count", 0),
            "action_count": gmail.get("action_count", 0),
        },
        "jobs": {
            "top_picks": [_serialize_job(j) for j in jobs[:5]],
            "total_found": len(jobs),
        },
        "research": {
            "papers": research.get("papers", [])[:5],
            "trending_repos": research.get("trending_repos", [])[:8],
            "ai_tool_of_day": research.get("ai_tool_of_day", {}),
        },
        "learning": {
            "resource": learning.get("learning_resource", {}),
            "interview_question": learning.get("interview_question", {}),
            "daily_quote": learning.get("daily_quote", {}),
            "ai_recommendation": learning.get("ai_recommendation", {}),
        },
        "stats": {
            "total_articles": len(news),
            "total_jobs": len(jobs),
            "email_count": gmail.get("total", 0),
            "categories_covered": list(news_by_category.keys()),
        },
    }

    logger.info(
        "Brief assembled: %s articles, %s jobs, %s emails, %s categories",
        len(news), len(jobs), gmail.get("total", 0), len(news_by_category),
    )
    return brief


def _get_greeting(name: str) -> str:
    hour = datetime.now(timezone.utc).hour
    first = name.split()[0] if name else "there"
    if hour < 12:
        return f"Good morning, {first} ☀️"
    if hour < 17:
        return f"Good afternoon, {first} 👋"
    return f"Good evening, {first} 🌙"


def _generate_headline(
    name: str,
    news: list[dict],
    market: dict,
    weather: Optional[dict],
) -> str:
    """Ask Gemini to write a 1-sentence executive headline for the day."""
    top_titles = [a.get("title", "") for a in sorted(
        news, key=lambda x: x.get("importance_score", 0), reverse=True
    )[:5]]

    market_line = ""
    stocks = market.get("stocks", [])
    if stocks:
        s = stocks[0]
        market_line = f"{s['ticker']} at ${s['price']} ({s['change_pct']:+.1f}%)"

    weather_line = ""
    if weather:
        weather_line = f"{weather['city']}: {weather['temp_c']}°C, {weather['description']}"

    return generate(
        f"Write one punchy, executive-style 'Today's Headline' sentence (max 20 words) that "
        f"captures the most important thing happening today based on:\n"
        f"Top stories: {'; '.join(top_titles[:3])}\n"
        f"Market: {market_line}\n"
        f"Weather: {weather_line}\n"
        f"Do NOT start with 'Today'. Make it feel like a Bloomberg terminal headline.",
        temperature=0.6,
    ) or "Markets steady as AI continues to reshape the global technology landscape."


def _serialize_article(a: dict) -> dict:
    return {
        "id": a.get("id"),
        "title": a.get("title", ""),
        "summary": a.get("summary", ""),
        "source": a.get("source", ""),
        "category": a.get("category", ""),
        "url": a.get("url", ""),
        "image_url": a.get("image_url"),
        "importance_score": round(a.get("importance_score", 5.0), 1),
        "read_time_minutes": a.get("read_time_minutes", 3),
        "published_at": str(a.get("published_at", "")),
    }


def _serialize_job(j: dict) -> dict:
    return {
        "id": j.get("id"),
        "title": j.get("title", ""),
        "company": j.get("company", ""),
        "location": j.get("location", ""),
        "url": j.get("url", ""),
        "source": j.get("source", ""),
        "fit_score": round(j.get("fit_score", 5.0), 1),
        "fit_reason": j.get("fit_reason", ""),
        "match_tags": j.get("match_tags", []),
        "salary_min": j.get("salary_min"),
        "salary_max": j.get("salary_max"),
    }
