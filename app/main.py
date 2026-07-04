"""
Flora OS — Application Entry Point
Run with: streamlit run app/main.py
"""

import streamlit as st

# set_page_config MUST be the very first Streamlit call
st.set_page_config(
    page_title="Flora OS",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.config import settings
from app.database import init_db
from app.utils.logger import setup_logging, get_logger

# ── Bootstrap (runs once per process) ────────────────────────────────────────
setup_logging()
logger = get_logger("main")

@st.cache_resource
def _bootstrap():
    init_db()
    from app.scheduler.morning_brief import start_scheduler
    start_scheduler()
    logger.info("Flora OS started. env=%s", settings.app_env)
    return True

_bootstrap()

# ── OAuth callbacks — must run before any switch_page ────────────────────────
# Google redirects to http://localhost:8501/?code=...&state=<prefix:token>
# We check state prefix to route: "google:" = login, "gmail:" = Gmail connect.

def _handle_google_login_callback():
    """Handle Google sign-in / sign-up OAuth callback."""
    params = st.query_params
    code  = params.get("code")
    state = params.get("state", "")

    if not (code and state.startswith("google:")):
        return False

    st.query_params.clear()

    from app.auth.google_oauth import exchange_code as google_exchange, upsert_google_user, get_token_expiry
    from app.auth.token_manager import save_oauth_token
    from app.auth.session import login
    from app.database import get_db
    from app.ui.components import toast_success, toast_error

    saved_state = st.session_state.get("oauth_state")
    if saved_state and state != saved_state:
        toast_error("OAuth state mismatch. Please try again.")
        st.switch_page("pages/login.py")
        return True

    token_data = google_exchange(code)
    if not token_data:
        toast_error("Google login failed. Please try again.")
        st.switch_page("pages/login.py")
        return True

    with get_db() as db:
        u, access_token, refresh_token = upsert_google_user(db, token_data)
        if not u:
            toast_error("Could not retrieve your Google profile.")
            st.switch_page("pages/login.py")
            return True
        expires_at = get_token_expiry(token_data.get("expires_in", 3600))
        save_oauth_token(db, u.id, "google", access_token, refresh_token,
                         expires_at, scope=token_data.get("scope"))

    from app.auth.token_manager import create_session_token
    from app.database import get_db as _get_db2
    with _get_db2() as _db2:
        _token = create_session_token(_db2, user_id=u.id)

    st.session_state.pop("oauth_state", None)

    # Redirect back into the HF Spaces wrapper with the session token in the URL.
    # get_current_user() picks up _ft and restores the session — no localStorage needed.
    _base = settings.app_base_url.rstrip("/")
    _page = "onboarding" if not u.is_onboarded else "dashboard"
    _dest = f"{_base}/?_ft={_token}&_ns={_page}"
    st.components.v1.html(
        f"<script>window.top.location.href = '{_dest}';</script>",
        height=0,
    )
    st.stop()
    return True


def _handle_gmail_connect_callback():
    """Handle Gmail OAuth callback (initiated from Settings page).

    The state is encoded as "gmail:{user_id}:{random}" so we can look up the
    user directly from the DB without needing an active Streamlit session.
    """
    params = st.query_params
    code  = params.get("code")
    state = params.get("state", "")

    if not (code and state.startswith("gmail:")):
        return False

    st.query_params.clear()

    from app.auth.google_oauth import exchange_code as google_exchange, get_user_info, get_token_expiry
    from app.database import get_db
    from app.models import GmailConnection, User
    from app.utils.encryption import encrypt

    # Extract user_id from state: "gmail:{user_id}:{random_token}"
    parts = state.split(":", 2)
    try:
        user_id = int(parts[1])
    except (IndexError, ValueError):
        st.session_state["gmail_connect_result"] = {"success": False, "error": "Invalid OAuth state."}
        st.switch_page("pages/settings.py")
        return True

    token_data = google_exchange(code)
    if not token_data:
        st.session_state["gmail_connect_result"] = {"success": False, "error": "Could not exchange Gmail code."}
        st.switch_page("pages/settings.py")
        return True

    access_token  = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    info          = get_user_info(access_token) if access_token else None
    gmail_email   = info.get("email", "") if info else ""

    if access_token and gmail_email:
        expires_at = get_token_expiry(token_data.get("expires_in", 3600))
        db_user = None
        with get_db() as db:
            db_user = db.query(User).filter_by(id=user_id, is_active=True).first()
            if not db_user:
                st.session_state["gmail_connect_result"] = {"success": False, "error": "User not found."}
                st.switch_page("pages/settings.py")
                return True
            db.expunge(db_user)
            existing = db.query(GmailConnection).filter_by(user_id=user_id).first()
            if existing:
                existing.gmail_address     = gmail_email
                existing.access_token_enc  = encrypt(access_token)
                existing.refresh_token_enc = encrypt(refresh_token) if refresh_token else existing.refresh_token_enc
                existing.token_expires_at  = expires_at
                existing.is_active         = True
            else:
                db.add(GmailConnection(
                    user_id=user_id,
                    gmail_address=gmail_email,
                    access_token_enc=encrypt(access_token),
                    refresh_token_enc=encrypt(refresh_token or ""),
                    token_expires_at=expires_at,
                ))
        # Establish a full session so settings.py can load without redirecting to login
        from app.auth.session import login as session_login
        session_login(db_user)
        st.session_state.pop("gmail_oauth_state", None)
        st.session_state["gmail_connect_result"] = {"success": True, "email": gmail_email}
    else:
        st.session_state["gmail_connect_result"] = {"success": False, "error": "Missing tokens from Google."}

    st.switch_page("pages/settings.py")
    return True


if _handle_google_login_callback():
    st.stop()

if _handle_gmail_connect_callback():
    st.stop()

# ── Route to login or dashboard ───────────────────────────────────────────────
from app.auth.session import get_current_user
from app.ui.theme import apply_theme_no_config

apply_theme_no_config()

user = get_current_user()
if user:
    _ns = st.query_params.get("_ns", "dashboard")
    st.query_params.clear()
    if _ns == "onboarding":
        st.switch_page("pages/onboarding.py")
    else:
        st.switch_page("pages/dashboard.py")
else:
    st.switch_page("pages/login.py")
