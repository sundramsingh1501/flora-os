"""
Flora OS — Session Management

How session persistence works across page refreshes:
  1. On login  → token stored in st.session_state + localStorage (via height=1 iframe)
  2. On refresh → session_state is empty; streamlit_js_eval reads localStorage
     • Render 1: JS not yet responded → returns None → show brief loading screen
     • Render 2: JS responded → returns token (or null)
       - token valid   → restore session, page continues
       - token invalid → redirect to login
"""

from datetime import datetime, timezone
from typing import Optional

import streamlit as st

from app.database import get_db
from app.models import User, UserPreferences
from app.auth.token_manager import (
    create_session_token,
    invalidate_session_token,
    validate_session_token,
)
from app.utils.logger import get_logger

logger = get_logger("auth.session")

_SESSION_KEY    = "flora_session_token"
_USER_KEY       = "flora_user"
_LS_KEY         = "flora_token"
_LS_CHECKED_KEY = "_flora_ls_checked"   # flag: True after first JS read attempt


# ── localStorage helpers ────────────────────────────────────────────────────────

def _write_token_js(token: str) -> None:
    """Write token to localStorage. height=1 ensures the iframe renders & JS runs."""
    st.components.v1.html(
        f"""<script>
          try {{
            localStorage.setItem('{_LS_KEY}', '{token}');
          }} catch(e) {{ console.warn('flora: ls write failed', e); }}
        </script>""",
        height=1,
    )


def _clear_token_js() -> None:
    st.components.v1.html(
        f"""<script>
          try {{ localStorage.removeItem('{_LS_KEY}'); }} catch(e) {{}}
        </script>""",
        height=1,
    )


def _read_token_from_ls() -> Optional[str]:
    """
    Read session token from localStorage via streamlit-js-eval.
    Returns None on the first render (JS is async); returns the actual value on the
    second render (after the JS response triggers a Streamlit rerun).
    """
    try:
        from streamlit_js_eval import streamlit_js_eval
        result = streamlit_js_eval(
            js_expressions=f"localStorage.getItem('{_LS_KEY}')",
            key="_flora_ls_read",
        )
        return result if isinstance(result, str) and result.strip() else None
    except Exception as exc:
        logger.debug("streamlit_js_eval unavailable: %s", exc)
        return None


def _validate_token(token: str) -> Optional[User]:
    """Validate a token string against the DB. Returns User or None."""
    with get_db() as db:
        rec = validate_session_token(db, token)
        if not rec:
            return None
        u = db.query(User).filter(User.id == rec.user_id).first()
        if not u or not u.is_active:
            return None
        u.last_login = datetime.now(timezone.utc)
        db.expunge(u)
        return u


# ── Public API ──────────────────────────────────────────────────────────────────

def login(user: User) -> None:
    """Call after any successful authentication."""
    with get_db() as db:
        token = create_session_token(db, user_id=user.id)
    st.session_state[_SESSION_KEY]    = token
    st.session_state[_USER_KEY]       = user
    st.session_state.pop(_LS_CHECKED_KEY, None)   # reset the read-flag
    _write_token_js(token)
    logger.info("Session started for user_id=%s", user.id)


def logout() -> None:
    """Invalidate token, clear state, go to login."""
    token = st.session_state.get(_SESSION_KEY)
    if token:
        with get_db() as db:
            invalidate_session_token(db, token)
    _clear_token_js()
    for key in [_SESSION_KEY, _USER_KEY, _LS_CHECKED_KEY,
                "cfg_email_topics", "cfg_web_topics", "ob_topics", "onboard_step"]:
        st.session_state.pop(key, None)
    logger.info("Session logged out.")
    st.switch_page("pages/login.py")


def get_current_user() -> Optional[User]:
    """
    Return the currently authenticated User from memory, or None.
    Does NOT touch localStorage — call require_auth() for full restore logic.
    """
    if _USER_KEY in st.session_state:
        return st.session_state[_USER_KEY]

    token = st.session_state.get(_SESSION_KEY)

    # Token may also arrive via URL param set during OAuth callback
    if not token:
        token = st.query_params.get("_ft")
        if token:
            st.session_state[_SESSION_KEY] = token
            clean = {k: v for k, v in st.query_params.items()
                     if k not in ("_ft", "_ns", "code", "state")}
            st.query_params.clear()
            for k, v in clean.items():
                st.query_params[k] = v

    if not token:
        return None

    u = _validate_token(token)
    if not u:
        st.session_state.pop(_SESSION_KEY, None)
        return None

    st.session_state[_USER_KEY] = u
    return u


def require_auth() -> User:
    """
    Gate for every protected page.

    • Already logged in (session_state populated) → instant pass-through.
    • Page refreshed (empty session_state):
        Render 1 – streamlit_js_eval returns None while JS runs → show 1-frame
                   loading screen, set _flora_ls_checked flag, st.stop()
        Render 2 – streamlit_js_eval returns actual localStorage value:
                   - valid token  → restore session, continue rendering the page
                   - null / bad   → redirect to /login
    """
    # ── fast path: already authenticated ──────────────────────────────────────
    user = get_current_user()
    if user:
        st.session_state.pop(_LS_CHECKED_KEY, None)
        # Re-persist token on every authenticated render so localStorage stays
        # populated even if the login()-time write was skipped by early navigation.
        token = st.session_state.get(_SESSION_KEY)
        if token:
            _write_token_js(token)
        return user

    # ── try to restore from localStorage ──────────────────────────────────────
    ls_token = _read_token_from_ls()

    if ls_token:
        # localStorage has a token — validate it
        u = _validate_token(ls_token)
        if u:
            st.session_state[_SESSION_KEY] = ls_token
            st.session_state[_USER_KEY]    = u
            st.session_state.pop(_LS_CHECKED_KEY, None)
            logger.info("Session restored from localStorage for user_id=%s", u.id)
            return u
        # Token expired / invalid
        _clear_token_js()
        st.switch_page("pages/login.py")
        st.stop()

    # ls_token is None — two possibilities:
    #   A) JS hasn't responded yet (first render after refresh)
    #   B) JS responded but localStorage is empty (not logged in)
    if _LS_CHECKED_KEY not in st.session_state:
        # Case A — show loading for one frame while JS runs
        st.session_state[_LS_CHECKED_KEY] = True
        st.markdown(
            """
            <div style="position:fixed;inset:0;background:#09090f;
                        display:flex;align-items:center;justify-content:center;
                        flex-direction:column;gap:14px;z-index:9999;">
              <div style="font-size:2.4rem;">🌿</div>
              <div style="font-size:0.9rem;color:#7070a0;
                          font-family:-apple-system,BlinkMacSystemFont,sans-serif;">
                Loading Flora OS&hellip;
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()
    else:
        # Case B — JS confirmed empty localStorage → go to login
        st.session_state.pop(_LS_CHECKED_KEY, None)
        st.switch_page("pages/login.py")
        st.stop()


def get_user_preferences(user_id: int) -> Optional[UserPreferences]:
    with get_db() as db:
        prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
        if prefs:
            db.expunge(prefs)
        return prefs
