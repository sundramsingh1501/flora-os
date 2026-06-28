# -*- coding: utf-8 -*-
"""
Flora OS - Markets Page
Stocks and crypto with live charts, watchlist management, and AI summaries.
"""

import streamlit as st
import plotly.graph_objects as go

from app.auth.session import require_auth
from app.database import get_db
from app.models import UserPreferences
from app.services.market_service import get_stock_data, get_crypto_data, get_stock_history
from app.ui.theme import apply_theme
from app.ui.navbar import render_navbar
from app.ui.components import section_header, empty_state, metric_card
from app.utils.logger import get_logger

logger = get_logger("pages.market")

apply_theme()
user = require_auth()
render_navbar(user, active_page="Markets")

# -- Load watchlist --
@st.cache_data(ttl=60, show_spinner=False)
def _get_market_data(stocks: tuple, cryptos: tuple):
    return {
        "stocks": get_stock_data(list(stocks)),
        "crypto": get_crypto_data(list(cryptos)),
    }

with get_db() as db:
    prefs = db.query(UserPreferences).filter_by(user_id=user.id).first()
    watchlist_stocks = list(prefs.stock_watchlist or ["AAPL", "GOOGL", "MSFT"]) if prefs else ["AAPL", "GOOGL", "MSFT"]
    watchlist_crypto = list(prefs.crypto_watchlist or ["bitcoin", "ethereum"]) if prefs else ["bitcoin", "ethereum"]

# -- Header --
st.markdown(
    """
    <h1 class="flora-h1" style="margin-bottom:0.5rem;">Markets</h1>
    <p style="color:var(--text-secondary);margin-bottom:1.5rem;">Live prices &middot; Your personal watchlist</p>
    """,
    unsafe_allow_html=True,
)

col_refresh = st.columns([5, 1])[1]
with col_refresh:
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with st.spinner("Fetching market data..."):
    data = _get_market_data(tuple(watchlist_stocks), tuple(watchlist_crypto))

stocks  = data["stocks"]
cryptos = data["crypto"]

# -- Market overview metrics --
if stocks:
    gainers    = [s for s in stocks if s.get("change_pct", 0) > 0]
    losers     = [s for s in stocks if s.get("change_pct", 0) < 0]
    top_gainer = max(gainers, key=lambda x: x["change_pct"], default=None) if gainers else None
    top_loser  = min(losers,  key=lambda x: x["change_pct"], default=None) if losers  else None

    cols = st.columns(4)
    with cols[0]:
        metric_card("Stocks Tracked", str(len(stocks)))
    with cols[1]:
        if top_gainer:
            metric_card("Top Gainer", top_gainer["ticker"], f"+{top_gainer['change_pct']:.2f}%", color="var(--accent-green)")
    with cols[2]:
        if top_loser:
            metric_card("Top Loser", top_loser["ticker"], f"{top_loser['change_pct']:.2f}%", color="var(--accent-red)")
    with cols[3]:
        metric_card("Crypto Tracked", str(len(cryptos)))
    st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

# -- Tabs --
tab_stocks, tab_crypto, tab_chart = st.tabs(["Stocks", "Crypto", "Charts"])

