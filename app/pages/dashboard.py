"""
Flora OS -- Dashboard
Home screen: greeting, headline, key stats, top stories, market snapshot, quick actions.
"""

import streamlit as st
from datetime import datetime, timezone

from app.auth.session import require_auth
from app.database import get_db
from app.models import DailyBrief, Article, EmailSummary, UserPreferences
from app.agents.orchestrator import get_or_generate_brief
from app.ui.theme import apply_theme
from app.ui.navbar import render_navbar
from app.ui.components import section_header, metric_card, article_card, loading_card, empty_state, labeled_divider
from app.utils.logger import get_logger

logger = get_logger("pages.dashboard")

apply_theme()
user = require_auth()
render_navbar(user, active_page="Dashboard")


@st.cache_data(ttl=300, show_spinner=False)
def _load_brief_cached(user_id: int, date: str):
    """Only return brief if it already exists â€” never blocks to generate."""
    with get_db() as db:
        existing = db.query(DailyBrief).filter(
            DailyBrief.user_id == user_id,
            DailyBrief.date == date,
        ).first()
        return existing.content if existing else None


def _generate_brief_now(user_id: int, date: str):
    """Generate brief synchronously â€” called only when user clicks Generate."""
    with get_db() as db:
        from app.models import User
        u = db.query(User).filter_by(id=user_id).first()
        if not u:
            return None
        return get_or_generate_brief(db, u)


@st.cache_data(ttl=60, show_spinner=False)
def _load_stats(user_id: int):
    with get_db() as db:
        article_count = db.query(Article).filter(Article.user_id == user_id).count()
        email_count = db.query(EmailSummary).filter(EmailSummary.user_id == user_id).count()
        brief_count = db.query(DailyBrief).filter(DailyBrief.user_id == user_id).count()
        prefs = db.query(UserPreferences).filter_by(user_id=user_id).first()
        return {
            "articles": article_count,
            "emails": email_count,
            "briefs": brief_count,
            "location": prefs.location if prefs else "",
        }


today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Load existing brief (non-blocking)
brief = _load_brief_cached(user.id, today_str)

# If no brief yet, attempt generation (with timeout guard)
if brief is None and st.session_state.get("_generating_brief"):
    try:
        with st.spinner("Flora is generating your brief… this takes ~30 seconds."):
            import threading, queue
            q = queue.Queue()
            def _run():
                try:
                    q.put(("ok", _generate_brief_now(user.id, today_str)))
                except Exception as exc:
                    q.put(("err", str(exc)))
            t = threading.Thread(target=_run, daemon=True)
            t.start()
            t.join(timeout=60)
            if not t.is_alive():
                result = q.get_nowait() if not q.empty() else ("err", "No result")
                if result[0] == "ok" and result[1]:
                    brief = result[1]
                    _load_brief_cached.clear()
                else:
                    st.warning(f"Brief generation failed: {result[1]}. Check your API keys in .env")
            else:
                st.warning("Brief generation timed out (>60s). Check your API keys in .env")
    except Exception as e:
        st.warning(f"Could not generate brief: {e}")
    finally:
        st.session_state.pop("_generating_brief", None)
    if brief:
        st.rerun()

stats = _load_stats(user.id)

# Header
first_name = user.name.split()[0] if user.name else "there"
greeting = brief.get("meta", {}).get("greeting", f"Good morning, {first_name}") if brief else f"Hello, {first_name}"
date_display = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
headline = brief.get("headline", "Your personalized brief is ready.") if brief else "Generating your brief..."

