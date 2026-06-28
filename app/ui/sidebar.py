"""
Flora OS -- Sidebar Navigation
Renders the persistent left sidebar with user info and page links.
"""

import streamlit as st
from app.auth.session import logout
from app.models import User


_PAGES = [
    ("Home",      "Dashboard",      "pages/dashboard.py"),
    ("Brief",     "Morning Brief",  "pages/morning_brief.py"),
    ("Email",     "Email Hub",      "pages/email_hub.py"),
    ("Jobs",      "Job Board",      "pages/job_board.py"),
    ("Markets",   "Markets",        "pages/market.py"),
    ("Settings",  "Settings",       "pages/settings.py"),
]

_ICONS = {
    "Dashboard":     "&#127968;",
    "Morning Brief": "&#128240;",
    "Email Hub":     "&#9993;",
    "Job Board":     "&#128188;",
    "Markets":       "&#128200;",
    "Settings":      "&#9881;",
}


def render_sidebar(user: User, active_page: str = "Dashboard") -> None:
    with st.sidebar:
        # Logo
        st.markdown(
            """
            <div style="padding:0.5rem 0 1.5rem;">
              <div style="font-size:1.4rem;font-weight:800;letter-spacing:-0.03em;
                          background:linear-gradient(135deg,#7c6af7,#38bdf8);
                          -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                          background-clip:text;">
                Flora OS
              </div>
              <div style="font-size:0.7rem;color:var(--text-muted);margin-top:2px;letter-spacing:0.08em;">
                YOUR PERSONAL AI
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Navigation
        for _, label, page_path in _PAGES:
            is_active = label == active_page
            if st.button(
                label,
                key=f"nav_{label}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.switch_page(page_path)

        st.markdown("---")

        # User profile
        avatar = user.avatar_url or ""
        avatar_html = (
            f'<img src="{avatar}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;">'
            if avatar
            else f'<div style="width:32px;height:32px;border-radius:50%;background:var(--accent-purple);'
                 f'display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.8rem;">'
                 f'{user.name[0].upper()}</div>'
        )
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:10px;padding:0.5rem 0;">
              {avatar_html}
              <div>
                <div style="font-weight:600;font-size:0.85rem;">{user.name}</div>
                <div style="font-size:0.72rem;color:var(--text-muted);">{user.email}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Sign Out", use_container_width=True, key="sidebar_logout"):
            logout()
