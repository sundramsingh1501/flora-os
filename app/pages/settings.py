"""
Flora OS — Settings Page
Account, Gmail connection, news preferences, career, market watchlist.
"""

import streamlit as st

from app.auth.session import require_auth, get_user_preferences
from app.auth.token_manager import save_oauth_token
from app.auth.google_oauth import get_gmail_authorization_url as google_auth_url, get_token_expiry
from app.database import get_db
from app.models import GmailConnection, UserPreferences, User
from app.ui.theme import apply_theme
from app.ui.navbar import render_navbar
from app.ui.components import section_header, labeled_divider, toast_success, toast_error
from app.utils.encryption import encrypt
from app.utils.logger import get_logger
from app.config import settings as app_settings
import secrets
from datetime import datetime, timezone

logger = get_logger("pages.settings")

apply_theme()
user = require_auth()
render_navbar(user, active_page="Settings")

# ── Gmail connect result (set by main.py after OAuth redirect) ────────────────
if "gmail_connect_result" in st.session_state:
    _gcr = st.session_state.pop("gmail_connect_result")
    if _gcr.get("success"):
        toast_success(f"Gmail connected: {_gcr['email']}")
    else:
        toast_error(_gcr.get("error", "Gmail connection failed."))

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_account, tab_gmail, tab_news, tab_career, tab_market = st.tabs([
    "👤 Account", "✉️ Gmail", "📰 News", "💼 Career", "📈 Market"
])

# ── Account tab ───────────────────────────────────────────────────────────────
with tab_account:
    section_header("Your Account", "")

    avatar = user.avatar_url or ""
    avatar_html = (
        f'<img src="{avatar}" style="width:80px;height:80px;border-radius:50%;object-fit:cover;border:3px solid var(--border);">'
        if avatar else
        f'<div style="width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,var(--accent-purple),var(--accent-blue));'
        f'display:flex;align-items:center;justify-content:center;font-weight:800;font-size:2rem;">'
        f'{user.name[0].upper()}</div>'
    )
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:1.5rem;margin-bottom:1.5rem;">
          {avatar_html}
          <div>
            <div style="font-size:1.25rem;font-weight:700;">{user.name}</div>
            <div style="color:var(--text-secondary);">{user.email}</div>
            <div style="margin-top:6px;">
              <span class="badge badge-purple">{user.auth_provider.upper()}</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("update_name_form"):
        new_name = st.text_input("Display Name", value=user.name)
        if st.form_submit_button("Update Name"):
            with get_db() as db:
                u = db.query(User).filter_by(id=user.id).first()
                if u:
                    u.name = new_name.strip()
            st.session_state["flora_user"] = None  # force reload
            toast_success("Name updated.")
            st.rerun()

    if user.auth_provider == "email":
        labeled_divider("Change Password")
        with st.form("change_pass_form"):
            cur_pass = st.text_input("Current Password", type="password")
            new_pass = st.text_input("New Password", type="password")
            con_pass = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Change Password"):
                if new_pass != con_pass:
                    toast_error("Passwords do not match.")
                else:
                    with get_db() as db:
                        u = db.query(User).filter_by(id=user.id).first()
                        from app.auth.email_auth import change_password
                        ok, err = change_password(db, u, cur_pass, new_pass)
                    if ok:
                        toast_success("Password changed. Please log in again.")
                    else:
                        toast_error(err)

