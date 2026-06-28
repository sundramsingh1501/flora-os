"""
Flora OS — Agent Orchestrator
Coordinates all specialized agents for a single user.
Runs agents concurrently using ThreadPoolExecutor for speed.
Saves the final brief to the database.
"""

import concurrent.futures
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.agents import news_agent, market_agent, gmail_agent, job_agent, research_agent, learning_agent
from app.agents.brief_generator import generate_brief
from app.models import (
    Article, DailyBrief, EmailSummary, GmailConnection,
    User, UserPreferences, UserActivity,
)
from app.utils.encryption import decrypt
from app.utils.logger import get_logger

logger = get_logger("agents.orchestrator")


def _prefs_to_dict(prefs: Optional[UserPreferences]) -> dict:
    if not prefs:
        return {}
    return {
        "news_categories": prefs.news_categories or [],
        "job_roles": prefs.job_roles or [],
        "job_locations": prefs.job_locations or [],
        "tech_stack": prefs.tech_stack or [],
        "favorite_companies": prefs.favorite_companies or [],
        "stock_watchlist": prefs.stock_watchlist or [],
        "crypto_watchlist": prefs.crypto_watchlist or [],
        "location": prefs.location or "",
        "timezone": prefs.timezone or "UTC",
        "interests_summary": prefs.interests_summary or "",
    }


def _get_gmail_connection_dict(gmail: Optional[GmailConnection]) -> Optional[dict]:
    if not gmail or not gmail.is_active:
        return None
    try:
        return {
            "gmail_address": gmail.gmail_address,
            "access_token": decrypt(gmail.access_token_enc),
            "refresh_token": decrypt(gmail.refresh_token_enc),
            "is_active": gmail.is_active,
        }
    except Exception as exc:
        logger.error("Failed to decrypt Gmail tokens: %s", exc)
        return None


def run_for_user(db: Session, user: User) -> Optional[dict]:
    """
    Run all agents for a single user and return the assembled brief dict.
    Also persists articles, email summaries, and the daily brief to DB.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Check if brief already generated today
    existing = (
        db.query(DailyBrief)
        .filter(DailyBrief.user_id == user.id, DailyBrief.date == today)
        .first()
    )
    if existing:
        logger.info("Brief already exists for user_id=%s date=%s", user.id, today)
        return existing.content

    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user.id).first()
    gmail = db.query(GmailConnection).filter(GmailConnection.user_id == user.id).first()

    prefs_dict = _prefs_to_dict(prefs)
    gmail_dict = _get_gmail_connection_dict(gmail)

    logger.info("Orchestrator starting for user_id=%s (%s)", user.id, user.email)

    # ── Run agents concurrently ────────────────────────────────────────────
    agent_results = {}
    agent_errors = {}

    def _run(name: str, fn, *args):
        try:
            return name, fn(*args)
        except Exception as exc:
            logger.error("Agent %s failed: %s", name, exc)
            return name, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(_run, "news", news_agent.run, user.id, prefs_dict),
            pool.submit(_run, "market", market_agent.run, user.id, prefs_dict),
            pool.submit(_run, "gmail", gmail_agent.run, user.id, gmail_dict),
            pool.submit(_run, "jobs", job_agent.run, user.id, prefs_dict),
            pool.submit(_run, "research", research_agent.run, user.id, prefs_dict),
            pool.submit(_run, "learning", learning_agent.run, user.id, prefs_dict),
        }
        for future in concurrent.futures.as_completed(futures):
            name, result = future.result()
            agent_results[name] = result

    logger.info("All agents completed for user_id=%s", user.id)

    # ── Persist articles ───────────────────────────────────────────────────
    news_articles = agent_results.get("news") or []
    research_data = agent_results.get("research") or {}
    research_papers = research_data.get("papers", []) if isinstance(research_data, dict) else []

    all_articles = news_articles + research_papers
    saved_article_ids = []

    for art in all_articles:
        try:
            from sqlalchemy.exc import IntegrityError
            new_art = Article(
                user_id=user.id,
                title=art.get("title", ""),
                summary=art.get("summary", ""),
                source=art.get("source", ""),
                category=art.get("category", "General"),
                url=art.get("url", ""),
                image_url=art.get("image_url"),
                importance_score=art.get("importance_score", 5.0),
                read_time_minutes=art.get("read_time_minutes", 3),
                published_at=art.get("published_at"),
            )
            db.add(new_art)
            db.flush()
            saved_article_ids.append(new_art.id)
        except Exception:
            db.rollback()

    # ── Persist email summaries ────────────────────────────────────────────
    gmail_result = agent_results.get("gmail") or {}
    emails = gmail_result.get("emails", []) if isinstance(gmail_result, dict) else []

    for email in emails:
        try:
            existing_email = (
                db.query(EmailSummary)
                .filter(
                    EmailSummary.user_id == user.id,
                    EmailSummary.gmail_message_id == email.get("gmail_message_id", ""),
                )
                .first()
            )
            if not existing_email:
                es = EmailSummary(
                    user_id=user.id,
                    gmail_message_id=email.get("gmail_message_id", ""),
                    subject=email.get("subject", ""),
                    sender_name=email.get("sender_name"),
                    sender_email=email.get("sender_email", ""),
                    summary=email.get("summary", ""),
                    action_items=email.get("action_items", []),
                    reply_draft=email.get("reply_draft"),
                    category=email.get("category", "general"),
                    importance=email.get("importance", "normal"),
                    received_at=email.get("received_at"),
                )
                db.add(es)
                db.flush()
        except Exception as exc:
            logger.warning("Failed to save email summary: %s", exc)
            db.rollback()

    # Update Gmail last_synced
    if gmail and emails:
        gmail.last_synced = datetime.now(timezone.utc)
        db.flush()

    # ── Generate the final brief ────────────────────────────────────────────
    weather = _get_weather(prefs_dict.get("location", ""))
    brief_content = generate_brief(
        user=user,
        prefs=prefs_dict,
        news=news_articles,
        market=agent_results.get("market") or {},
        gmail=gmail_result,
        jobs=agent_results.get("jobs") or [],
        research=research_data,
        learning=agent_results.get("learning") or {},
        weather=weather,
        date=today,
    )

    # ── Save brief to DB ───────────────────────────────────────────────────
    brief_record = DailyBrief(
        user_id=user.id,
        date=today,
        content=brief_content,
    )
    db.add(brief_record)
    db.flush()

    # Log activity
    db.add(UserActivity(
        user_id=user.id,
        action="brief_generated",
        extra={"date": today, "article_count": len(all_articles), "email_count": len(emails)},
    ))
    db.flush()

    logger.info("Brief generated and saved for user_id=%s date=%s", user.id, today)
    return brief_content


def _get_weather(location: str) -> Optional[dict]:
    if not location:
        return None
    try:
        from app.services.weather_service import get_weather, get_forecast
        w = get_weather(location)
        if w:
            w["forecast"] = get_forecast(location, days=3)
        return w
    except Exception as exc:
        logger.warning("Weather fetch failed: %s", exc)
        return None


def get_or_generate_brief(db: Session, user: User) -> Optional[dict]:
    """
    Get today's brief from DB or generate it now.
    Use this from the dashboard — it's safe to call repeatedly.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = (
        db.query(DailyBrief)
        .filter(DailyBrief.user_id == user.id, DailyBrief.date == today)
        .first()
    )
    if existing:
        return existing.content
    return run_for_user(db, user)
