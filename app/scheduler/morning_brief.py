"""
Flora OS — Morning Brief Scheduler
Runs every minute, checks each user's brief_time (in their timezone),
generates brief and sends email to subscribed users.
"""

import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pytz

from app.utils.logger import get_logger

logger = get_logger("scheduler")

_scheduler: BackgroundScheduler | None = None


def _send_emails_for_due_users() -> None:
    """Check every minute — send morning email to users whose brief_time just arrived."""
    from app.database import get_db
    from app.models import User, UserPreferences
    from app.services.email_sender import send_morning_brief
    from app.services.news_service import fetch_top_stories
    from app.services.weather_service import get_weather
    from app.services.market_service import get_market_data

    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")

    with get_db() as db:
        # Find all users with email active
        subscribed = (
            db.query(User, UserPreferences)
            .join(UserPreferences, UserPreferences.user_id == User.id)
            .filter(
                User.is_active == True,
                UserPreferences.morning_email_active == True,
            )
            .all()
        )

    for user, prefs in subscribed:
        try:
            # Skip if already sent today
            if prefs.last_email_sent_date == today_str:
                continue

            # Convert user's brief_time to UTC and check if it's time (±1 min window)
            tz_name = prefs.timezone or "UTC"
            brief_time_str = prefs.brief_time or "07:00"
            h, m = map(int, brief_time_str.split(":"))

            try:
                user_tz = pytz.timezone(tz_name)
            except Exception:
                user_tz = pytz.utc

            # Build today's scheduled datetime in user's timezone
            now_local = now_utc.astimezone(user_tz)
            scheduled_local = now_local.replace(hour=h, minute=m, second=0, microsecond=0)
            scheduled_utc = scheduled_local.astimezone(timezone.utc)

            # Fire if we're within a 1-minute window of their scheduled time
            diff = abs((now_utc - scheduled_utc).total_seconds())
            if diff > 60:
                continue

            logger.info("Sending morning brief email to user_id=%s (%s)", user.id, user.email)

            # Fetch yesterday's news (from last 24h)
            articles = _get_yesterdays_news(user, prefs)
            weather = _get_weather_safe(prefs)
            market = _get_market_safe(prefs)

            jobs = _get_fresher_jobs_safe()

            ok = send_morning_brief(
                to_email=user.email,
                user_name=user.name,
                morning_message=prefs.morning_message or "",
                articles=articles,
                weather=weather,
                market=market,
                jobs=jobs,
            )

            if ok:
                with get_db() as db2:
                    p = db2.query(UserPreferences).filter_by(user_id=user.id).first()
                    if p:
                        p.last_email_sent_date = today_str

        except Exception as exc:
            logger.error("Email send failed for user_id=%s: %s", user.id, exc)


_DEFAULT_EMAIL_TOPICS = [
    "AI & Machine Learning", "Data Science", "GenAI & LLMs",
    "Technology", "Indian News", "Indian Markets", "Sports",
]


def _get_fresher_jobs_safe() -> list[dict]:
    try:
        from app.services.job_service import fetch_fresher_aiml_jobs
        return fetch_fresher_aiml_jobs()
    except Exception as exc:
        logger.warning("Fresher jobs fetch failed: %s", exc)
        return []


def _get_yesterdays_news(user, prefs) -> list[dict]:
    """Fetch/build article list from yesterday's brief or live news."""
    from app.database import get_db
    from app.models import DailyBrief
    from datetime import datetime, timezone, timedelta

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Try yesterday's stored brief first
    for date in [today, yesterday]:
        with get_db() as db:
            brief = db.query(DailyBrief).filter(
                DailyBrief.user_id == user.id,
                DailyBrief.date == date,
            ).first()
            if brief and brief.content:
                stories = brief.content.get("top_stories", [])
                if stories:
                    return stories

    # Fall back to live fetch
    try:
        from app.services.news_service import fetch_all_news
        # Use user's email_topics if set, else defaults; always include core topics
        email_cats = list(prefs.email_topics or []) if prefs.email_topics else []
        cats = email_cats if email_cats else _DEFAULT_EMAIL_TOPICS
        articles = fetch_all_news(categories=cats, max_per_category=3)
        return [
            {
                "title": a.get("title", ""),
                "summary": a.get("summary", a.get("description", "")),
                "source": a.get("source", {}).get("name", "") if isinstance(a.get("source"), dict) else a.get("source", ""),
                "url": a.get("url", "#"),
                "category": a.get("category", ""),
                "importance_score": a.get("importance_score", 5),
                "read_time_minutes": a.get("read_time_minutes", 3),
            }
            for a in articles[:15]
        ]
    except Exception as exc:
        logger.warning("News fetch failed: %s", exc)
        return []


def _get_weather_safe(prefs) -> dict | None:
    if not prefs.location:
        return None
    try:
        from app.services.weather_service import get_weather
        return get_weather(prefs.location)
    except Exception:
        return None


def _get_market_safe(prefs) -> dict | None:
    try:
        from app.services.market_service import get_market_data
        stocks = list(prefs.stock_watchlist or ["AAPL", "GOOGL", "MSFT"])
        cryptos = list(prefs.crypto_watchlist or ["bitcoin"])
        return get_market_data(tickers=stocks, crypto_ids=cryptos)
    except Exception:
        return None


def _generate_brief_for_all_users() -> None:
    """Daily brief generation (for the web app). Called at 05:00 UTC."""
    from app.database import get_db
    from app.models import User
    from app.agents.orchestrator import run_for_user

    logger.info("Scheduler: generating morning briefs for all users...")
    with get_db() as db:
        users = db.query(User).filter(User.is_active == True).all()
        for u in users:
            try:
                run_for_user(db, u)
                logger.info("Scheduler: brief done for user_id=%s", u.id)
            except Exception as exc:
                logger.error("Scheduler: failed for user_id=%s: %s", u.id, exc)


def start_scheduler() -> None:
    """Start the background scheduler. Called once at app startup."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone=pytz.utc)

    # Check every 60 seconds whether any user is due for their morning email
    _scheduler.add_job(
        _send_emails_for_due_users,
        trigger=IntervalTrigger(seconds=60),
        id="email_delivery",
        name="Morning Email Delivery Check",
        replace_existing=True,
        misfire_grace_time=120,
    )

    # Also run full brief generation daily at 05:00 UTC
    from apscheduler.triggers.cron import CronTrigger
    _scheduler.add_job(
        _generate_brief_for_all_users,
        trigger=CronTrigger(hour=5, minute=0),
        id="morning_brief",
        name="Daily Morning Brief Generation",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    _scheduler.start()
    logger.info("Scheduler started — email check every 60s, brief generation at 05:00 UTC.")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


def trigger_now() -> None:
    """Manually trigger brief generation (for testing)."""
    _generate_brief_for_all_users()
