"""
Flora OS -- Job Board
Personalized job listings with AI fit scoring, filters, and search.
"""

import re
import html as _html
import streamlit as st

from app.auth.session import require_auth
from app.database import get_db
from app.models import UserPreferences
from app.ui.theme import apply_theme
from app.ui.navbar import render_navbar
from app.ui.components import section_header, empty_state
from app.utils.logger import get_logger

logger = get_logger("pages.job_board")

apply_theme()
user = require_auth()
render_navbar(user, active_page="Job Board")

from app.config import settings as app_settings


@st.cache_data(ttl=1800, show_spinner=False)
def _load_jobs(user_id: int):
    import threading, queue
    with get_db() as db:
        prefs = db.query(UserPreferences).filter_by(user_id=user_id).first()
        if not prefs:
            return [], {}
        p = {
            "roles": prefs.job_roles or [],
            "locations": prefs.job_locations or [],
            "tech": prefs.tech_stack or [],
        }
    if not p["roles"]:
        return [], p

    q: queue.Queue = queue.Queue()

    def _run():
        try:
            from app.agents.job_agent import run as job_run
            result = job_run(user_id, {
                "job_roles": p["roles"],
                "job_locations": p["locations"],
                "tech_stack": p["tech"],
            })
            q.put(("ok", result))
        except Exception as exc:
            q.put(("err", str(exc)))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=60)
    if t.is_alive() or q.empty():
        return [], p
    item = q.get_nowait()
    return (item[1] if item[0] == "ok" else []), p


with st.spinner("Fetching personalized jobs..."):
    jobs, prefs_info = _load_jobs(user.id)

st.markdown(
    f"""
    <h1 class="flora-h1" style="margin-bottom:0.5rem;">Job Board</h1>
    <p style="color:var(--text-secondary);margin-bottom:1.5rem;">
      {len(jobs)} personalized openings &middot; AI-scored for your fit
    </p>
    """,
    unsafe_allow_html=True,
)

if not prefs_info.get("roles"):
    st.markdown(
        """
        <div class="flora-card" style="text-align:center;padding:2.5rem;">
          <div style="font-size:2.5rem;margin-bottom:1rem;">&#128188;</div>
          <div style="font-size:1.1rem;font-weight:700;margin-bottom:0.5rem;">Set your job preferences</div>
          <div style="font-size:0.875rem;color:var(--text-secondary);max-width:380px;margin:0 auto 1.5rem;">
            Tell Flora what roles and tech stack you are targeting to get personalized job recommendations.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Set Preferences in Settings"):
        st.switch_page("pages/settings.py")
    st.stop()

if not jobs:
    empty_state("&#128269;", "No jobs found", "Try broadening your roles or locations in Settings.")
    st.stop()

# Filters
col1, col2, col3, col4 = st.columns(4)
with col1:
    min_fit = st.slider("Min Fit Score", 1.0, 10.0, 5.0, 0.5)
with col2:
    sources = ["All"] + list({j.get("source", "") for j in jobs})
    source_filter = st.selectbox("Source", sources)
with col3:
    locations_avail = ["All"] + list({j.get("location", "") for j in jobs})
    loc_filter = st.selectbox("Location", locations_avail)
with col4:
    search_q = st.text_input("Search", placeholder="Search jobs...", label_visibility="collapsed")

filtered = [j for j in jobs if j.get("fit_score", 0) >= min_fit]
if source_filter != "All":
    filtered = [j for j in filtered if j.get("source") == source_filter]
if loc_filter != "All":
    filtered = [j for j in filtered if j.get("location") == loc_filter]
if search_q:
    q = search_q.lower()
    filtered = [j for j in filtered if q in j.get("title","").lower() or q in j.get("company","").lower()]

st.markdown(f'<div style="font-size:0.8rem;color:var(--text-muted);margin-bottom:1.5rem;">Showing {len(filtered)} of {len(jobs)} jobs</div>', unsafe_allow_html=True)

def _strip_html(text: str) -> str:
    """Strip all HTML tags and decode entities to plain text."""
    text = re.sub(r"<[^>]+>", " ", text)   # remove tags
    text = _html.unescape(text)              # decode &amp; &lt; &nbsp; etc.
    text = re.sub(r"\s+", " ", text).strip()
    return text


if not filtered:
    empty_state("&#128269;", "No jobs match your filters", "Try lowering the fit score threshold.")
else:
    for j in filtered:
        fit       = j.get("fit_score", 5.0)
        try:
            fit = float(fit)
        except (TypeError, ValueError):
            fit = 5.0

        fit_color  = "#4ade80" if fit >= 7 else "#fbbf24" if fit >= 5 else "#f87171"
        title      = str(j.get("title", "") or "")
        company    = str(j.get("company", "") or "")
        location   = str(j.get("location", "") or "")
        source     = str(j.get("source", "") or "")
        fit_reason = str(j.get("fit_reason", "") or "")
        tags       = j.get("match_tags", []) or []
        desc       = _strip_html(str(j.get("description", "") or ""))
        desc_short = desc[:300] + ("…" if len(desc) > 300 else "")

        salary_parts = []
        try:
            s_min = j.get("salary_min")
            s_max = j.get("salary_max")
            if s_min:
                salary_parts.append(f"💰 ${int(float(s_min)):,}")
            if s_max:
                salary_parts.append(f"${int(float(s_max)):,}")
        except (TypeError, ValueError):
            pass
        salary_str = "–".join(salary_parts) if salary_parts else ""

        with st.container():
            st.markdown(
                '<div style="border:1px solid rgba(255,255,255,0.08);border-radius:12px;'
                'padding:18px 20px;margin-bottom:12px;background:#12121e;">',
                unsafe_allow_html=True,
            )

            # Title row + fit score badge
            col_main, col_score = st.columns([5, 1])
            with col_main:
                st.markdown(f"**{title}**")
                meta = f"🏢 {company}"
                if location:
                    meta += f"  ·  📍 {location}"
                meta += f"  ·  via {source}"
                if salary_str:
                    meta += f"  ·  {salary_str}"
                st.caption(meta)

            with col_score:
                st.markdown(
                    f'<div style="text-align:center;padding:8px 0;">'
                    f'<div style="font-size:1.8rem;font-weight:800;color:{fit_color};line-height:1;">{fit:.0f}</div>'
                    f'<div style="font-size:0.6rem;color:#55556a;text-transform:uppercase;letter-spacing:0.1em;">FIT</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Description
            if desc_short:
                st.caption(desc_short)

            # Tags
            if tags:
                tag_row = "  ".join(f"`{t}`" for t in tags[:5])
                st.markdown(tag_row)

            # Fit reason
            if fit_reason:
                st.markdown(
                    f'<div style="font-size:0.8rem;color:{fit_color};margin-top:4px;">⭐ {fit:.1f}/10 — {fit_reason}</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)

            job_url = j.get("url", "")
            if job_url and job_url != "#":
                st.link_button("Apply →", job_url)
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

