"""
Flora OS — Reusable UI Components
All components return or render HTML/Streamlit widgets.
"""

from typing import Optional
import streamlit as st


# ---------------------------------------------------------------------------
# Logo & Branding
# ---------------------------------------------------------------------------

def render_logo(size: str = "md") -> None:
    sizes = {"sm": "1.4rem", "md": "1.8rem", "lg": "2.5rem"}
    font_size = sizes.get(size, "1.8rem")
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;">
          <span style="font-size:{font_size};font-weight:800;
                       background:linear-gradient(135deg,#7c6af7,#38bdf8);
                       -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                       background-clip:text;letter-spacing:-0.03em;">
            🌿 Flora OS
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Section headers
# ---------------------------------------------------------------------------

def section_header(title: str, subtitle: str = "", badge: str = "", badge_color: str = "purple") -> None:
    badge_html = f'<span class="badge badge-{badge_color}" style="margin-left:12px;">{badge}</span>' if badge else ""
    sub_html = f'<p style="color:var(--text-secondary);font-size:0.875rem;margin-top:4px;">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div style="margin-bottom:1.5rem;">
          <h2 class="flora-h2">{title}{badge_html}</h2>
          {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Stat / metric card
# ---------------------------------------------------------------------------

def metric_card(label: str, value: str, delta: str = "", color: str = "var(--accent-purple2)") -> None:
    delta_html = ""
    if delta:
        arrow = "↑" if not delta.startswith("-") else "↓"
        clr = "var(--accent-green)" if not delta.startswith("-") else "var(--accent-red)"
        delta_html = f'<div style="font-size:0.8rem;color:{clr};margin-top:4px;">{arrow} {delta}</div>'

    st.markdown(
        f"""
        <div class="flora-metric">
          <div class="value" style="color:{color};">{value}</div>
          <div class="label">{label}</div>
          {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Article card (for news feed)
# ---------------------------------------------------------------------------

def article_card(
    title: str,
    summary: str,
    source: str,
    category: str,
    importance: float,
    read_time: int,
    url: str,
    is_bookmarked: bool = False,
    article_id: Optional[int] = None,
    key_prefix: str = "",
) -> bool:
    """Render an article card. Returns True if 'Read More' was clicked."""
    importance_color = (
        "var(--accent-red)" if importance >= 8
        else "var(--accent-amber)" if importance >= 6
        else "var(--accent-green)"
    )
    category_colors = {
        "AI": "purple", "Technology": "blue", "World News": "amber",
        "Indian News": "green", "Market": "green", "Crypto": "amber",
        "Jobs": "pink", "Research": "blue", "GitHub": "purple",
        "Gmail": "blue", "Weather": "blue", "Learning": "green",
    }
    badge_color = category_colors.get(category, "purple")

    bookmark_icon = "🔖" if is_bookmarked else "☆"

    st.markdown(
        f"""
        <div class="article-card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div style="flex:1;">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                <span class="importance-dot" style="background:{importance_color};"></span>
                <span class="badge badge-{badge_color}">{category}</span>
                <span style="font-size:0.75rem;color:var(--text-muted);">{read_time} min read</span>
              </div>
              <div class="article-title">{title}</div>
              <div class="article-summary">{summary}</div>
              <div class="article-meta" style="margin-top:8px;">
                📰 {source} &nbsp;·&nbsp; ⭐ {importance:.1f}/10
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _uid = f"{key_prefix}{article_id}" if article_id else f"{key_prefix}{hash(title)}"
    col1, col2 = st.columns([3, 1])
    with col1:
        st.link_button("Read More →", url, use_container_width=False)
    with col2:
        st.button(bookmark_icon, key=f"bm_{_uid}", help="Bookmark")

    return False


# ---------------------------------------------------------------------------
# Email summary card
# ---------------------------------------------------------------------------

def email_card(
    subject: str,
    sender: str,
    summary: str,
    category: str,
    importance: str,
    action_items: list,
    has_draft: bool = False,
    email_id: Optional[int] = None,
) -> None:
    importance_colors = {
        "urgent": "var(--accent-red)",
        "normal": "var(--accent-purple2)",
        "low": "var(--text-muted)",
    }
    imp_color = importance_colors.get(importance, "var(--accent-purple2)")
    actions_html = "".join(
        f'<li style="font-size:0.82rem;color:var(--text-secondary);">{a}</li>'
        for a in action_items[:3]
    ) if action_items else ""

    st.markdown(
        f"""
        <div class="flora-card" style="margin-bottom:0.75rem;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div style="font-weight:600;font-size:0.95rem;">{subject}</div>
              <div style="font-size:0.8rem;color:var(--text-secondary);margin-top:2px;">From: {sender}</div>
            </div>
            <span class="badge badge-{'red' if importance=='urgent' else 'purple'}">{importance}</span>
          </div>
          <div style="font-size:0.875rem;color:var(--text-secondary);margin-top:10px;line-height:1.5;">
            {summary}
          </div>
          {f'<ul style="margin-top:8px;padding-left:16px;">{actions_html}</ul>' if actions_html else ''}
          {'<div style="font-size:0.78rem;color:var(--accent-green);margin-top:8px;">✍️ Reply draft ready</div>' if has_draft else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Loading / empty states
# ---------------------------------------------------------------------------

def loading_card(message: str = "Flora is thinking...") -> None:
    st.markdown(
        f"""
        <div class="flora-card" style="text-align:center;padding:2.5rem;">
          <div style="font-size:2rem;margin-bottom:1rem;">🌿</div>
          <div style="font-weight:600;color:var(--text-primary);">{message}</div>
          <div style="font-size:0.85rem;color:var(--text-secondary);margin-top:6px;">
            Gathering insights from across the internet...
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(icon: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div style="text-align:center;padding:3rem 1rem;">
          <div style="font-size:3rem;margin-bottom:1rem;">{icon}</div>
          <div class="flora-h3">{title}</div>
          <div style="font-size:0.875rem;color:var(--text-secondary);margin-top:8px;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Divider with label
# ---------------------------------------------------------------------------

def labeled_divider(label: str) -> None:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:1rem;margin:1.5rem 0;">
          <div style="flex:1;height:1px;background:var(--border);"></div>
          <span class="flora-label">{label}</span>
          <div style="flex:1;height:1px;background:var(--border);"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Toast-style notification
# ---------------------------------------------------------------------------

def toast_success(message: str) -> None:
    st.toast(f"✅ {message}", icon=None)


def toast_error(message: str) -> None:
    st.toast(f"❌ {message}", icon=None)
