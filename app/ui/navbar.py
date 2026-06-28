"""
Flora OS — Navigation
Top page header + slim professional left sidebar.
"""

import streamlit as st
from app.models import User
from app.auth.session import logout


_NAV_ITEMS = [
    ("🏠", "Dashboard",     "pages/dashboard.py"),
    ("📰", "Morning Brief", "pages/morning_brief.py"),
    ("✉️",  "Email Hub",     "pages/email_hub.py"),
    ("💼", "Job Board",     "pages/job_board.py"),
    ("📈", "Markets",       "pages/market.py"),
    ("⚙️",  "Settings",      "pages/settings.py"),
]

_NAV_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Force sidebar always open — never slide off-screen ──────── */
[data-testid="stSidebar"] {
  transform: none !important;
  left: 0 !important;
  visibility: visible !important;
}
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
button[kind="header"] { display: none !important; }

/* ── Sidebar panel ──────────────────────────────────── */
[data-testid="stSidebar"] {
  background: #0c0c18 !important;
  border-right: 1px solid rgba(255,255,255,0.06) !important;
  padding: 0 !important;
  width: 220px !important;
  min-width: 220px !important;
}
[data-testid="stSidebar"] > div {
  padding: 0 !important;
}
[data-testid="stSidebarContent"] {
  padding: 0 !important;
}

/* ── Zero out ALL Streamlit wrapper padding in sidebar ── */
[data-testid="stSidebar"] [data-testid="element-container"],
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > *,
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stSidebar"] .row-widget,
[data-testid="stSidebar"] .stButton {
  padding: 0 !important;
  margin: 0 !important;
  width: 100% !important;
  box-sizing: border-box !important;
}

/* ── page_link nav items ── */
[data-testid="stSidebar"] [data-testid="stPageLink"] {
  padding: 0 !important;
  margin: 0 !important;
  width: 100% !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a,
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  padding: 11px 18px !important;
  width: 100% !important;
  box-sizing: border-box !important;
  border-left: 3px solid transparent !important;
  border-top: none !important;
  border-right: none !important;
  border-bottom: none !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: #7070a0 !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  text-decoration: none !important;
  transition: background 0.15s ease, color 0.15s ease !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover,
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
  background: rgba(255,255,255,0.05) !important;
  color: #e8e8ff !important;
}
/* Active page link */
[data-testid="stSidebar"] .flora-nav-active [data-testid="stPageLink"] a,
[data-testid="stSidebar"] .flora-nav-active [data-testid="stPageLink-NavLink"] {
  background: rgba(124,106,247,0.12) !important;
  color: #c4b5fd !important;
  border-left: 3px solid #7c6af7 !important;
  font-weight: 600 !important;
}
[data-testid="stSidebar"] .flora-nav-active [data-testid="stPageLink"] a:hover,
[data-testid="stSidebar"] .flora-nav-active [data-testid="stPageLink-NavLink"]:hover {
  background: rgba(124,106,247,0.2) !important;
  color: #d8c8ff !important;
}

/* Logout button in sidebar */
[data-testid="stSidebar"] .flora-logout .stButton > button {
  background: rgba(248,113,113,0.08) !important;
  border: 1px solid rgba(248,113,113,0.18) !important;
  border-radius: 10px !important;
  color: #f87171 !important;
  font-size: 0.82rem !important;
  justify-content: center !important;
  width: 100% !important;
  padding: 8px 14px !important;
}
[data-testid="stSidebar"] .flora-logout .stButton > button:hover {
  background: rgba(248,113,113,0.18) !important;
}
[data-testid="stSidebar"] .flora-logout .stButton {
  padding: 0 8px !important;
}

/* ── Main area top padding ─────────────────────────── */
.block-container {
  padding-top: 1.5rem !important;
  padding-left: 2rem !important;
  padding-right: 2rem !important;
  max-width: 1400px !important;
}

