"""
Flora OS — Token Manager
Generates, validates, and manages persistent session tokens.
Handles OAuth access token refresh for Google and GitHub.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import OAuthToken, UserSession
from app.utils.encryption import decrypt, encrypt
from app.utils.logger import get_logger

logger = get_logger("auth.token_manager")


# ---------------------------------------------------------------------------
# Session tokens
# ---------------------------------------------------------------------------

def create_session_token(
    db: Session,
    user_id: int,
    device_info: str = "",
    ip_address: str = "",
) -> str:
    """Create a new persistent session token valid for SESSION_COOKIE_MAX_AGE seconds."""
    token = secrets.token_urlsafe(64)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.session_cookie_max_age)

    session = UserSession(
        user_id=user_id,
        session_token=token,
        device_info=device_info,
        ip_address=ip_address,
        expires_at=expires_at,
    )
    db.add(session)
    db.flush()
    logger.info("Session created for user_id=%s", user_id)
    return token


def validate_session_token(db: Session, token: str) -> Optional["UserSession"]:
    """Return the UserSession if valid and not expired, else None."""
    if not token:
        return None

    session = (
        db.query(UserSession)
        .filter(
            UserSession.session_token == token,
            UserSession.is_valid == True,
            UserSession.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if session:
        session.last_used = datetime.now(timezone.utc)
        db.flush()

    return session


def invalidate_session_token(db: Session, token: str) -> None:
    """Mark a session token as invalid (logout)."""
    session = db.query(UserSession).filter(UserSession.session_token == token).first()
    if session:
        session.is_valid = False
        db.flush()
        logger.info("Session invalidated for user_id=%s", session.user_id)


def invalidate_all_sessions(db: Session, user_id: int) -> None:
    """Invalidate all sessions for a user (e.g. password change)."""
    db.query(UserSession).filter(UserSession.user_id == user_id).update({"is_valid": False})
    db.flush()


# ---------------------------------------------------------------------------
# OAuth token storage
# ---------------------------------------------------------------------------

def save_oauth_token(
    db: Session,
    user_id: int,
    provider: str,
    access_token: str,
    refresh_token: Optional[str],
    expires_at: Optional[datetime],
    scope: Optional[str] = None,
) -> OAuthToken:
    """Upsert an OAuth token for a user/provider pair."""
    existing = (
        db.query(OAuthToken)
        .filter(OAuthToken.user_id == user_id, OAuthToken.provider == provider)
        .first()
    )

    enc_access = encrypt(access_token)
    enc_refresh = encrypt(refresh_token) if refresh_token else None

    if existing:
        existing.access_token_enc = enc_access
        if enc_refresh:
            existing.refresh_token_enc = enc_refresh
        existing.expires_at = expires_at
        existing.scope = scope
        db.flush()
        return existing

    token = OAuthToken(
        user_id=user_id,
        provider=provider,
        access_token_enc=enc_access,
        refresh_token_enc=enc_refresh,
        expires_at=expires_at,
        scope=scope,
    )
    db.add(token)
    db.flush()
    return token


def get_oauth_access_token(db: Session, user_id: int, provider: str) -> Optional[str]:
    """
    Return a valid access token, refreshing it automatically if expired.
    Returns None if no token stored or refresh fails.
    """
    record = (
        db.query(OAuthToken)
        .filter(OAuthToken.user_id == user_id, OAuthToken.provider == provider)
        .first()
    )
    if not record:
        return None

    now = datetime.now(timezone.utc)
    if record.expires_at and record.expires_at > now:
        return decrypt(record.access_token_enc)

    # Token expired — attempt refresh
    if not record.refresh_token_enc:
        logger.warning("No refresh token available for user_id=%s provider=%s", user_id, provider)
        return None

    refresh_token = decrypt(record.refresh_token_enc)

    if provider == "google":
        new_token_data = _refresh_google_token(refresh_token)
    else:
        logger.warning("Token refresh not supported for provider=%s", provider)
        return None

    if not new_token_data:
        return None

    record.access_token_enc = encrypt(new_token_data["access_token"])
    record.expires_at = datetime.now(timezone.utc) + timedelta(seconds=new_token_data.get("expires_in", 3600))
    db.flush()
    logger.info("Refreshed OAuth token for user_id=%s provider=%s", user_id, provider)
    return new_token_data["access_token"]


def _refresh_google_token(refresh_token: str) -> Optional[dict]:
    """Call Google token endpoint to exchange a refresh token for a new access token."""
    try:
        resp = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("Google token refresh failed: %s", exc)
        return None
