"""
Flora OS -- Email Hub
AI-processed Gmail summaries, action items, reply drafts, categories.
"""

import streamlit as st

from app.auth.session import require_auth
from app.database import get_db
from app.models import EmailSummary
from app.ui.theme import apply_theme
from app.ui.navbar import render_navbar
from app.ui.components import section_header, empty_state, labeled_divider
from app.utils.logger import get_logger

logger = get_logger("pages.email_hub")

apply_theme()
user = require_auth()
render_navbar(user, active_page="Email Hub")


@st.cache_data(ttl=120, show_spinner=False)
def _load_emails(user_id: int):
    with get_db() as db:
        emails = (
            db.query(EmailSummary)
            .filter(EmailSummary.user_id == user_id)
            .order_by(EmailSummary.received_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": e.id,
                "subject": e.subject,
                "sender_name": e.sender_name or "",
                "sender_email": e.sender_email,
                "summary": e.summary,
                "action_items": e.action_items or [],
                "reply_draft": e.reply_draft or "",
                "category": e.category,
                "importance": e.importance,
                "received_at": str(e.received_at)[:16] if e.received_at else "",
                "is_actioned": e.is_actioned,
            }
            for e in emails
        ]


emails = _load_emails(user.id)

st.markdown(
    """
    <h1 class="flora-h1" style="margin-bottom:0.5rem;">Email Hub</h1>
    <p style="color:var(--text-secondary);margin-bottom:1.5rem;">
      Job emails only &middot; Interviews, assessments, offers &amp; rejections
    </p>
    """,
    unsafe_allow_html=True,
)

# Always show Sync button at top when Gmail is connected
from app.models import GmailConnection
from app.utils.encryption import decrypt
with get_db() as _db:
    _gc = _db.query(GmailConnection).filter_by(user_id=user.id, is_active=True).first()
    if _gc:
        try:
            _gmail_conn = {
                "access_token": decrypt(_gc.access_token_enc),
                "refresh_token": decrypt(_gc.refresh_token_enc) if _gc.refresh_token_enc else "",
                "is_active": True,
            }
        except Exception:
            _gmail_conn = None
    else:
        _gmail_conn = None

