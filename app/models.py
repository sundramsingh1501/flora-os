"""
Flora OS — Database Models
All SQLAlchemy ORM models. Each user's data is fully isolated by user_id FK.
"""

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    auth_provider: Mapped[str] = mapped_column(String(50), default="email")  # google | github | email
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    oauth_tokens: Mapped[list["OAuthToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    gmail_connection: Mapped["GmailConnection | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    preferences: Mapped["UserPreferences | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    daily_briefs: Mapped[list["DailyBrief"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    articles: Mapped[list["Article"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    email_summaries: Mapped[list["EmailSummary"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    activity_logs: Mapped[list["UserActivity"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Sessions (persistent login)
# ---------------------------------------------------------------------------

class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_token: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    device_info: Mapped[str | None] = mapped_column(String(512))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="sessions")


# ---------------------------------------------------------------------------
# OAuth Tokens (Google login + Gmail + GitHub login)
# ---------------------------------------------------------------------------

class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(50))  # google | github
    access_token_enc: Mapped[str] = mapped_column(Text)   # encrypted
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)  # encrypted
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scope: Mapped[str | None] = mapped_column(String(512))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user: Mapped["User"] = relationship(back_populates="oauth_tokens")


# ---------------------------------------------------------------------------
# Gmail Connection
# ---------------------------------------------------------------------------

class GmailConnection(Base):
    __tablename__ = "gmail_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    gmail_address: Mapped[str] = mapped_column(String(255))
    access_token_enc: Mapped[str] = mapped_column(Text)
    refresh_token_enc: Mapped[str] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_synced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="gmail_connection")


# ---------------------------------------------------------------------------
# User Preferences
# ---------------------------------------------------------------------------

class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    # News
    news_categories: Mapped[list] = mapped_column(JSON, default=list)
    # Jobs
    job_roles: Mapped[list] = mapped_column(JSON, default=list)
    job_locations: Mapped[list] = mapped_column(JSON, default=list)
    tech_stack: Mapped[list] = mapped_column(JSON, default=list)
    experience_years: Mapped[int] = mapped_column(default=0)
    favorite_companies: Mapped[list] = mapped_column(JSON, default=list)
    # Market
    stock_watchlist: Mapped[list] = mapped_column(JSON, default=list)
    crypto_watchlist: Mapped[list] = mapped_column(JSON, default=list)
    # Personal
    location: Mapped[str | None] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(100), default="UTC")
    brief_time: Mapped[str] = mapped_column(String(10), default="07:00")
    # AI Memory summary
    interests_summary: Mapped[str | None] = mapped_column(Text)
    # Morning email delivery
    morning_email_active: Mapped[bool] = mapped_column(Boolean, default=False)
    morning_message: Mapped[str | None] = mapped_column(String(500))
    last_email_sent_date: Mapped[str | None] = mapped_column(String(10))  # YYYY-MM-DD
    email_topics: Mapped[list] = mapped_column(JSON, default=list)  # topics shown in morning email

    user: Mapped["User"] = relationship(back_populates="preferences")


# ---------------------------------------------------------------------------
# Daily Brief
# ---------------------------------------------------------------------------

class DailyBrief(Base):
    __tablename__ = "daily_briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    content: Mapped[dict] = mapped_column(JSON, default=dict)  # full structured brief
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="daily_briefs")

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_date_brief"),)


# ---------------------------------------------------------------------------
# Articles (news feed items)
# ---------------------------------------------------------------------------

class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100), index=True)
    url: Mapped[str] = mapped_column(String(1024))
    image_url: Mapped[str | None] = mapped_column(String(1024))
    importance_score: Mapped[float] = mapped_column(Float, default=5.0)
    read_time_minutes: Mapped[int] = mapped_column(Integer, default=3)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="articles")


# ---------------------------------------------------------------------------
# Email Summaries
# ---------------------------------------------------------------------------

class EmailSummary(Base):
    __tablename__ = "email_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    gmail_message_id: Mapped[str] = mapped_column(String(255), index=True)
    subject: Mapped[str] = mapped_column(String(512))
    sender_name: Mapped[str | None] = mapped_column(String(255))
    sender_email: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    action_items: Mapped[list] = mapped_column(JSON, default=list)
    reply_draft: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), default="general")
    importance: Mapped[str] = mapped_column(String(20), default="normal")  # urgent | normal | low
    is_actioned: Mapped[bool] = mapped_column(Boolean, default=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="email_summaries")

    __table_args__ = (UniqueConstraint("user_id", "gmail_message_id", name="uq_user_message"),)


# ---------------------------------------------------------------------------
# User Activity (for personalization learning)
# ---------------------------------------------------------------------------

class UserActivity(Base):
    __tablename__ = "user_activity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(100))  # read_article | bookmark | ignore | search
    entity_type: Mapped[str | None] = mapped_column(String(50))  # article | job | email
    entity_id: Mapped[int | None] = mapped_column(Integer)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="activity_logs")