/* ── Page top bar (breadcrumb + user) ──────────────── */
.flora-pagebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 1.5rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  margin-bottom: 2rem;
}
.flora-pagebar-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: #f0f0ff;
  letter-spacing: -0.02em;
}
.flora-pagebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
}
.flora-pagebar-avatar {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7c6af7, #38bdf8);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 0.9rem; color: white;
  border: 2px solid rgba(124,106,247,0.35);
  overflow: hidden;
}
.flora-pagebar-info { text-align: right; }
.flora-pagebar-name { font-size: 0.85rem; font-weight: 600; color: #e0e0ff; }
.flora-pagebar-email { font-size: 0.72rem; color: #55556a; }
</style>
"""


def _avatar_html(user: User, size: int = 36) -> str:
    if user.avatar_url:
        return f'<img src="{user.avatar_url}" style="width:{size}px;height:{size}px;border-radius:50%;object-fit:cover;">'
    initial = (user.name or "?")[0].upper()
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
        f'background:linear-gradient(135deg,#7c6af7,#38bdf8);'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-weight:700;font-size:{int(size*0.4)}px;color:white;">{initial}</div>'
    )


_PAGE_SUBTITLES = {
    "Dashboard":     "Good morning — here's what's happening",
    "Morning Brief": "Your curated daily news digest",
    "Email Hub":     "Inbox intelligence & action items",
    "Job Board":     "Personalized opportunities for you",
    "Markets":       "Real-time market data & watchlist",
    "Settings":      "Account, connections & preferences",
}


def render_navbar(user: User, active_page: str = "Dashboard") -> None:
    """Render the sidebar nav + top page header."""
    st.markdown(_NAV_CSS, unsafe_allow_html=True)

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        # Logo
        st.markdown(
            """
            <div style="padding:28px 18px 20px;border-bottom:1px solid rgba(255,255,255,0.06);">
              <div style="display:flex;align-items:center;gap:10px;">
                <div style="font-size:1.5rem;line-height:1;">🌿</div>
                <div>
                  <div style="font-size:1.05rem;font-weight:800;letter-spacing:-0.04em;
                              background:linear-gradient(135deg,#a78bfa,#38bdf8);
                              -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                              background-clip:text;line-height:1.2;">Flora OS</div>
                  <div style="font-size:0.58rem;letter-spacing:0.14em;text-transform:uppercase;
                              color:#55556a;margin-top:2px;">Personal AI</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Navigation items
        st.markdown(
            '<div style="font-size:0.65rem;font-weight:600;letter-spacing:0.12em;'
            'text-transform:uppercase;color:#3a3a5c;padding:14px 18px 8px;">Navigation</div>',
            unsafe_allow_html=True,
        )

        for icon, label, path in _NAV_ITEMS:
            is_active = label == active_page
            if is_active:
                st.markdown('<div class="flora-nav-active">', unsafe_allow_html=True)
            st.page_link(path, label=f"{icon}  {label}", use_container_width=True)
            if is_active:
                st.markdown('</div>', unsafe_allow_html=True)

        # Divider + User profile
        st.markdown(
            """
            <div style="position:absolute;bottom:0;left:0;right:0;
                        padding:14px 16px;
                        border-top:1px solid rgba(255,255,255,0.06);
                        background:#0c0c18;">
            """,
            unsafe_allow_html=True,
        )
        avatar = _avatar_html(user, size=36)
        first = (user.name or "User").split()[0]
        email_short = user.email if len(user.email) < 24 else user.email[:21] + "…"
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
              {avatar}
              <div style="overflow:hidden;">
                <div style="font-size:0.83rem;font-weight:600;color:#e0e0ff;
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                  {user.name}
                </div>
                <div style="font-size:0.68rem;color:#55556a;
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                  {email_short}
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="flora-logout">', unsafe_allow_html=True)
        if st.button("Sign Out", key="sidebar_logout", use_container_width=True):
            logout()
        st.markdown("</div></div>", unsafe_allow_html=True)

    # ── Top page header bar ───────────────────────────────────────────────────
    subtitle = _PAGE_SUBTITLES.get(active_page, "")
    avatar_sm = _avatar_html(user, size=36)
    st.markdown(
        f"""
        <div class="flora-pagebar">
          <div>
            <div class="flora-pagebar-title">{active_page}</div>
            <div style="font-size:0.82rem;color:#55556a;margin-top:2px;">{subtitle}</div>
          </div>
          <div class="flora-pagebar-user">
            <div class="flora-pagebar-info">
              <div class="flora-pagebar-name">{user.name}</div>
              <div class="flora-pagebar-email">{user.email}</div>
            </div>
            <div class="flora-pagebar-avatar">{avatar_sm}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
