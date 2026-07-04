"""
Flora OS — Google OAuth2
Handles both Google Login and Gmail OAuth in one flow.
Scopes: profile + email (for login) + gmail.readonly (for Gmail agent).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.models import User, UserPreferences
from app.utils.logger import get_logger

logger = get_logger("auth.google")

# Login scopes — basic profile only (no sensitive scopes to avoid 403)
_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# Gmail scopes — requested separately from Settings page when user connects Gmail
_GMAIL_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
]

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def get_authorization_url(state: str) -> str:
    """Build the Google OAuth2 authorization URL (login only — no Gmail scope)."""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{_AUTH_URL}?{urlencode(params)}"


def get_gmail_authorization_url(state: str) -> str:
    """Build the OAuth2 URL requesting Gmail read scope (used from Settings page)."""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(_GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> Optional[dict]:
    """Exchange authorization code for tokens. Returns token dict or None."""
    try:
        resp = httpx.post(
            _TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("Google code exchange failed: %s", exc)
        return None


def get_user_info(access_token: str) -> Optional[dict]:
    """Fetch Google user profile using the access token."""
    try:
        resp = httpx.get(
            _USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("Google userinfo fetch failed: %s", exc)
        return None


def upsert_google_user(db, token_data: dict) -> tuple[Optional[User], Optional[str], Optional[str]]:
    """
    Given token_data from Google, upsert the User record and return:
    (user, access_token, refresh_token)
    """
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)

    if not access_token:
        return None, None, None

    info = get_user_info(access_token)
    if not info:
        return None, None, None

    email = info.get("email", "").lower()
    name = info.get("name", email.split("@")[0])
    avatar = info.get("picture")

    existing = db.query(User).filter(User.email == email).first()

    if existing:
        existing.name = name
        existing.avatar_url = avatar
        existing.auth_provider = "google"
        db.flush()
        user = existing
    else:
        user = User(
            email=email,
            name=name,
            avatar_url=avatar,
            auth_provider="google",
        )
        db.add(user)
        db.flush()

        prefs = UserPreferences(
            user_id=user.id,
            news_categories=["AI", "Technology", "World News", "Indian News"],
            stock_watchlist=["AAPL", "GOOGL", "MSFT"],
            crypto_watchlist=["bitcoin", "ethereum"],
        )
        db.add(prefs)
        db.flush()

    logger.info("Google login upsert for user_id=%s email=%s", user.id, email)
    return user, access_token, refresh_token


def get_token_expiry(expires_in: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=expires_in)