st.markdown(
    f"""
    <div style="margin-bottom:2rem;">
      <div style="font-size:0.8rem;color:var(--text-muted);text-transform:uppercase;
                  letter-spacing:0.1em;margin-bottom:6px;">{date_display}</div>
      <h1 class="flora-h1">{greeting}</h1>
      <p style="color:var(--text-secondary);margin-top:8px;font-size:1rem;">{headline}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Live weather via browser geolocation ─────────────────────────────────────
# Try to get GPS coords from the browser; fall back to saved city preference.
@st.cache_data(ttl=600, show_spinner=False)
def _weather_by_coords(lat: float, lon: float):
    from app.services.weather_service import get_weather_by_coords
    return get_weather_by_coords(lat, lon)

@st.cache_data(ttl=600, show_spinner=False)
def _weather_by_city(city: str):
    from app.services.weather_service import get_weather
    return get_weather(city) if city else None

def _get_live_weather(fallback_city: str):
    try:
        from streamlit_js_eval import get_geolocation
        loc = get_geolocation(key="_dash_geo")
        if loc and loc.get("coords"):
            lat = loc["coords"]["latitude"]
            lon = loc["coords"]["longitude"]
            return _weather_by_coords(round(lat, 3), round(lon, 3))
    except Exception:
        pass
    return _weather_by_city(fallback_city)

with get_db() as _wdb:
    _wprefs = _wdb.query(UserPreferences).filter_by(user_id=user.id).first()
    _fallback_city = (_wprefs.location or "") if _wprefs else ""

weather = _get_live_weather(_fallback_city)

if weather:
    st.markdown(
        f"""
        <div style="background:var(--bg-glass);border:1px solid var(--border);
                    border-radius:var(--radius-md);padding:0.75rem 1.25rem;
                    display:inline-flex;align-items:center;gap:1.5rem;margin-bottom:1.5rem;">
          <span style="font-size:1.5rem;">{weather.get("icon","")}</span>
          <div>
            <div style="font-weight:600;">{weather.get("city","")} &mdash; {weather.get("temp_c","")}&#176;C</div>
            <div style="font-size:0.8rem;color:var(--text-secondary);">
              {weather.get("description","")} &middot; Feels like {weather.get("feels_like","")}&#176;C &middot;
              {weather.get("humidity","")}% humidity &middot; {weather.get("wind_kph","")} km/h
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Weather strip (from brief, shown only if live weather unavailable)
if brief and not weather:
    _bw = brief.get("weather")
    if _bw:
        st.markdown(
            f"""
            <div style="background:var(--bg-glass);border:1px solid var(--border);
                        border-radius:var(--radius-md);padding:0.75rem 1.25rem;
                        display:inline-flex;align-items:center;gap:1.5rem;margin-bottom:1.5rem;">
              <span style="font-size:1.5rem;">{_bw.get("icon","")}</span>
              <div>
                <div style="font-weight:600;">{_bw.get("city","")} &mdash; {_bw.get("temp_c","")}&#176;C</div>
                <div style="font-size:0.8rem;color:var(--text-secondary);">
                  {_bw.get("description","")} &middot; Feels like {_bw.get("feels_like","")}&#176;C &middot;
                  {_bw.get("humidity","")}% humidity &middot; {_bw.get("wind_kph","")} km/h
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# Stats row — only show real numbers when brief exists
if brief:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        article_count = len(brief.get("top_stories", []))
        metric_card("Articles Today", str(article_count))
    with col2:
        email_count = brief.get("gmail", {}).get("total", 0)
        urgent = brief.get("gmail", {}).get("urgent_count", 0)
        metric_card("Emails", str(email_count), f"{urgent} urgent" if urgent else "", color="var(--accent-blue)")
    with col3:
        job_count = brief.get("jobs", {}).get("total_found", 0)
        metric_card("Job Matches", str(job_count), color="var(--accent-green)")
        if st.button(f"View jobs →", key="dash_jobs_stat", use_container_width=True):
            st.switch_page("pages/job_board.py")
    with col4:
        mover = brief.get("market", {}).get("top_mover")
        if mover:
            sign = "+" if mover["change_pct"] >= 0 else ""
            metric_card("Top Mover", mover["name"], f"{sign}{mover['change_pct']:.1f}%",
                        color="var(--accent-green)" if mover["change_pct"] >= 0 else "var(--accent-red)")
        else:
            metric_card("Top Mover", "--")
else:
    # Welcome banner for new users — no zeros, just a helpful prompt
    st.markdown(
        f"""
        <div class="flora-card" style="padding:2rem;margin-bottom:1.5rem;
             background:linear-gradient(135deg,rgba(124,106,247,0.12),rgba(56,189,248,0.08));
             border-color:rgba(124,106,247,0.3);">
          <div style="display:flex;align-items:center;gap:1.5rem;">
            <div style="font-size:3rem;">🌿</div>
            <div>
              <div style="font-size:1.2rem;font-weight:700;color:#f0f0ff;margin-bottom:6px;">
                Welcome to Flora OS, {first_name}!
              </div>
              <div style="font-size:0.88rem;color:#8888aa;line-height:1.6;">
                Your dashboard will populate once your first morning brief is generated.<br>
                Flora delivers a personalised brief to your inbox daily — or you can generate one now.
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

# Main grid
col_news, col_market = st.columns([3, 2], gap="large")

with col_news:
    section_header("Top Stories", "Highest-importance articles today", badge="AI Ranked", badge_color="purple")

    if not brief:
        st.markdown(
            """
            <div class="flora-card" style="text-align:center;padding:2.5rem;">
              <div style="font-size:2.5rem;margin-bottom:1rem;">&#127807;</div>
              <div style="font-size:1.1rem;font-weight:700;margin-bottom:0.5rem;">Your morning brief isn't ready yet</div>
              <div style="font-size:0.875rem;color:var(--text-secondary);margin-bottom:1.5rem;">
                Flora generates your personalized brief daily at 5:00 AM UTC.
                You can generate it now manually (requires API keys in .env).
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Generate Brief Now", use_container_width=True):
            st.session_state["_generating_brief"] = True
            st.rerun()
    else:
        top = brief.get("top_stories", [])
        if not top:
            empty_state("&#128240;", "No articles yet", "Check back after your brief is generated.")
        else:
            for art in top:
                article_card(
                    title=art["title"], summary=art["summary"], source=art["source"],
                    category=art["category"], importance=art["importance_score"],
                    read_time=art["read_time_minutes"], url=art["url"],
                    article_id=art.get("id"),
                    key_prefix="dash_",
                )
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if brief:
        if st.button("Read Full Morning Brief", use_container_width=True):
            st.switch_page("pages/morning_brief.py")

with col_market:
    section_header("Market Snapshot", "Your watchlist")

    if brief:
        market_data = brief.get("market", {})
        stocks = market_data.get("stocks", [])
        cryptos = market_data.get("crypto", [])

        if stocks:
            st.markdown('<div class="flora-label" style="margin-bottom:8px;">STOCKS</div>', unsafe_allow_html=True)
            for s in stocks[:5]:
                pct = s.get("change_pct", 0)
                color = "var(--accent-green)" if pct >= 0 else "var(--accent-red)"
                arrow = "&#9650;" if pct >= 0 else "&#9660;"
                st.markdown(
                    f"""
                    <div class="flora-card" style="padding:0.75rem 1rem;margin-bottom:6px;">
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                          <span style="font-weight:700;">{s["ticker"]}</span>
                          <span style="font-size:0.8rem;color:var(--text-secondary);margin-left:8px;">{s.get("name","")[:20]}</span>
                        </div>
                        <div style="text-align:right;">
                          <div style="font-weight:600;">${s["price"]:,.2f}</div>
                          <div style="font-size:0.8rem;color:{color};">{arrow} {abs(pct):.2f}%</div>
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if cryptos:
            st.markdown('<div class="flora-label" style="margin:12px 0 8px;">CRYPTO</div>', unsafe_allow_html=True)
            for c in cryptos[:4]:
                chg = c.get("change_24h", 0)
                color = "var(--accent-green)" if chg >= 0 else "var(--accent-red)"
                arrow = "&#9650;" if chg >= 0 else "&#9660;"
                st.markdown(
                    f"""
                    <div class="flora-card" style="padding:0.75rem 1rem;margin-bottom:6px;">
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-weight:700;">{c["name"].title()}</span>
                        <div style="text-align:right;">
                          <div style="font-weight:600;">${c["price"]:,.2f}</div>
                          <div style="font-size:0.8rem;color:{color};">{arrow} {abs(chg):.2f}%</div>
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        mkt_summary = market_data.get("summary", "")
        if mkt_summary:
            st.markdown(
                f'<div style="background:var(--bg-glass);border:1px solid var(--border);border-radius:var(--radius-md);'
                f'padding:0.875rem;margin-top:0.75rem;font-size:0.82rem;color:var(--text-secondary);line-height:1.6;">'
                f'&#129302; {mkt_summary}</div>',
                unsafe_allow_html=True,
            )
        if st.button("Full Market View", use_container_width=True):
            st.switch_page("pages/market.py")
    else:
        empty_state("&#128200;", "Market data loading...")

# Bottom row
st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
labeled_divider("Quick Access")

col_email, col_jobs, col_learn = st.columns(3, gap="large")

with col_email:
    section_header("Emails", "")
    # Check Gmail connection live — don't rely on stale brief cache
    from app.models import GmailConnection
    with get_db() as _db:
        _gc = _db.query(GmailConnection).filter_by(user_id=user.id, is_active=True).first()
        _gmail_connected = _gc is not None

    if _gmail_connected:
        from app.models import EmailSummary as _ES
        from datetime import timedelta
        with get_db() as _db2:
            _recent = _db2.query(_ES).filter(
                _ES.user_id == user.id,
            ).order_by(_ES.received_at.desc()).limit(5).all()
            _email_count = _db2.query(_ES).filter_by(user_id=user.id).count()

        if _recent:
            st.markdown(
                f"""
                <div class="flora-card">
                  <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:10px;">
                    {_email_count} job emails processed
                  </div>
                  {''.join(
                    f'<div style="font-size:0.82rem;color:var(--text-primary);padding:4px 0;'
                    f'border-bottom:1px solid rgba(255,255,255,0.05);">'
                    f'<span style="color:var(--accent-purple2);">●</span> {e.subject[:45]}{"…" if len(e.subject)>45 else ""}'
                    f'</div>'
                    for e in _recent
                  )}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            empty_state("&#9993;", "No job emails yet", "Sync in Email Hub")
    else:
        empty_state("&#9993;", "Gmail not connected", "Connect in Settings")
    if st.button("Open Email Hub", use_container_width=True):
        st.switch_page("pages/email_hub.py")

with col_jobs:
    section_header("Top Jobs", "")
    if brief:
        jobs_data = brief.get("jobs", {})
        top_jobs = jobs_data.get("top_picks", [])
        if top_jobs:
            for j in top_jobs[:3]:
                score_color = "var(--accent-green)" if j["fit_score"] >= 7 else "var(--accent-amber)"
                st.markdown(
                    f"""
                    <div class="flora-card" style="margin-bottom:6px;">
                      <div style="font-weight:600;font-size:0.875rem;">{j["title"]}</div>
                      <div style="font-size:0.78rem;color:var(--text-secondary);">{j["company"]} &middot; {j["location"]}</div>
                      <div style="font-size:0.75rem;color:{score_color};margin-top:4px;">
                        &#11088; {j["fit_score"]:.1f}/10 &mdash; {j.get("fit_reason","")}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            empty_state("&#128188;", "Set job preferences", "Configure in Settings")
    if st.button("Full Job Board", use_container_width=True):
        st.switch_page("pages/job_board.py")

with col_learn:
    section_header("Today's Pick", "")
    if brief:
        learning = brief.get("learning", {})
        rec = learning.get("ai_recommendation", {})
        quote = learning.get("daily_quote", {})

        if rec:
            st.markdown(
                f"""
                <div class="flora-card" style="margin-bottom:8px;">
                  <div style="font-size:0.7rem;color:var(--accent-purple2);font-weight:600;
                              text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">
                    Flora Recommends
                  </div>
                  <div style="font-weight:600;font-size:0.9rem;">{rec.get("title","")}</div>
                  <div style="font-size:0.8rem;color:var(--text-secondary);margin-top:4px;line-height:1.5;">
                    {rec.get("description","")[:120]}...
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if quote:
            st.markdown(
                f"""
                <div style="border-left:3px solid var(--accent-purple);padding:0.75rem 1rem;
                            background:var(--bg-glass);border-radius:0 var(--radius-sm) var(--radius-sm) 0;">
                  <div style="font-style:italic;color:var(--text-secondary);font-size:0.82rem;">"{quote.get("text","")}"</div>
                  <div style="font-size:0.72rem;color:var(--text-muted);margin-top:4px;">&mdash; {quote.get("author","")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        empty_state("&#127891;", "Learning content loading...")

