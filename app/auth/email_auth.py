"""
Flora OS — Email & Password Authentication
bcrypt hashing, registration, login, password change.
"""

import re
from typing import Optional

import bcrypt
from sqlalchemy.orm import Session

from app.models import User, UserPreferences
from app.utils.logger import get_logger

logger = get_logger("auth.email")

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def _validate_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


def _validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    return True, ""


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_user(
    db: Session,
    name: str,
    email: str,
    password: str,
) -> tuple[Optional[User], str]:
    """
    Create a new email/password user.
    Returns (user, "") on success or (None, error_message) on failure.
    """
    email = email.strip().lower()

    if not _validate_email(email):
        return None, "Invalid email address."

    ok, err = _validate_password(password)
    if not ok:
        return None, err

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return None, "An account with this email already exists."

    user = User(
        email=email,
        name=name.strip(),
        auth_provider="email",
        password_hash=hash_password(password),
    )
    db.add(user)
    db.flush()

    # Create default preferences
    prefs = UserPreferences(
        user_id=user.id,
        news_categories=["AI", "Technology", "World News", "Indian News"],
        job_roles=[],
        job_locations=[],
        tech_stack=[],
        stock_watchlist=["AAPL", "GOOGL", "MSFT"],
        crypto_watchlist=["bitcoin", "ethereum"],
    )
    db.add(prefs)
    db.flush()

    logger.info("Registered new email user: %s (id=%s)", email, user.id)
    return user, ""


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def login_user(
    db: Session,
    email: str,
    password: str,
) -> tuple[Optional[User], str]:
    """
    Authenticate an email/password user.
    Returns (user, "") or (None, error_message).
    """
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email, User.auth_provider == "email").first()

    if not user:
        # Check if they registered via Google
        google_user = db.query(User).filter(User.email == email).first()
        if google_user and google_user.auth_provider == "google":
            return None, "This email is registered with Google. Please use 'Continue with Google' to sign in."
        return None, "No account found with this email. Please create an account first."

    if not user.password_hash:
        return None, "No account found with this email. Please create an account first."

    if not verify_password(password, user.password_hash):
        return None, "Invalid email or password."

    if not user.is_active:
        return None, "This account has been deactivated."

    logger.info("Email login success: %s (id=%s)", email, user.id)
    return user, ""


# ---------------------------------------------------------------------------
# Password change
# ---------------------------------------------------------------------------

def change_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> tuple[bool, str]:
    if not verify_password(current_password, user.password_hash or ""):
        return False, "Current password is incorrect."

    ok, err = _validate_password(new_password)
    if not ok:
        return False, err

    user.password_hash = hash_password(new_password)
    db.flush()
    logger.info("Password changed for user_id=%s", user.id)
    return True, ""
