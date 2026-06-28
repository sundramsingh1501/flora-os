"""
Flora OS -- Morning Brief Page
The full interactive newspaper. All sections in one beautiful layout.
"""

import streamlit as st
from datetime import datetime, timezone

from app.auth.session import require_auth
from app.database import get_db
from app.agents.orchestrator import get_or_generate_brief
from app.ui.theme import apply_theme
from app.ui.navbar import render_navbar
from app.ui.components import section_header, article_card, labeled_divider, loading_card, empty_state
from app.utils.logger import get_logger

logger = get_logger("pages.morning_brief")

apply_theme()
user = require_auth()
render_navbar(user, active_page="Morning Brief")

from app.config import settings as app_settings

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
date_display = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")


@st.cache_data(ttl=300, show_spinner=False)
def _get_brief(user_id: int, date: str):
    import threading, queue
    q: queue.Queue = queue.Queue()

    def _run():
        try:
            with get_db() as db:
                from app.models import User
                u = db.query(User).filter_by(id=user_id).first()
                result = get_or_generate_brief(db, u) if u else None
            q.put(("ok", result))
        except Exception as exc:
            q.put(("err", str(exc)))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=90)
    if t.is_alive():
        return None  # timed out
    item = q.get_nowait() if not q.empty() else ("err", "no result")
    return item[1] if item[0] == "ok" else None