# ── Gmail tab ─────────────────────────────────────────────────────────────────
with tab_gmail:
    section_header("Gmail Connection", "Read-only access. Flora never sends emails without your approval.")

    with get_db() as db:
        gmail_conn = db.query(GmailConnection).filter_by(user_id=user.id).first()
        gmail_info = {
            "address": gmail_conn.gmail_address if gmail_conn else None,
            "is_active": gmail_conn.is_active if gmail_conn else False,
            "connected_at": str(gmail_conn.connected_at)[:16] if gmail_conn else "",
            "last_synced": str(gmail_conn.last_synced)[:16] if gmail_conn and gmail_conn.last_synced else "Never",
        } if gmail_conn else None

    if gmail_info and gmail_info["is_active"]:
        st.markdown(
            f"""
            <div class="flora-card" style="margin-bottom:1.5rem;">
              <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <div style="width:40px;height:40px;background:rgba(74,222,128,0.15);border-radius:50%;
                            display:flex;align-items:center;justify-content:center;font-size:1.2rem;">✉️</div>
                <div>
                  <div style="font-weight:700;">Connected</div>
                  <div style="font-size:0.82rem;color:var(--text-secondary);">{gmail_info["address"]}</div>
                </div>
                <span class="badge badge-green" style="margin-left:auto;">ACTIVE</span>
              </div>
              <div style="font-size:0.8rem;color:var(--text-muted);">
                Connected: {gmail_info["connected_at"]} &nbsp;·&nbsp; Last synced: {gmail_info["last_synced"]}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Reconnect Gmail", use_container_width=True):
                state = f"gmail:{user.id}:{secrets.token_urlsafe(16)}"
                st.session_state["gmail_oauth_state"] = state
                redirect = app_settings.google_redirect_uri
                url = google_auth_url(state).replace(
                    f"redirect_uri={app_settings.google_redirect_uri}",
                    f"redirect_uri={redirect}"
                )
                st.markdown(f'<meta http-equiv="refresh" content="0; url={url}">', unsafe_allow_html=True)
        with col2:
            if st.button("🗑️ Disconnect Gmail", use_container_width=True):
                with get_db() as db:
                    gc = db.query(GmailConnection).filter_by(user_id=user.id).first()
                    if gc:
                        gc.is_active = False
                toast_success("Gmail disconnected.")
                st.rerun()
    else:
        st.markdown(
            """
            <div class="flora-card" style="text-align:center;padding:2rem;margin-bottom:1.5rem;">
              <div style="font-size:2.5rem;margin-bottom:1rem;">✉️</div>
              <div style="font-size:1rem;font-weight:700;margin-bottom:0.5rem;">Connect Gmail</div>
              <div style="font-size:0.875rem;color:var(--text-secondary);max-width:400px;margin:0 auto;">
                Connect once. Flora reads your emails every morning, summarizes them,
                extracts action items, and prepares reply drafts — all privately.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🔵  Connect Gmail with Google", use_container_width=False):
            if not app_settings.google_client_id:
                toast_error("Google OAuth not configured. Add GOOGLE_CLIENT_ID to your .env file.")
            else:
                state = f"gmail:{user.id}:{secrets.token_urlsafe(16)}"
                st.session_state["gmail_oauth_state"] = state
                url = google_auth_url(state)
                st.markdown(f'<meta http-equiv="refresh" content="0; url={url}">', unsafe_allow_html=True)

    st.markdown(
        """
        <div style="font-size:0.78rem;color:var(--text-muted);margin-top:1rem;line-height:1.6;">
          🔒 Flora uses read-only Gmail access. We never read emails outside the scope you approve.
          Flora never sends, deletes, or modifies any emails. You can disconnect anytime.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── News tab ──────────────────────────────────────────────────────────────────
with tab_news:
    section_header("News Preferences", "Which topics should appear in your morning brief?")

    # Daily email toggle
    with get_db() as db:
        _ep = db.query(UserPreferences).filter_by(user_id=user.id).first()
        _email_active = _ep.morning_email_active if _ep else False
        _morning_msg  = _ep.morning_message or "" if _ep else ""
        _brief_t      = _ep.brief_time or "07:00" if _ep else "07:00"

    try:
        _brief_display = datetime.strptime(_brief_t, "%H:%M").strftime("%I:%M %p")
    except Exception:
        _brief_display = _brief_t

    _status_badge = (
        '<span style="background:rgba(74,222,128,0.15);color:#4ade80;border-radius:20px;'
        'padding:2px 12px;font-size:0.78rem;font-weight:700;">ACTIVE</span>'
        if _email_active else
        '<span style="background:rgba(248,113,113,0.15);color:#f87171;border-radius:20px;'
        'padding:2px 12px;font-size:0.78rem;font-weight:700;">INACTIVE</span>'
    )
    st.markdown(
        f"""
        <div style="background:var(--bg-glass);border:1px solid var(--border);
                    border-radius:12px;padding:16px 20px;margin-bottom:1.5rem;
                    display:flex;align-items:center;justify-content:space-between;">
          <div>
            <div style="font-weight:700;margin-bottom:4px;">
              Daily Morning Email &nbsp; {_status_badge}
            </div>
            <div style="font-size:0.82rem;color:var(--text-secondary);">
              Delivered to <strong>{user.email}</strong> at {_brief_display}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_ea, col_eb, col_ec = st.columns(3)
    with col_ea:
        if _email_active:
            if st.button("⏸ Deactivate Daily Email", use_container_width=True):
                with get_db() as db:
                    p = db.query(UserPreferences).filter_by(user_id=user.id).first()
                    if p:
                        p.morning_email_active = False
                toast_success("Daily email deactivated.")
                st.rerun()
        else:
            if st.button("▶ Activate Daily Email", use_container_width=True):
                with get_db() as db:
                    p = db.query(UserPreferences).filter_by(user_id=user.id).first()
                    if p:
                        p.morning_email_active = True
                toast_success("Daily email activated!")
                st.rerun()

    with st.form("brief_time_inline_form"):
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            new_brief_t = st.text_input(
                "Delivery Time (HH:MM, 24h)",
                value=_brief_t,
                placeholder="07:00",
                help="Time at which Flora emails your morning brief.",
            )
        with col_t2:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            save_time = st.form_submit_button("Save Time", use_container_width=True)
        if save_time:
            with get_db() as db:
                p = db.query(UserPreferences).filter_by(user_id=user.id).first()
                if p:
                    p.brief_time = new_brief_t.strip()
            toast_success(f"Delivery time set to {new_brief_t.strip()}.")
            st.rerun()

    with st.form("morning_msg_form"):
        new_msg = st.text_area(
            "Custom morning message",
            value=_morning_msg,
            max_chars=400,
            height=80,
            help="Shown at the top of every morning email.",
        )
        if st.form_submit_button("Save Message", use_container_width=True):
            with get_db() as db:
                p = db.query(UserPreferences).filter_by(user_id=user.id).first()
                if p:
                    p.morning_message = new_msg.strip()
            toast_success("Morning message saved.")

    # ── Email topics — free-form ──────────────────────────────────────────────
    labeled_divider("Daily Email Topics")

    with get_db() as db:
        _ep2 = db.query(UserPreferences).filter_by(user_id=user.id).first()
        if _ep2 and _ep2.email_topics:
            _saved_email = list(_ep2.email_topics)
        elif _ep2 and _ep2.news_categories:
            # Fall back to their onboarding news choices
            _saved_email = list(_ep2.news_categories)
        else:
            _saved_email = ["AI & Machine Learning", "Data Science", "GenAI & LLMs",
                            "Technology", "Indian News", "Indian Stock Market", "Sports News"]

    # Always sync from DB unless user is actively editing (button pressed this run)
    if "cfg_email_topics" not in st.session_state or st.session_state.get("_reload_prefs"):
        st.session_state.cfg_email_topics = _saved_email

    _EMAIL_SUGG = [
        "AI & Machine Learning", "Data Science", "GenAI & LLMs", "Research Papers",
        "Technology", "Startups", "Indian News", "Indian Stock Market", "Sports News",
        "Cricket", "Football", "World News", "Business", "Finance & Investing",
        "Crypto", "GitHub & Open Source", "Career & Jobs", "Science",
        "Health & Wellness", "Politics", "Climate & Environment",
    ]

    col_ei, col_eb = st.columns([4, 1])
    with col_ei:
        et_new = st.text_input("Search or type any email topic", placeholder="e.g. Indian Stock Market, Sports News…",
                               key="cfg_email_inp", label_visibility="collapsed")
    with col_eb:
        if st.button("Add", key="cfg_email_add", use_container_width=True):
            t = et_new.strip().title()
            if t and t not in st.session_state.cfg_email_topics:
                st.session_state.cfg_email_topics.append(t)
                st.rerun()

    st.markdown("<div style='font-size:0.78rem;color:#7070a0;margin:6px 0 2px;'>Suggestions:</div>", unsafe_allow_html=True)
    es_cols = st.columns(4)
    for i, s in enumerate(_EMAIL_SUGG):
        with es_cols[i % 4]:
            if s not in st.session_state.cfg_email_topics:
                if st.button(f"+ {s}", key=f"es_{i}", use_container_width=True):
                    st.session_state.cfg_email_topics.append(s)
                    st.rerun()

    if st.session_state.cfg_email_topics:
        st.markdown("<div style='font-size:0.78rem;color:#7070a0;margin:10px 0 2px;'>Selected (click to remove):</div>", unsafe_allow_html=True)
        er_cols = st.columns(4)
        for i, t in enumerate(list(st.session_state.cfg_email_topics)):
            with er_cols[i % 4]:
                if st.button(f"✕ {t}", key=f"er_{i}", use_container_width=True):
                    st.session_state.cfg_email_topics.remove(t)
                    st.rerun()

    if st.button("💾 Save Email Topics", use_container_width=True, key="save_email_topics"):
        if len(st.session_state.cfg_email_topics) < 2:
            toast_error("Select at least 2 topics.")
        else:
            with get_db() as db:
                p = db.query(UserPreferences).filter_by(user_id=user.id).first()
                if p:
                    p.email_topics = st.session_state.cfg_email_topics
            toast_success("Email topics saved.")

    # ── Web Brief Topics — free-form ──────────────────────────────────────────
    labeled_divider("Web Brief Topics")

    with get_db() as db:
        prefs = db.query(UserPreferences).filter_by(user_id=user.id).first()
        _saved_web = list(prefs.news_categories or []) if prefs else []

    if "cfg_web_topics" not in st.session_state or st.session_state.get("_reload_prefs"):
        st.session_state.cfg_web_topics = _saved_web
    st.session_state.pop("_reload_prefs", None)

    _WEB_SUGG = [
        "AI & Machine Learning", "Data Science", "GenAI & LLMs", "Research Papers",
        "Technology", "Startups", "World News", "Indian News", "Indian Stock Market",
        "Business", "Finance & Investing", "Crypto", "GitHub & Open Source",
        "Career & Jobs", "Product & Design", "Science", "Sports News",
        "Cricket", "Football", "Politics", "Health & Wellness",
    ]

    col_wi, col_wb = st.columns([4, 1])
    with col_wi:
        wt_new = st.text_input("Search or type any web topic", placeholder="e.g. Indian Stock Market, Sports News…",
                               key="cfg_web_inp", label_visibility="collapsed")
    with col_wb:
        if st.button("Add", key="cfg_web_add", use_container_width=True):
            t = wt_new.strip().title()
            if t and t not in st.session_state.cfg_web_topics:
                st.session_state.cfg_web_topics.append(t)
                st.rerun()

    st.markdown("<div style='font-size:0.78rem;color:#7070a0;margin:6px 0 2px;'>Suggestions:</div>", unsafe_allow_html=True)
    ws_cols = st.columns(4)
    for i, s in enumerate(_WEB_SUGG):
        with ws_cols[i % 4]:
            if s not in st.session_state.cfg_web_topics:
                if st.button(f"+ {s}", key=f"ws_{i}", use_container_width=True):
                    st.session_state.cfg_web_topics.append(s)
                    st.rerun()

    if st.session_state.cfg_web_topics:
        st.markdown("<div style='font-size:0.78rem;color:#7070a0;margin:10px 0 2px;'>Selected (click to remove):</div>", unsafe_allow_html=True)
        wr_cols = st.columns(4)
        for i, t in enumerate(list(st.session_state.cfg_web_topics)):
            with wr_cols[i % 4]:
                if st.button(f"✕ {t}", key=f"wr_{i}", use_container_width=True):
                    st.session_state.cfg_web_topics.remove(t)
                    st.rerun()

    if st.button("💾 Save Web Topics", use_container_width=True, key="save_web_topics"):
        if len(st.session_state.cfg_web_topics) < 2:
            toast_error("Select at least 2 topics.")
        else:
            with get_db() as db:
                p = db.query(UserPreferences).filter_by(user_id=user.id).first()
                if p:
                    p.news_categories = st.session_state.cfg_web_topics
            st.cache_data.clear()
            toast_success("Web topics saved.")

# ── Career tab ────────────────────────────────────────────────────────────────
with tab_career:
    section_header("Career Preferences", "Flora uses these to find personalized jobs and learning resources.")

    with get_db() as db:
        prefs = db.query(UserPreferences).filter_by(user_id=user.id).first()
        if prefs:
            cur_roles   = list(prefs.job_roles or [])
            cur_locs    = list(prefs.job_locations or [])
            cur_tech    = list(prefs.tech_stack or [])
            cur_exp_yrs = prefs.experience_years or 0
        else:
            cur_roles, cur_locs, cur_tech, cur_exp_yrs = [], [], [], 0

    _EXP_OPTIONS = [
        "Fresher (0–1 yr)",
        "Junior (1–3 yrs)",
        "Mid-level (3–5 yrs)",
        "Senior (5+ yrs)",
    ]
    _EXP_YEARS = [0, 1, 3, 5]
    _cur_exp_label = next(
        (lbl for lbl, yr in zip(_EXP_OPTIONS, _EXP_YEARS) if yr <= cur_exp_yrs),
        _EXP_OPTIONS[0],
    )
    # pick the closest bucket index
    _exp_idx = max(
        (i for i, yr in enumerate(_EXP_YEARS) if yr <= cur_exp_yrs),
        default=0,
    )

    all_roles = [
        "Software Engineer", "ML Engineer", "Data Scientist", "AI Researcher",
        "Product Manager", "Designer", "DevOps Engineer", "Backend Engineer",
        "Frontend Engineer", "Full Stack Engineer", "Data Engineer", "Analyst",
    ]
    all_locs = [
        "Remote", "Bangalore", "Mumbai", "Delhi NCR", "Hyderabad", "Pune",
        "Chennai", "New York", "San Francisco", "London", "Singapore",
    ]
    all_tech = [
        "Python", "JavaScript", "TypeScript", "React", "Node.js", "Go",
        "Rust", "Java", "C++", "SQL", "PostgreSQL", "AWS", "GCP", "Azure",
        "Docker", "Kubernetes", "LangChain", "PyTorch", "TensorFlow",
    ]

    with st.form("career_prefs_form"):
        exp_sel   = st.selectbox(
            "Experience Level",
            _EXP_OPTIONS,
            index=_exp_idx,
            help="Flora uses this to filter job recommendations by seniority.",
        )
        roles_sel = st.multiselect("Target Roles", all_roles, default=cur_roles)
        locs_sel  = st.multiselect("Preferred Locations", all_locs, default=cur_locs)
        tech_sel  = st.multiselect("Your Tech Stack", all_tech, default=cur_tech)
        if st.form_submit_button("Save Career Preferences", use_container_width=True):
            exp_years_val = _EXP_YEARS[_EXP_OPTIONS.index(exp_sel)]
            with get_db() as db:
                p = db.query(UserPreferences).filter_by(user_id=user.id).first()
                if p:
                    p.job_roles        = roles_sel
                    p.job_locations    = locs_sel
                    p.tech_stack       = tech_sel
                    p.experience_years = exp_years_val
            st.cache_data.clear()
            toast_success("Career preferences saved.")

# ── Market tab ────────────────────────────────────────────────────────────────
with tab_market:
    section_header("Market Watchlist", "Stocks and crypto Flora tracks for you every morning.")

    with get_db() as db:
        prefs = db.query(UserPreferences).filter_by(user_id=user.id).first()
        _mkt_stocks  = list(prefs.stock_watchlist or []) if prefs else []
        _mkt_cryptos = list(prefs.crypto_watchlist or []) if prefs else []
        cur_loc      = prefs.location or "" if prefs else ""
        cur_tz       = prefs.timezone or "Asia/Kolkata" if prefs else "Asia/Kolkata"

    # ── Stocks tag editor ─────────────────────────────────────────────────────
    labeled_divider("Stock Watchlist")

    if "mkt_stocks" not in st.session_state:
        st.session_state.mkt_stocks = _mkt_stocks
    if "mkt_cryptos" not in st.session_state:
        st.session_state.mkt_cryptos = _mkt_cryptos

    _STOCK_SUGG = ["RELIANCE", "TCS", "INFY", "WIPRO", "HDFCBANK", "SBIN",
                   "ADANIENT", "BAJFINANCE", "NIFTY50", "AAPL", "GOOGL", "MSFT", "NVDA", "TSLA"]
    _CRYPTO_SUGG = ["bitcoin", "ethereum", "solana", "binancecoin", "ripple", "dogecoin"]

    col_si, col_sb = st.columns([4, 1])
    with col_si:
        stock_inp = st.text_input("Add ticker symbol", placeholder="e.g. RELIANCE, AAPL",
                                  key="mkt_stock_inp", label_visibility="collapsed")
    with col_sb:
        if st.button("Add", key="mkt_stock_add", use_container_width=True):
            t = stock_inp.strip().upper()
            if t and t not in st.session_state.mkt_stocks:
                st.session_state.mkt_stocks.append(t)
                st.rerun()

    st.markdown("<div style='font-size:0.78rem;color:#7070a0;margin:6px 0 2px;'>Popular stocks:</div>", unsafe_allow_html=True)
    st_sugg_cols = st.columns(4)
    for i, s in enumerate(_STOCK_SUGG):
        with st_sugg_cols[i % 4]:
            if s not in st.session_state.mkt_stocks:
                if st.button(f"+ {s}", key=f"ss_{i}", use_container_width=True):
                    st.session_state.mkt_stocks.append(s)
                    st.rerun()

    if st.session_state.mkt_stocks:
        st.markdown("<div style='font-size:0.78rem;color:#7070a0;margin:10px 0 2px;'>Your watchlist (click to remove):</div>", unsafe_allow_html=True)
        sr_cols = st.columns(4)
        for i, t in enumerate(list(st.session_state.mkt_stocks)):
            with sr_cols[i % 4]:
                if st.button(f"✕ {t}", key=f"sr_{i}", use_container_width=True):
                    st.session_state.mkt_stocks.remove(t)
                    st.rerun()

    # ── Crypto tag editor ─────────────────────────────────────────────────────
    labeled_divider("Crypto Watchlist")

    col_ci, col_cb = st.columns([4, 1])
    with col_ci:
        crypto_inp = st.text_input("Add coin (CoinGecko ID)", placeholder="e.g. bitcoin, ethereum, solana",
                                   key="mkt_crypto_inp", label_visibility="collapsed")
    with col_cb:
        if st.button("Add", key="mkt_crypto_add", use_container_width=True):
            t = crypto_inp.strip().lower()
            if t and t not in st.session_state.mkt_cryptos:
                st.session_state.mkt_cryptos.append(t)
                st.rerun()

    st.markdown("<div style='font-size:0.78rem;color:#7070a0;margin:6px 0 2px;'>Popular coins:</div>", unsafe_allow_html=True)
    cr_sugg_cols = st.columns(4)
    for i, s in enumerate(_CRYPTO_SUGG):
        with cr_sugg_cols[i % 4]:
            if s not in st.session_state.mkt_cryptos:
                if st.button(f"+ {s}", key=f"cs_{i}", use_container_width=True):
                    st.session_state.mkt_cryptos.append(s)
                    st.rerun()

    if st.session_state.mkt_cryptos:
        st.markdown("<div style='font-size:0.78rem;color:#7070a0;margin:10px 0 2px;'>Your watchlist (click to remove):</div>", unsafe_allow_html=True)
        cr_cols = st.columns(4)
        for i, t in enumerate(list(st.session_state.mkt_cryptos)):
            with cr_cols[i % 4]:
                if st.button(f"✕ {t}", key=f"cr_{i}", use_container_width=True):
                    st.session_state.mkt_cryptos.remove(t)
                    st.rerun()

    # ── Location / timezone ───────────────────────────────────────────────────
    labeled_divider("Location & Timezone")
    _TZ_OPTIONS = ["Asia/Kolkata", "America/New_York", "America/Los_Angeles",
                   "Europe/London", "Asia/Singapore", "UTC"]
    with st.form("market_prefs_form"):
        location_inp = st.text_input("Your City (for weather)", value=cur_loc, placeholder="Bangalore")
        tz_sel = st.selectbox(
            "Timezone",
            _TZ_OPTIONS,
            index=_TZ_OPTIONS.index(cur_tz) if cur_tz in _TZ_OPTIONS else 0,
        )
        if st.form_submit_button("Save Location & Timezone", use_container_width=True):
            with get_db() as db:
                p = db.query(UserPreferences).filter_by(user_id=user.id).first()
                if p:
                    p.location = location_inp.strip()
                    p.timezone = tz_sel
            st.cache_data.clear()
            toast_success("Location & timezone saved.")

    if st.button("💾 Save Watchlists", use_container_width=True, key="save_watchlists"):
        with get_db() as db:
            p = db.query(UserPreferences).filter_by(user_id=user.id).first()
            if p:
                p.stock_watchlist  = st.session_state.mkt_stocks
                p.crypto_watchlist = st.session_state.mkt_cryptos
        st.cache_data.clear()
        toast_success("Watchlists saved.")