if not _gmail_conn:
    st.markdown(
        """
        <div class="flora-card" style="text-align:center;padding:3rem;">
          <div style="font-size:3rem;margin-bottom:1rem;">&#9993;</div>
          <div style="font-size:1.25rem;font-weight:700;margin-bottom:0.5rem;">Gmail Not Connected</div>
          <div style="font-size:0.875rem;color:var(--text-secondary);max-width:400px;margin:0 auto 1.5rem;">
            Connect your Gmail to automatically fetch interview calls, test links,
            offer letters and rejection emails every morning.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Connect Gmail in Settings", use_container_width=False):
        st.switch_page("pages/settings.py")
    st.stop()

# Sync button — always visible
_sync_col, _spacer = st.columns([1, 3])
with _sync_col:
    if st.button("🔄 Sync Job Emails Now", use_container_width=True):
        with st.spinner("Scanning Gmail for interview, test & rejection emails…"):
            from app.agents.gmail_agent import fetch_and_process_emails
            from app.models import EmailSummary
            new_emails = fetch_and_process_emails(
                _gmail_conn["access_token"],
                _gmail_conn["refresh_token"],
                user.id,
                hours_back=24,
            )
            if new_emails:
                with get_db() as _db2:
                    existing_ids = {
                        r[0] for r in _db2.query(EmailSummary.gmail_message_id)
                        .filter_by(user_id=user.id).all()
                    }
                    added = 0
                    for e in new_emails:
                        if e["gmail_message_id"] not in existing_ids:
                            _db2.add(EmailSummary(
                                user_id=e["user_id"],
                                gmail_message_id=e["gmail_message_id"],
                                subject=e["subject"],
                                sender_name=e.get("sender_name", ""),
                                sender_email=e.get("sender_email", ""),
                                summary=e.get("summary", ""),
                                action_items=e.get("action_items", []),
                                reply_draft=e.get("reply_draft", ""),
                                category=e.get("category", "general"),
                                importance=e.get("importance", "normal"),
                                received_at=e.get("received_at"),
                            ))
                            added += 1
                st.success(f"Synced {added} new job emails.")
            else:
                st.info("No new interview/test/rejection emails in the last 24 hours.")
        _load_emails.clear()
        st.rerun()

if not emails:
    empty_state("&#128205;", "No job emails yet",
                "Hit 'Sync Job Emails Now' above — Flora scans for interviews, tests, offers & rejections.")
    st.stop()

# Stats
urgent = [e for e in emails if e["importance"] == "urgent"]
action = [e for e in emails if e["action_items"]]
with_draft = [e for e in emails if e["reply_draft"]]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="flora-metric"><div class="value">{len(emails)}</div><div class="label">Total Emails</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="flora-metric"><div class="value" style="color:var(--accent-red);">{len(urgent)}</div><div class="label">Urgent</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="flora-metric"><div class="value" style="color:var(--accent-amber);">{len(action)}</div><div class="label">Need Action</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="flora-metric"><div class="value" style="color:var(--accent-green);">{len(with_draft)}</div><div class="label">Drafts Ready</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

# Filters
col_filter1, col_filter2, col_search = st.columns([1.5, 1.5, 3])
with col_filter1:
    importance_filter = st.selectbox("Importance", ["All", "Urgent", "Normal", "Low"], label_visibility="collapsed")
with col_filter2:
    category_filter = st.selectbox("Category", ["All"] + list({e["category"] for e in emails}), label_visibility="collapsed")
with col_search:
    search_q = st.text_input("Search", placeholder="Search emails...", label_visibility="collapsed")

filtered = emails
if importance_filter != "All":
    filtered = [e for e in filtered if e["importance"].lower() == importance_filter.lower()]
if category_filter != "All":
    filtered = [e for e in filtered if e["category"] == category_filter]
if search_q:
    q = search_q.lower()
    filtered = [e for e in filtered if q in e["subject"].lower() or q in e["summary"].lower() or q in e["sender_email"].lower()]

st.markdown(f'<div style="font-size:0.8rem;color:var(--text-muted);margin-bottom:1rem;">Showing {len(filtered)} of {len(emails)} emails</div>', unsafe_allow_html=True)

if not filtered:
    empty_state("&#128269;", "No emails match your filters")
else:
    for email in filtered:
        sender_display = email["sender_name"] or email["sender_email"]
        imp = email["importance"]
        imp_badge_color = "red" if imp == "urgent" else "purple" if imp == "normal" else "blue"
        cat_colors = {
            "urgent": "red", "newsletter": "blue", "receipt": "green",
            "social": "pink", "meeting": "amber", "general": "purple",
        }

        prefix = "[URGENT] " if imp == "urgent" else ""
        with st.expander(f"{prefix}{email['subject']} -- {sender_display} | {email['received_at']}", expanded=(imp == "urgent")):
            st.markdown(
                f"""
                <div style="display:flex;gap:8px;margin-bottom:12px;">
                  <span class="badge badge-{imp_badge_color}">{imp.upper()}</span>
                  <span class="badge badge-{cat_colors.get(email['category'],'purple')}">{email['category']}</span>
                  <span style="font-size:0.78rem;color:var(--text-muted);">From: {email['sender_email']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div style="background:var(--bg-elevated);border-radius:var(--radius-md);
                            padding:0.875rem;margin-bottom:1rem;">
                  <div style="font-size:0.72rem;color:var(--accent-purple2);text-transform:uppercase;
                              letter-spacing:0.08em;margin-bottom:6px;">AI Summary</div>
                  <div style="font-size:0.875rem;line-height:1.6;">{email['summary']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if email["action_items"]:
                st.markdown('<div style="font-size:0.72rem;color:var(--accent-amber);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">Action Items</div>', unsafe_allow_html=True)
                for item in email["action_items"]:
                    st.markdown(
                        f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:4px;font-size:0.875rem;">'
                        f'<span style="color:var(--accent-amber);margin-top:2px;">-&gt;</span>{item}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

            if email["reply_draft"]:
                st.markdown('<div style="font-size:0.72rem;color:var(--accent-green);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">Draft Reply (AI Generated)</div>', unsafe_allow_html=True)
                draft_text = st.text_area(
                    "Draft",
                    value=email["reply_draft"],
                    height=120,
                    key=f"draft_{email['id']}",
                    label_visibility="collapsed",
                )
                col_copy, col_note = st.columns([1, 3])
                with col_copy:
                    if st.button("Copy Draft", key=f"copy_{email['id']}"):
                        st.code(draft_text)
                with col_note:
                    st.markdown(
                        '<div style="font-size:0.75rem;color:var(--text-muted);padding-top:8px;">'
                        'Flora never sends emails automatically. Review before sending.</div>',
                        unsafe_allow_html=True,
                    )