st.markdown(
    f"""
    <div style="margin-bottom:2rem;padding-bottom:1.5rem;border-bottom:1px solid var(--border);">
      <div style="font-size:0.75rem;color:var(--text-muted);letter-spacing:0.15em;text-transform:uppercase;margin-bottom:8px;">
        {date_display}
      </div>
      <h1 style="font-size:2.5rem;font-weight:800;letter-spacing:-0.04em;line-height:1.1;margin-bottom:0.5rem;">
        Morning Brief
      </h1>
      <p style="color:var(--text-secondary);font-size:1rem;">
        Your personalized AI-curated newspaper &middot; Powered by Flora
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

col_hdr, col_btn = st.columns([5, 1])
with col_btn:
    if st.button("Refresh", help="Regenerate today's brief"):
        st.cache_data.clear()
        st.rerun()

if not app_settings.gemini_api_key:
    st.warning(
        "**Gemini API key not configured.**  \n"
        "Flora needs a Gemini key to generate your morning brief.  \n"
        "1. Get a free key at [aistudio.google.com](https://aistudio.google.com/app/apikey)  \n"
        "2. Add it to your `.env` file: `GEMINI_API_KEY=your_key_here`  \n"
        "3. Restart the app"
    )
    st.stop()

with st.spinner("Flora is compiling your brief..."):
    brief = _get_brief(user.id, today)

if not brief:
    st.warning(
        "Brief generation timed out or failed. This usually means:  \n"
        "- Gemini API is slow or rate-limited — try refreshing in a minute  \n"
        "- Check your Gemini API key in `.env`"
    )
    if st.button("Try Again"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

# Headline banner
headline = brief.get("headline", "")
if headline:
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,rgba(124,106,247,0.1),rgba(56,189,248,0.1));
                    border:1px solid rgba(124,106,247,0.2);border-radius:var(--radius-lg);
                    padding:1.5rem 2rem;margin-bottom:2rem;text-align:center;">
          <div style="font-size:0.7rem;color:var(--accent-purple2);letter-spacing:0.15em;
                      text-transform:uppercase;margin-bottom:8px;">TODAY'S HEADLINE</div>
          <div style="font-size:1.25rem;font-weight:700;line-height:1.4;">{headline}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

tabs = st.tabs([
    "Top Stories", "AI & Tech", "World", "Research",
    "Markets", "Jobs", "Email", "Learning"
])

news_by_cat = brief.get("news_by_category", {})
top_stories = brief.get("top_stories", [])


def _show_articles(articles: list, prefix: str = "") -> None:
    if not articles:
        empty_state("&#128240;", "No articles in this section")
        return
    for i, art in enumerate(articles):
        article_card(
            title=art["title"], summary=art["summary"], source=art["source"],
            category=art["category"], importance=art["importance_score"],
            read_time=art["read_time_minutes"], url=art["url"], article_id=art.get("id"),
            key_prefix=f"{prefix}_{i}_",
        )
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)


# Tab 1: Top Stories
with tabs[0]:
    section_header("Top Stories", "Highest importance articles across all categories", badge="AI Ranked")
    _show_articles(top_stories, prefix="t0a")
    labeled_divider("All Articles")
    all_articles = []
    for cat_articles in news_by_cat.values():
        all_articles.extend(cat_articles)
    all_articles.sort(key=lambda x: x.get("importance_score", 0), reverse=True)
    _show_articles(all_articles[3:15], prefix="t0b")

# Tab 2: AI & Tech
with tabs[1]:
    ai_cats = ["AI", "AI & Machine Learning", "GenAI", "GenAI & LLMs", "Technology"]
    ai_articles = []
    for cat in ai_cats:
        ai_articles.extend(news_by_cat.get(cat, []))
    section_header("AI & Technology", f"{len(ai_articles)} articles", badge="Live Feed")

    research = brief.get("research", {})
    tool = research.get("ai_tool_of_day", {})
    if tool:
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,rgba(124,106,247,0.08),rgba(56,189,248,0.08));
                        border:1px solid rgba(124,106,247,0.2);border-radius:var(--radius-lg);
                        padding:1.25rem 1.5rem;margin-bottom:1.5rem;">
              <div style="font-size:0.7rem;color:var(--accent-purple2);letter-spacing:0.12em;
                          text-transform:uppercase;margin-bottom:8px;">AI TOOL OF THE DAY</div>
              <div style="font-size:1.1rem;font-weight:700;">{tool.get("name","")}</div>
              <div style="font-size:0.875rem;color:var(--text-secondary);margin-top:4px;">{tool.get("tagline","")}</div>
              <div style="font-size:0.82rem;color:var(--text-secondary);margin-top:8px;line-height:1.6;">{tool.get("why","")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    _show_articles(ai_articles, prefix="t1")

# Tab 3: World News
with tabs[2]:
    world_cats = ["World News", "Indian News", "Business", "Science"]
    world_articles = []
    for cat in world_cats:
        world_articles.extend(news_by_cat.get(cat, []))
    section_header("World & India", f"{len(world_articles)} articles")
    _show_articles(world_articles, prefix="t2")

# Tab 4: Research & GitHub
with tabs[3]:
    research = brief.get("research", {})
    papers = research.get("papers", [])
    repos = research.get("trending_repos", [])

    col_papers, col_repos = st.columns(2, gap="large")

    with col_papers:
        section_header("Research Papers", f"{len(papers)} from ArXiv")
        _show_articles(papers, prefix="t3p")

    with col_repos:
        section_header("GitHub Trending", f"{len(repos)} repos today")
        if not repos:
            empty_state("&#128187;", "Could not fetch GitHub trending")
        else:
            for repo in repos:
                lang_badge = f'<span class="badge badge-blue">{repo["language"]}</span>' if repo.get("language") else ""
                st.markdown(
                    f"""
                    <div class="flora-card" style="margin-bottom:8px;">
                      <div style="font-weight:600;font-size:0.9rem;">
                        {repo["owner"]} / <span style="color:var(--accent-purple2);">{repo["name"]}</span>
                      </div>
                      <div style="font-size:0.8rem;color:var(--text-secondary);margin-top:4px;line-height:1.4;">
                        {repo.get("description","")[:100]}
                      </div>
                      <div style="margin-top:8px;display:flex;align-items:center;gap:10px;">
                        {lang_badge}
                        <span style="font-size:0.75rem;color:var(--text-muted);">&#11088; {repo.get("stars","")}</span>
                        <span style="font-size:0.75rem;color:var(--accent-green);">{repo.get("stars_today","")}</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.link_button("View", repo["url"])

# Tab 5: Markets
with tabs[4]:
    market = brief.get("market", {})
    section_header("Markets", "Your watchlist", badge="Live")

    mkt_summary = market.get("summary", "")
    if mkt_summary:
        st.markdown(
            f'<div style="background:var(--bg-glass);border:1px solid var(--border);border-radius:var(--radius-md);'
            f'padding:1rem 1.25rem;margin-bottom:1.5rem;font-size:0.875rem;color:var(--text-secondary);line-height:1.6;">'
            f'&#129302; <strong>Flora\'s Market Briefing:</strong> {mkt_summary}</div>',
            unsafe_allow_html=True,
        )

    col_s, col_c = st.columns(2, gap="large")
    with col_s:
        st.markdown('<div class="flora-label" style="margin-bottom:12px;">STOCKS</div>', unsafe_allow_html=True)
        for s in market.get("stocks", []):
            pct = s.get("change_pct", 0)
            color = "var(--accent-green)" if pct >= 0 else "var(--accent-red)"
            arrow = "&#9650;" if pct >= 0 else "&#9660;"
            st.markdown(
                f"""
                <div class="flora-card" style="margin-bottom:8px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                      <div style="font-size:1.1rem;font-weight:700;">{s["ticker"]}</div>
                      <div style="font-size:0.78rem;color:var(--text-secondary);">{s.get("name","")}</div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:1.1rem;font-weight:700;">${s["price"]:,.2f}</div>
                      <div style="font-size:0.85rem;color:{color};">{arrow} {abs(pct):.2f}%</div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_c:
        st.markdown('<div class="flora-label" style="margin-bottom:12px;">CRYPTO</div>', unsafe_allow_html=True)
        for c in market.get("crypto", []):
            chg = c.get("change_24h", 0)
            color = "var(--accent-green)" if chg >= 0 else "var(--accent-red)"
            arrow = "&#9650;" if chg >= 0 else "&#9660;"
            st.markdown(
                f"""
                <div class="flora-card" style="margin-bottom:8px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                      <div style="font-size:1.1rem;font-weight:700;">{c["name"].title()}</div>
                      <div style="font-size:0.78rem;color:var(--text-secondary);">24h change</div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:1.1rem;font-weight:700;">${c["price"]:,.2f}</div>
                      <div style="font-size:0.85rem;color:{color};">{arrow} {abs(chg):.2f}%</div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    if st.button("Full Market Dashboard", use_container_width=True):
        st.switch_page("pages/market.py")

# Tab 6: Jobs
with tabs[5]:
    jobs_data = brief.get("jobs", {})
    top_jobs = jobs_data.get("top_picks", [])
    section_header("Job Matches", f"{jobs_data.get('total_found', 0)} openings found", badge="Personalized")

    if not top_jobs:
        empty_state("&#128188;", "No job matches yet", "Add job roles in Settings.")
    else:
        for j in top_jobs:
            fit = j["fit_score"]
            fit_color = "var(--accent-green)" if fit >= 7 else "var(--accent-amber)" if fit >= 5 else "var(--accent-red)"
            tags_html = "".join(
                f'<span class="badge badge-purple" style="margin-right:4px;">{t}</span>'
                for t in j.get("match_tags", [])[:3]
            )
            st.markdown(
                f"""
                <div class="flora-card" style="margin-bottom:10px;">
                  <div style="font-weight:700;font-size:1rem;">{j["title"]}</div>
                  <div style="font-size:0.85rem;color:var(--text-secondary);margin-top:2px;">
                    {j["company"]} &middot; {j["location"]} &middot; via {j["source"]}
                  </div>
                  <div style="margin-top:8px;">{tags_html}</div>
                  <div style="font-size:0.8rem;color:{fit_color};margin-top:6px;">
                    &#11088; {fit:.1f}/10 &mdash; {j.get("fit_reason","")}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.link_button("Apply", j["url"])
    if st.button("Full Job Board", use_container_width=True):
        st.switch_page("pages/job_board.py")

# Tab 7: Email
with tabs[6]:
    gmail = brief.get("gmail", {})
    section_header("Email Summary", "Last 24 hours")
    if not gmail.get("connected"):
        st.info("Gmail not connected. Connect in Settings to see email summaries.")
        if st.button("Connect Gmail"):
            st.switch_page("pages/settings.py")
    else:
        st.markdown(
            f'<div style="background:var(--bg-glass);border:1px solid var(--border);border-radius:var(--radius-md);'
            f'padding:1rem 1.25rem;margin-bottom:1.5rem;font-size:0.875rem;color:var(--text-secondary);line-height:1.6;">'
            f'&#129302; {gmail.get("summary","")}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Open Full Email Hub"):
            st.switch_page("pages/email_hub.py")

# Tab 8: Learning
with tabs[7]:
    learning = brief.get("learning", {})
    resource = learning.get("resource", {})
    iq = learning.get("interview_question", {})
    quote = learning.get("daily_quote", {})
    rec = learning.get("ai_recommendation", {})

    col_l, col_r = st.columns(2, gap="large")

    with col_l:
        section_header("Learning Resource")
        if resource:
            st.markdown(
                f"""
                <div class="flora-card">
                  <div style="font-size:0.7rem;color:var(--accent-blue);text-transform:uppercase;
                              letter-spacing:0.1em;margin-bottom:8px;">
                    {resource.get("type","")} &middot; {resource.get("duration","")}
                  </div>
                  <div style="font-weight:700;font-size:1rem;margin-bottom:6px;">{resource.get("title","")}</div>
                  <div style="font-size:0.8rem;color:var(--text-secondary);">{resource.get("source","")}</div>
                  <div style="font-size:0.875rem;color:var(--text-secondary);margin-top:10px;line-height:1.6;">
                    {resource.get("why","")}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if resource.get("url"):
                st.link_button("Open Resource", resource["url"], use_container_width=True)

        if rec:
            st.markdown(
                f"""
                <div class="flora-card" style="margin-top:1rem;border-color:rgba(124,106,247,0.3);">
                  <div style="font-size:0.7rem;color:var(--accent-purple2);text-transform:uppercase;
                              letter-spacing:0.1em;margin-bottom:8px;">Flora Recommends</div>
                  <div style="font-weight:700;font-size:0.95rem;margin-bottom:6px;">{rec.get("title","")}</div>
                  <div style="font-size:0.875rem;color:var(--text-secondary);line-height:1.6;">{rec.get("description","")}</div>
                  <div style="font-size:0.82rem;color:var(--accent-green);margin-top:10px;">
                    Action: {rec.get("action","")}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_r:
        section_header("Interview Question")
        if iq:
            diff_colors = {"Easy": "green", "Medium": "amber", "Hard": "red"}
            diff_color = diff_colors.get(iq.get("difficulty", "Medium"), "amber")
            st.markdown(
                f"""
                <div class="flora-card" style="margin-bottom:1rem;">
                  <div style="display:flex;gap:8px;margin-bottom:10px;">
                    <span class="badge badge-{diff_color}">{iq.get("difficulty","")}</span>
                    <span class="badge badge-blue">{iq.get("topic","")}</span>
                  </div>
                  <div style="font-weight:600;font-size:0.95rem;line-height:1.5;margin-bottom:10px;">
                    {iq.get("question","")}
                  </div>
                  <div style="font-size:0.8rem;color:var(--accent-amber);margin-bottom:8px;">
                    Hint: {iq.get("hint","")}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("Show Answer"):
                st.markdown(f'<div style="font-size:0.875rem;line-height:1.7;">{iq.get("answer","")}</div>', unsafe_allow_html=True)

        section_header("Daily Quote")
        if quote:
            st.markdown(
                f"""
                <div style="border-left:3px solid var(--accent-purple);padding:1rem 1.25rem;
                            background:var(--bg-glass);border-radius:0 var(--radius-md) var(--radius-md) 0;">
                  <div style="font-size:1rem;font-style:italic;line-height:1.6;">&ldquo;{quote.get("text","")}&rdquo;</div>
                  <div style="font-size:0.82rem;color:var(--text-muted);margin-top:8px;">&mdash; {quote.get("author","")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

