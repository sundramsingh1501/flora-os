"""
Flora OS — GitHub OAuth2 Login
Scope: read:user + user:email (login only, no repo access).
"""

import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.models import User, UserPreferences
from app.utils.logger import get_logger

logger = get_logger("auth.github")

_AUTH_URL = "https://github.com/login/oauth/authorize"
_TOKEN_URL = "https://github.com/login/oauth/access_token"
_USER_URL = "https://api.github.com/user"
_EMAILS_URL = "https://api.github.com/user/emails"

_SCOPES = ["read:user", "user:email"]


def get_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": " ".join(_SCOPES),
        "state": state,
    }
    return f"{_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> Optional[str]:
    """Exchange code for GitHub access token."""
    try:
        resp = httpx.post(
            _TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("access_token")
    except Exception as exc:
        logger.error("GitHub code exchange failed: %s", exc)
        return None


def get_user_info(access_token: str) -> Optional[dict]:
    try:
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github+json",
        }
        user_resp = httpx.get(_USER_URL, headers=headers, timeout=10)
        user_resp.raise_for_status()
        user_data = user_resp.json()

        # GitHub may not expose email in the main endpoint — fetch separately
        if not user_data.get("email"):
            email_resp = httpx.get(_EMAILS_URL, headers=headers, timeout=10)
            if email_resp.status_code == 200:
                emails = email_resp.json()
                primary = next((e["email"] for e in emails if e.get("primary") and e.get("verified")), None)
                user_data["email"] = primary

        return user_data
    except Exception as exc:
        logger.error("GitHub user info fetch failed: %s", exc)
        return None


def upsert_github_user(db, access_token: str) -> Optional[User]:
    info = get_user_info(access_token)
    if not info:
        return None

    email = (info.get("email") or "").lower()
    if not email:
        logger.warning("GitHub user has no verified email — cannot create account.")
        return None

    name = info.get("name") or info.get("login") or email.split("@")[0]
    avatar = info.get("avatar_url")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        existing.name = name
        existing.avatar_url = avatar
        existing.auth_provider = "github"
        db.flush()
        return existing

    user = User(
        email=email,
        name=name,
        avatar_url=avatar,
        auth_provider="github",
    )
    db.add(user)
    db.flush()

    prefs = UserPreferences(
        user_id=user.id,
        news_categories=["AI", "Technology", "GitHub", "World News"],
        tech_stack=[],
        stock_watchlist=["AAPL", "GOOGL", "MSFT"],
        crypto_watchlist=["bitcoin", "ethereum"],
    )
    db.add(prefs)
    db.flush()

    logger.info("GitHub login upsert for user_id=%s email=%s", user.id, email)
    return user
