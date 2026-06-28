"""
Flora OS — Onboarding / Personalization Wizard
Shown once after first registration.
Steps: Topics → Career → Watchlists → Morning Email Setup → Activate
"""

import streamlit as st
from datetime import datetime

from app.auth.session import require_auth
from app.database import get_db
from app.models import UserPreferences, User
from app.ui.theme import apply_theme
from app.ui.components import section_header, toast_success, toast_error
from app.utils.logger import get_logger

logger = get_logger("pages.onboarding")

apply_theme(sidebar_state="collapsed")
user = require_auth()

TOTAL_STEPS = 5

if "onboard_step" not in st.session_state:
    st.session_state.onboard_step = 1

step = st.session_state.onboard_step


def _progress_bar():
    st.markdown(
        f"""
        <div style="max-width:640px;margin:0 auto 2rem;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <div style="font-size:1.3rem;font-weight:800;">
              Welcome to <span style="background:linear-gradient(135deg,#7c6af7,#38bdf8);
              -webkit-background-clip:text;-webkit-text-fill-color:transparent;">Flora OS</span>
            </div>
            <div style="font-size:0.82rem;color:var(--text-secondary);">Step {step} of {TOTAL_STEPS}</div>
          </div>
          <div style="background:var(--bg-elevated);border-radius:100px;height:5px;overflow:hidden;">
            <div style="background:linear-gradient(90deg,#7c6af7,#38bdf8);
                        width:{int(step/TOTAL_STEPS*100)}%;height:100%;border-radius:100px;
                        transition:width 0.4s ease;"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _nav(back_step=None):
    col1, col2 = st.columns([1, 3])
    with col1:
        if back_step and st.button("← Back", use_container_width=True):
            st.session_state.onboard_step = back_step
            st.rerun()
    return col2


_progress_bar()

st.markdown('<div style="max-width:640px;margin:0 auto;">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# STEP 1 — News topics
# ═══════════════════════════════════════════════════
if step == 1:
    section_header("What do you want to read about?",
                   "Flora will curate your morning brief around these topics.")

    _SUGGESTIONS = [
        "AI & Machine Learning", "Data Science", "GenAI & LLMs",
        "Research Papers", "Technology", "Startups",
        "World News", "Indian News", "Indian Stock Market", "Business",
        "Finance & Investing", "Crypto", "GitHub & Open Source",
        "Career & Jobs", "Product & Design", "Science",
        "Sports News", "Cricket", "Football", "Politics",
        "Health & Wellness", "Climate & Environment",
    ]

    if "ob_topics" not in st.session_state:
        st.session_state.ob_topics = ["AI & Machine Learning", "Technology", "World News"]

    # Free-form custom topic input
    col_inp, col_btn = st.columns([4, 1])
    with col_inp:
        new_topic = st.text_input(
            "Search or type any topic",
            placeholder="e.g. Indian Stock Market, Sports News, Cricket…",
            key="ob_topic_input",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("Add", use_container_width=True, key="ob_add_topic"):
            t = new_topic.strip().title()
            if t and t not in st.session_state.ob_topics:
                st.session_state.ob_topics.append(t)
                st.rerun()

    # Suggestion chips
    st.markdown("<div style='margin-top:8px;margin-bottom:4px;font-size:0.78rem;color:#7070a0;'>Popular suggestions — click to add:</div>", unsafe_allow_html=True)
    suggestion_cols = st.columns(4)
    for i, sug in enumerate(_SUGGESTIONS):
        with suggestion_cols[i % 4]:
            if sug not in st.session_state.ob_topics:
                if st.button(f"+ {sug}", key=f"ob_sug_{i}", use_container_width=True):
                    st.session_state.ob_topics.append(sug)
                    st.rerun()

    # Selected topics display + remove
    if st.session_state.ob_topics:
        st.markdown("<div style='margin-top:16px;margin-bottom:4px;font-size:0.78rem;color:#7070a0;'>Your selected topics:</div>", unsafe_allow_html=True)
        rem_cols = st.columns(4)
        for i, t in enumerate(list(st.session_state.ob_topics)):
            with rem_cols[i % 4]:
                if st.button(f"✕ {t}", key=f"ob_rem_{i}", use_container_width=True):
                    st.session_state.ob_topics.remove(t)
                    st.rerun()

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    if st.button("Continue →", use_container_width=True):
        if len(st.session_state.ob_topics) < 3:
            toast_error("Please add at least 3 topics.")
        else:
            with get_db() as db:
                p = db.query(UserPreferences).filter_by(user_id=user.id).first()
                if p:
                    p.news_categories = st.session_state.ob_topics
            st.session_state.onboard_step = 2
            st.rerun()

# ═══════════════════════════════════════════════════
# STEP 2 — Career
# ═══════════════════════════════════════════════════
elif step == 2:
    section_header("Tell Flora about your career",
                   "Personalized job alerts and career insights just for you.")

    roles = st.multiselect(
        "Job roles you're interested in",
        ["Software Engineer", "ML Engineer", "Data Scientist", "AI Researcher",
         "Product Manager", "Designer", "DevOps Engineer", "Backend Engineer",
         "Frontend Engineer", "Full Stack Engineer", "Data Engineer", "Analyst"],
    )
    locations = st.multiselect(
        "Preferred locations",
        ["Remote", "Bangalore", "Mumbai", "Delhi NCR", "Hyderabad", "Pune",
         "Chennai", "New York", "San Francisco", "London", "Singapore"],
        default=["Remote"],
    )
    tech = st.multiselect(
        "Your tech stack",
        ["Python", "JavaScript", "TypeScript", "React", "Node.js", "Go",
         "Rust", "Java", "C++", "SQL", "PostgreSQL", "AWS", "GCP", "Azure",
         "Docker", "Kubernetes", "LangChain", "PyTorch", "TensorFlow"],
    )

    col_back, col_next = st.columns([1, 3])
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.onboard_step = 1
            st.rerun()
    with col_next:
        if st.button("Continue →", use_container_width=True):
            with get_db() as db:
                p = db.query(UserPreferences).filter_by(user_id=user.id).first()
                if p:
                    p.job_roles = roles
                    p.job_locations = locations
                    p.tech_stack = tech
            st.session_state.onboard_step = 3
            st.rerun()

# ═══════════════════════════════════════════════════
# STEP 3 — Watchlists & Location
# ═══════════════════════════════════════════════════
elif step == 3:
    section_header("Set up your watchlists",
                   "Flora tracks these for your morning market report.")

    stocks_input  = st.text_input("Stock tickers (comma-separated)", value="AAPL, GOOGL, MSFT, TSLA")
    crypto_input  = st.text_input("Crypto coins (comma-separated)", value="bitcoin, ethereum")
    location      = st.text_input("Your city (for weather)", placeholder="e.g. Bangalore, Mumbai, New York")
    timezone_sel  = st.selectbox("Your timezone", [
        "Asia/Kolkata", "America/New_York", "America/Los_Angeles",
        "Europe/London", "Asia/Singapore", "UTC",
    ])

    col_back, col_next = st.columns([1, 3])
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.onboard_step = 2
            st.rerun()
    with col_next:
        if st.button("Continue →", use_container_width=True):
            stocks  = [s.strip().upper() for s in stocks_input.split(",") if s.strip()]
            cryptos = [c.strip().lower() for c in crypto_input.split(",") if c.strip()]
            with get_db() as db:
                p = db.query(UserPreferences).filter_by(user_id=user.id).first()
                if p:
                    p.stock_watchlist  = stocks
                    p.crypto_watchlist = cryptos
                    p.location         = location.strip()
                    p.timezone         = timezone_sel
            st.session_state.onboard_step = 4
            st.rerun()

# ═══════════════════════════════════════════════════
# STEP 4 — Morning Email Personalization
# ═══════════════════════════════════════════════════
elif step == 4:
    section_header("Personalize your morning email",
                   "Flora will send you a personalized news brief every morning at your chosen time.")

    st.markdown(
        """
        <div style="background:var(--bg-glass);border:1px solid var(--border);
                    border-radius:12px;padding:16px 20px;margin-bottom:1.5rem;
                    font-size:0.87rem;color:var(--text-secondary);line-height:1.7;">
          &#127757; Flora will email you <strong style="color:var(--text-primary);">
          yesterday's top news</strong> every morning at your chosen time —
          curated for your interests, personalised with your greeting,
          and delivered straight to your inbox. You can deactivate anytime.
        </div>
        """,
        unsafe_allow_html=True,
    )

    brief_time = st.selectbox(
        "What time do you want your morning brief?",
        ["05:00 AM", "05:30 AM", "06:00 AM", "06:30 AM", "07:00 AM",
         "07:30 AM", "08:00 AM", "08:30 AM", "09:00 AM", "09:30 AM", "10:00 AM"],
        index=4,
    )

    greeting_name = st.text_input(
        "How should Flora greet you?",
        value=user.name.split()[0] if user.name else "",
        placeholder="Your first name or nickname",
        help="This is how Flora will address you in the email: 'Good morning, [name]'"
    )

    morning_message = st.text_area(
        "Custom morning message (optional)",
        placeholder="e.g. Here's your daily dose of what matters. Stay curious, stay sharp. 🚀",
        max_chars=400,
        height=100,
        help="This personal note appears at the top of every morning email.",
    )

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    col_back, col_next = st.columns([1, 3])
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.onboard_step = 3
            st.rerun()
    with col_next:
        if st.button("Continue →", use_container_width=True):
            h_m = datetime.strptime(brief_time, "%I:%M %p").strftime("%H:%M")
            final_msg = morning_message.strip() or (
                f"Here's what happened in the world yesterday. Stay informed, stay ahead."
            )
            with get_db() as db:
                p = db.query(UserPreferences).filter_by(user_id=user.id).first()
                if p:
                    p.brief_time      = h_m
                    p.morning_message = final_msg
            # Save greeting name preference too
            if greeting_name.strip() and greeting_name.strip() != user.name.split()[0]:
                with get_db() as db:
                    u = db.query(User).filter_by(id=user.id).first()
                    if u and greeting_name.strip():
                        # Store full name but use greeting_name in morning_message prefix
                        p2 = db.query(UserPreferences).filter_by(user_id=user.id).first()
                        if p2:
                            p2.morning_message = final_msg
            st.session_state["_onboard_greeting"] = greeting_name.strip()
            st.session_state.onboard_step = 5
            st.rerun()

# ═══════════════════════════════════════════════════
# STEP 5 — Activate
# ═══════════════════════════════════════════════════
elif step == 5:
    first_name = st.session_state.get("_onboard_greeting") or user.name.split()[0]

    # Load saved prefs to show summary
    with get_db() as db:
        p = db.query(UserPreferences).filter_by(user_id=user.id).first()
        brief_time_display = p.brief_time if p else "07:00"
        tz_display = p.timezone if p else "UTC"
        cats = list(p.news_categories or []) if p else []
        morning_msg = p.morning_message if p else ""

    try:
        t = datetime.strptime(brief_time_display, "%H:%M")
        brief_time_display = t.strftime("%I:%M %p")
    except Exception:
        pass

    st.markdown(
        f"""
        <div style="text-align:center;padding:1.5rem 0 2rem;">
          <div style="font-size:3.5rem;margin-bottom:1rem;">&#127807;</div>
          <h2 style="font-size:1.8rem;font-weight:800;letter-spacing:-0.03em;margin-bottom:0.75rem;">
            Flora is ready for you,
            <span style="background:linear-gradient(135deg,#7c6af7,#38bdf8);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
              {first_name}
            </span>
          </h2>
          <p style="color:var(--text-secondary);font-size:0.95rem;max-width:480px;margin:0 auto 2rem;">
            Your morning brief will be delivered to
            <strong style="color:var(--text-primary);">{user.email}</strong>
            every day at <strong style="color:var(--text-primary);">{brief_time_display}</strong>
            ({tz_display}).
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Summary card
    st.markdown(
        f"""
        <div style="background:var(--bg-glass);border:1px solid var(--border);
                    border-radius:12px;padding:20px 24px;margin-bottom:2rem;">
          <div style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.1em;
                      color:var(--text-muted);margin-bottom:12px;">Your Brief Summary</div>
          <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;">
            {"".join(f'<span style="background:rgba(124,106,247,0.15);color:#7c6af7;border-radius:20px;padding:3px 12px;font-size:0.8rem;font-weight:600;">{c}</span>' for c in cats[:6])}
          </div>
          <div style="font-size:0.88rem;color:var(--text-secondary);font-style:italic;line-height:1.6;
                      border-left:3px solid var(--accent-purple);padding-left:12px;">
            "{morning_msg or 'Here\'s what happened in the world yesterday.'}"
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_back, col_activate = st.columns([1, 3])
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.onboard_step = 4
            st.rerun()
    with col_activate:
        if st.button("✅ Activate Daily Brief & Enter Flora OS", use_container_width=True):
            with get_db() as db:
                p = db.query(UserPreferences).filter_by(user_id=user.id).first()
                if p:
                    p.morning_email_active = True
            with get_db() as db:
                u = db.query(User).filter_by(id=user.id).first()
                if u:
                    u.is_onboarded = True
            st.session_state.onboard_step = 1
            st.session_state.pop("_onboard_greeting", None)
            toast_success(f"Daily brief activated! First email arrives tomorrow at {brief_time_display}.")
            st.switch_page("pages/dashboard.py")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    if st.button("Skip activation — enter Flora OS without daily email", use_container_width=True):
        with get_db() as db:
            u = db.query(User).filter_by(id=user.id).first()
            if u:
                u.is_onboarded = True
        st.session_state.onboard_step = 1
        st.switch_page("pages/dashboard.py")

st.markdown("</div>", unsafe_allow_html=True)