# -- Stocks tab --
with tab_stocks:
    section_header("Stock Watchlist", f"{len(stocks)} tickers", badge="Live")

    if not stocks:
        empty_state("", "No stocks in watchlist", "Add tickers in Settings.")
    else:
        for s in stocks:
            pct   = s.get("change_pct", 0)
            chg   = s.get("change", 0)
            color = "var(--accent-green)" if pct >= 0 else "var(--accent-red)"
            arrow = "&#9650;" if pct >= 0 else "&#9660;"
            market_cap = s.get("market_cap")
            cap_str = (
                f"${market_cap/1e12:.2f}T" if market_cap and market_cap > 1e12
                else f"${market_cap/1e9:.1f}B" if market_cap
                else "&mdash;"
            )
            st.markdown(
                f"""
                <div class="flora-card" style="margin-bottom:10px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="display:flex;align-items:center;gap:16px;">
                      <div style="width:44px;height:44px;background:var(--bg-elevated);
                                  border-radius:var(--radius-sm);display:flex;align-items:center;
                                  justify-content:center;font-weight:800;font-size:0.8rem;
                                  color:var(--accent-purple2);">{s["ticker"][:4]}</div>
                      <div>
                        <div style="font-weight:700;">{s["ticker"]}</div>
                        <div style="font-size:0.78rem;color:var(--text-secondary);">{s.get("name","")[:30]}</div>
                      </div>
                    </div>
                    <div style="text-align:center;">
                      <div style="font-size:0.72rem;color:var(--text-muted);">PRICE</div>
                      <div style="font-weight:700;font-size:1.1rem;">${s["price"]:,.2f}</div>
                    </div>
                    <div style="text-align:center;">
                      <div style="font-size:0.72rem;color:var(--text-muted);">CHANGE</div>
                      <div style="color:{color};font-weight:600;">{arrow} {abs(chg):.2f}</div>
                    </div>
                    <div style="text-align:center;">
                      <div style="font-size:0.72rem;color:var(--text-muted);">% CHANGE</div>
                      <div style="font-size:1.1rem;font-weight:700;color:{color};">{arrow} {abs(pct):.2f}%</div>
                    </div>
                    <div style="text-align:center;">
                      <div style="font-size:0.72rem;color:var(--text-muted);">MKT CAP</div>
                      <div style="font-weight:600;">{cap_str}</div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# -- Crypto tab --
with tab_crypto:
    section_header("Crypto Watchlist", f"{len(cryptos)} coins", badge="Live")

    if not cryptos:
        empty_state("", "No crypto in watchlist", "Add coins in Settings.")
    else:
        for c in cryptos:
            chg   = c.get("change_24h", 0)
            color = "var(--accent-green)" if chg >= 0 else "var(--accent-red)"
            arrow = "&#9650;" if chg >= 0 else "&#9660;"
            mkt_cap = c.get("market_cap", 0)
            cap_str = (
                f"${mkt_cap/1e12:.2f}T" if mkt_cap > 1e12
                else f"${mkt_cap/1e9:.1f}B" if mkt_cap
                else "&mdash;"
            )
            st.markdown(
                f"""
                <div class="flora-card" style="margin-bottom:10px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                      <div style="font-weight:700;font-size:1.05rem;">{c["name"].title()}</div>
                      <div style="font-size:0.78rem;color:var(--text-secondary);">24h change</div>
                    </div>
                    <div style="text-align:center;">
                      <div style="font-size:0.72rem;color:var(--text-muted);">PRICE (USD)</div>
                      <div style="font-weight:700;font-size:1.1rem;">${c["price"]:,.2f}</div>
                    </div>
                    <div style="text-align:center;">
                      <div style="font-size:0.72rem;color:var(--text-muted);">24H CHANGE</div>
                      <div style="font-size:1.1rem;font-weight:700;color:{color};">{arrow} {abs(chg):.2f}%</div>
                    </div>
                    <div style="text-align:center;">
                      <div style="font-size:0.72rem;color:var(--text-muted);">MKT CAP</div>
                      <div style="font-weight:600;">{cap_str}</div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# -- Chart tab --
with tab_chart:
    section_header("Price Chart", "Historical performance")

    if not watchlist_stocks:
        empty_state("", "No stocks to chart", "Add tickers in Settings.")
    else:
        selected_ticker = st.selectbox("Select ticker", watchlist_stocks)
        period = st.select_slider("Period", ["1wk", "1mo", "3mo", "6mo", "1y"], value="1mo")

        if selected_ticker:
            with st.spinner(f"Loading {selected_ticker} chart..."):
                hist = get_stock_history(selected_ticker, period=period)

            if hist:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist["dates"],
                    y=hist["close"],
                    mode="lines",
                    name=selected_ticker,
                    line=dict(color="#7c6af7", width=2.5),
                    fill="tozeroy",
                    fillcolor="rgba(124,106,247,0.08)",
                ))
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter", color="#8888aa"),
                    margin=dict(l=0, r=0, t=20, b=0),
                    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", showline=False, zeroline=False),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", showline=False, zeroline=False),
                    hovermode="x unified",
                    height=350,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"Could not load chart for {selected_ticker}. Check your internet connection.")
