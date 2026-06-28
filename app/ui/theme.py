"""
Flora OS — Global Theme & CSS Injection
Injects the full design system into every Streamlit page.
Dark glassmorphism aesthetic inspired by Linear, Notion, and Apple.
"""

import streamlit as st


FLORA_CSS = """
<style>
/* ── Google Font ────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── CSS Variables ──────────────────────────────────────── */
:root {
  --bg-base:        #09090f;
  --bg-surface:     #0f0f1a;
  --bg-elevated:    #141428;
  --bg-glass:       rgba(255,255,255,0.04);
  --bg-glass-hover: rgba(255,255,255,0.07);
  --border:         rgba(255,255,255,0.08);
  --border-active:  rgba(124,106,247,0.5);

  --accent-purple:  #7c6af7;
  --accent-purple2: #9d8ffa;
  --accent-green:   #4ade80;
  --accent-blue:    #38bdf8;
  --accent-amber:   #fbbf24;
  --accent-red:     #f87171;
  --accent-pink:    #f472b6;

  --text-primary:   #f0f0ff;
  --text-secondary: #8888aa;
  --text-muted:     #55556a;

  --radius-sm:  8px;
  --radius-md:  12px;
  --radius-lg:  16px;
  --radius-xl:  24px;

  --shadow-glow: 0 0 24px rgba(124,106,247,0.15);
  --shadow-card: 0 4px 24px rgba(0,0,0,0.4);
  --transition:  all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ── Reset & Base ───────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stApp"] {
  background: var(--bg-base) !important;
  color: var(--text-primary) !important;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
  font-size: 15px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

/* ── Hide Streamlit chrome ──────────────────────────────── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { visibility: hidden !important; height: 0 !important; }

/* ── Hide default Streamlit multipage sidebar nav ───────── */
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Main content padding ───────────────────────────────── */
[data-testid="stMain"] > div:first-child {
  padding-top: 0 !important;
}
.block-container {
  padding: 2rem 2.5rem !important;
  max-width: 1400px !important;
}

/* ── Sidebar ────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: var(--bg-surface) !important;
  border-right: 1px solid var(--border) !important;
  padding: 0 !important;
}
[data-testid="stSidebar"] > div {
  padding: 1.5rem 1rem !important;
}

/* ── Cards ──────────────────────────────────────────────── */
.flora-card {
  background: var(--bg-glass);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1.25rem 1.5rem;
  backdrop-filter: blur(12px);
  transition: var(--transition);
  position: relative;
  overflow: hidden;
}
.flora-card:hover {
  background: var(--bg-glass-hover);
  border-color: var(--border-active);
  box-shadow: var(--shadow-glow);
  transform: translateY(-1px);
}
.flora-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(124,106,247,0.4), transparent);
}

/* ── Metric Cards ───────────────────────────────────────── */
.flora-metric {
  background: var(--bg-glass);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 1.25rem;
  text-align: center;
  transition: var(--transition);
}
.flora-metric:hover { border-color: var(--border-active); box-shadow: var(--shadow-glow); }
.flora-metric .value { font-size: 2rem; font-weight: 700; color: var(--accent-purple2); }
.flora-metric .label { font-size: 0.8rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.08em; margin-top: 4px; }

/* ── Badges ─────────────────────────────────────────────── */
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 100px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.badge-purple { background: rgba(124,106,247,0.15); color: var(--accent-purple2); border: 1px solid rgba(124,106,247,0.3); }
.badge-green  { background: rgba(74,222,128,0.12);  color: var(--accent-green);   border: 1px solid rgba(74,222,128,0.25); }
.badge-blue   { background: rgba(56,189,248,0.12);  color: var(--accent-blue);    border: 1px solid rgba(56,189,248,0.25); }
.badge-amber  { background: rgba(251,191,36,0.12);  color: var(--accent-amber);   border: 1px solid rgba(251,191,36,0.25); }
.badge-red    { background: rgba(248,113,113,0.12); color: var(--accent-red);     border: 1px solid rgba(248,113,113,0.25); }
.badge-pink   { background: rgba(244,114,182,0.12); color: var(--accent-pink);    border: 1px solid rgba(244,114,182,0.25); }

/* ── Typography ─────────────────────────────────────────── */
.flora-h1 { font-size: 2.25rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1.1; }
.flora-h2 { font-size: 1.5rem;  font-weight: 700; letter-spacing: -0.02em; }
.flora-h3 { font-size: 1.15rem; font-weight: 600; }
.flora-label { font-size: 0.75rem; font-weight: 500; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.1em; }
.gradient-text {
  background: linear-gradient(135deg, var(--accent-purple2), var(--accent-blue));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ── Buttons ────────────────────────────────────────────── */
.stButton > button {
  background: linear-gradient(135deg, var(--accent-purple), #6357e8) !important;
  color: white !important;
  border: none !important;
  border-radius: var(--radius-md) !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.875rem !important;
  padding: 0.6rem 1.5rem !important;
  transition: var(--transition) !important;
  box-shadow: 0 4px 15px rgba(124,106,247,0.3) !important;
}
.stButton > button:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 20px rgba(124,106,247,0.45) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* Secondary button */
.btn-secondary > button {
  background: var(--bg-glass) !important;
  border: 1px solid var(--border) !important;
  box-shadow: none !important;
}
.btn-secondary > button:hover {
  border-color: var(--border-active) !important;
  box-shadow: var(--shadow-glow) !important;
}

/* ── Inputs ─────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  color: var(--text-primary) !important;
  font-family: 'Inter', sans-serif !important;
  transition: var(--transition) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
  border-color: var(--accent-purple) !important;
  box-shadow: 0 0 0 3px rgba(124,106,247,0.2) !important;
  outline: none !important;
}

/* ── Tabs ───────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--bg-surface) !important;
  border-radius: var(--radius-md) !important;
  padding: 4px !important;
  gap: 4px !important;
  border: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--text-secondary) !important;
  border-radius: var(--radius-sm) !important;
  font-weight: 500 !important;
  font-size: 0.875rem !important;
}
.stTabs [aria-selected="true"] {
  background: var(--accent-purple) !important;
  color: white !important;
}

/* ── Divider ────────────────────────────────────────────── */
hr { border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }

/* ── Scrollbar ──────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* ── Article card ───────────────────────────────────────── */
.article-card {
  background: var(--bg-glass);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1rem 1.25rem;
  transition: var(--transition);
  cursor: pointer;
}
.article-card:hover {
  border-color: var(--border-active);
  background: var(--bg-glass-hover);
  box-shadow: var(--shadow-glow);
}
.article-title { font-size: 1rem; font-weight: 600; line-height: 1.4; color: var(--text-primary); }
.article-meta  { font-size: 0.78rem; color: var(--text-secondary); margin-top: 4px; }
.article-summary { font-size: 0.875rem; color: var(--text-secondary); margin-top: 8px; line-height: 1.5; }
.importance-dot {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}

/* ── Sidebar nav items ──────────────────────────────────── */
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition);
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 0.9rem;
  text-decoration: none;
  margin-bottom: 2px;
}
.nav-item:hover { background: var(--bg-glass); color: var(--text-primary); }
.nav-item.active { background: rgba(124,106,247,0.15); color: var(--accent-purple2); border-left: 2px solid var(--accent-purple); }

/* ── Loading spinner override ───────────────────────────── */
.stSpinner > div { border-top-color: var(--accent-purple) !important; }

/* ── Alert boxes ────────────────────────────────────────── */
.stAlert { border-radius: var(--radius-md) !important; border: 1px solid var(--border) !important; }

/* ── Plotly chart background ────────────────────────────── */
.js-plotly-plot .plotly { background: transparent !important; }
</style>
"""


def apply_theme() -> None:
    """Inject the Flora OS design system. Call at the top of every page."""
    st.set_page_config(
        page_title="Flora OS",
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(FLORA_CSS, unsafe_allow_html=True)


def apply_theme_no_config() -> None:
    """For pages where set_page_config was already called."""
    st.markdown(FLORA_CSS, unsafe_allow_html=True)
