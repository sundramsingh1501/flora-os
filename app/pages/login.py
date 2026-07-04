"""
Flora OS -- Login Page
"""

import secrets
import streamlit as st

from app.auth.session import get_current_user, login
from app.auth.email_auth import login_user, register_user
from app.auth.google_oauth import get_authorization_url as google_auth_url
from app.database import get_db
from app.models import UserPreferences
from app.ui.theme import apply_theme
from app.ui.components import labeled_divider, toast_error, toast_success
from app.utils.logger import get_logger
from datetime import datetime

logger = get_logger("pages.login")

apply_theme(sidebar_state="collapsed")

# ── Redirect if already logged in ────────────────────────────────────────────
user = get_current_user()
if user:
    st.switch_page("pages/dashboard.py")
    st.stop()

# Google OAuth callback is handled in main.py before this page loads.

# Google OAuth callback is handled in main.py before this page loads.

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Hide sidebar on login page */
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }

    /* Narrow centred card */
    .block-container {
        max-width: 480px !important;
        margin: 0 auto !important;
        padding-top: 3rem !important;
    }

    /* Google button style: white background, Google colors */
    button[data-testid="baseButton-secondary"].google-btn {
        background: #ffffff !important;
        color: #3c4043 !important;
        border: 1px solid #dadce0 !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.10) !important;
    }
    button[data-testid="baseButton-secondary"].google-btn:hover {
        background: #f8f9fa !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center;margin-bottom:2rem;">
      <div style="font-size:3rem;margin-bottom:0.75rem;">&#127807;</div>
      <h1 style="font-size:2.2rem;font-weight:800;letter-spacing:-0.04em;
                 background:linear-gradient(135deg,#7c6af7,#38bdf8);
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                 background-clip:text;margin-bottom:0.4rem;">Flora OS</h1>
      <p style="color:var(--text-secondary);font-size:0.95rem;margin:0;">
        Your personal AI executive assistant. Start your day with clarity.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Tab switcher (Sign In / Create Account) ───────────────────────────────────
if "login_tab" not in st.session_state:
    st.session_state.login_tab = "signin"

col_a, col_b = st.columns(2)
with col_a:
    if st.button(
        "Sign In",
        use_container_width=True,
        type="primary" if st.session_state.login_tab == "signin" else "secondary",
        key="tab_signin",
    ):
        st.session_state.login_tab = "signin"
        st.rerun()
with col_b:
    if st.button(
        "Create Account",
        use_container_width=True,
        type="primary" if st.session_state.login_tab == "register" else "secondary",
        key="tab_register",
    ):
        st.session_state.login_tab = "register"
        st.rerun()

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

_G_SVG = (
    '<svg width="18" height="18" viewBox="0 0 48 48" style="display:inline-block;vertical-align:middle;margin-right:8px;">'
    '<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0'
    ' 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>'
    '<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26'
    ' 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>'
    '<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19'
    'C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>'
    '<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3'
    '-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>'
    '</svg>'
)


def _google_button(label: str, google_url: str) -> None:
    """Renders a Google-branded anchor link with target='_top' inside a component iframe.
    This breaks out of the HF Spaces iframe on user click — the only reliable method."""
    st.components.v1.html(
        f"""
        <style>
          body {{ margin:0; padding:0; background:transparent; }}
          a.gbtn {{
            display:flex; align-items:center; justify-content:center;
            font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
            font-weight:600; font-size:0.93rem; color:#3c4043;
            background:#ffffff; border:1px solid #dadce0; border-radius:8px;
            padding:11px 16px; box-shadow:0 1px 3px rgba(0,0,0,.10);
            text-decoration:none; width:100%; box-sizing:border-box;
            transition:box-shadow .15s;
          }}
          a.gbtn:hover {{ box-shadow:0 2px 6px rgba(0,0,0,.18); }}
        </style>
        <a class="gbtn" href="{google_url}" target="_top">
          {_G_SVG}{label}
        </a>
        """,
        height=52,
    )


# ═══════════════════════════════════════════════════════════════════
#  SIGN IN TAB
# ═══════════════════════════════════════════════════════════════════
if st.session_state.login_tab == "signin":

    state = "google:" + secrets.token_urlsafe(16)
    google_url = google_auth_url(state)
    _google_button("Continue with Google", google_url)

    labeled_divider("or sign in with email")

    with st.form("login_form"):
        email_in = st.text_input("Email", placeholder="you@example.com")
        pass_in  = st.text_input("Password", type="password", placeholder="••••••••")
        if st.form_submit_button("Sign In", use_container_width=True):
            if not email_in or not pass_in:
                toast_error("Please fill in all fields.")
            else:
                signed_in_user = None
                sign_err = None
                with get_db() as db:
                    signed_in_user, sign_err = login_user(db, email_in, pass_in)
                if sign_err:
                    toast_error(sign_err)
                else:
                    login(signed_in_user)
                    toast_success(f"Welcome back, {signed_in_user.name.split()[0]}!")
                    st.switch_page("pages/dashboard.py")


# ═══════════════════════════════════════════════════════════════════
#  CREATE ACCOUNT TAB
# ═══════════════════════════════════════════════════════════════════
else:

    state = "google:" + secrets.token_urlsafe(16)
    google_url = google_auth_url(state)
    _google_button("Sign up with Google", google_url)

    labeled_divider("or create with email")

    with st.form("register_form"):
        reg_name  = st.text_input("Full Name", placeholder="Alex Johnson")
        reg_email = st.text_input("Email", placeholder="you@example.com")
        reg_pass  = st.text_input(
            "Password", type="password",
            placeholder="Min. 8 chars, 1 uppercase, 1 number",
        )
        reg_city  = st.text_input("Your City", placeholder="e.g. Bangalore, Mumbai, Delhi")
        reg_time  = st.selectbox(
            "When do you want your morning brief?",
            ["06:00 AM", "06:30 AM", "07:00 AM", "07:30 AM",
             "08:00 AM", "08:30 AM", "09:00 AM", "09:30 AM", "10:00 AM"],
            index=2,
        )
        reg_tz = st.selectbox(
            "Your timezone",
            ["Asia/Kolkata", "America/New_York", "America/Los_Angeles",
             "Europe/London", "Asia/Singapore", "UTC"],
        )
        if st.form_submit_button("Create Account", use_container_width=True):
            if not reg_name or not reg_email or not reg_pass:
                toast_error("Please fill in all required fields.")
            elif len(reg_pass) < 8:
                toast_error("Password must be at least 8 characters.")
            else:
                new_user = None
                reg_err = None
                with get_db() as db:
                    new_user, reg_err = register_user(db, reg_name, reg_email, reg_pass)
                    if not reg_err:
                        prefs = db.query(UserPreferences).filter_by(user_id=new_user.id).first()
                        if prefs:
                            prefs.location   = reg_city.strip()
                            prefs.timezone   = reg_tz
                            prefs.brief_time = datetime.strptime(reg_time, "%I:%M %p").strftime("%H:%M")
                            db.flush()
                if reg_err:
                    toast_error(reg_err)
                else:
                    # login() opens its own DB session — must be outside the block above
                    login(new_user)
                    toast_success(f"Welcome to Flora OS, {new_user.name.split()[0]}!")
                    st.switch_page("pages/onboarding.py")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center;margin-top:2.5rem;font-size:0.76rem;
                color:var(--text-muted);line-height:1.7;">
      By signing in you agree to Flora OS Terms of Service &amp; Privacy Policy.<br>
      Your data is never sold or shared with third parties.
    </div>
    """,
    unsafe_allow_html=True,
)
