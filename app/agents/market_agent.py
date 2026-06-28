"""
Flora OS — Market Agent
Fetches stock + crypto data and generates a concise AI market summary.
"""

from app.services.market_service import get_market_summary
from app.services.ai_service import generate
from app.utils.logger import get_logger

logger = get_logger("agents.market")


def run(user_id: int, preferences: dict) -> dict:
    """
    Fetch market data and produce a structured market report.

    Returns dict with keys: stocks, crypto, summary, top_mover
    """
    stocks = preferences.get("stock_watchlist") or ["AAPL", "GOOGL", "MSFT"]
    cryptos = preferences.get("crypto_watchlist") or ["bitcoin", "ethereum"]

    logger.info("MarketAgent running for user_id=%s", user_id)

    data = get_market_summary(stocks, cryptos)
    stock_data = data.get("stocks", [])
    crypto_data = data.get("crypto", [])

    # Find top mover
    all_assets = []
    for s in stock_data:
        all_assets.append({"name": s["ticker"], "change_pct": s.get("change_pct", 0), "type": "stock"})
    for c in crypto_data:
        all_assets.append({"name": c["name"], "change_pct": c.get("change_24h", 0), "type": "crypto"})

    top_mover = max(all_assets, key=lambda x: abs(x["change_pct"]), default=None) if all_assets else None

    # AI market summary
    if stock_data or crypto_data:
        context = _build_market_context(stock_data, crypto_data)
        summary = generate(
            f"Write a 3-sentence professional market briefing for an executive based on this data:\n{context}\n"
            "Be concise, factual, and highlight the most important movement."
        )
    else:
        summary = "Market data unavailable. Please check your watchlist in settings."

    return {
        "stocks": stock_data,
        "crypto": crypto_data,
        "summary": summary,
        "top_mover": top_mover,
    }


def _build_market_context(stocks: list[dict], crypto: list[dict]) -> str:
    lines = []
    for s in stocks:
        direction = "▲" if s["change_pct"] >= 0 else "▼"
        lines.append(
            f"{s['ticker']}: ${s['price']} {direction}{abs(s['change_pct']):.2f}%"
        )
    for c in crypto:
        direction = "▲" if c.get("change_24h", 0) >= 0 else "▼"
        lines.append(
            f"{c['name']}: ${c['price']:,.2f} {direction}{abs(c.get('change_24h', 0)):.2f}% (24h)"
        )
    return "\n".join(lines)
