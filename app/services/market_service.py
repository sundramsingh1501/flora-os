"""
Flora OS — Market Data Service
Stocks via yfinance, Crypto via CoinGecko (free, no key needed).
"""

from typing import Optional
import yfinance as yf
from pycoingecko import CoinGeckoAPI

from app.utils.logger import get_logger

logger = get_logger("services.market")

_cg = CoinGeckoAPI()


# ---------------------------------------------------------------------------
# Stocks
# ---------------------------------------------------------------------------

def get_stock_data(tickers: list[str]) -> list[dict]:
    """Fetch latest price, change, and basic info for a list of tickers."""
    results = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.fast_info
            hist = t.history(period="2d")
            if hist.empty:
                continue

            current = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
            change = current - prev
            pct = (change / prev * 100) if prev else 0.0

            results.append({
                "ticker": ticker.upper(),
                "name": getattr(info, "company_name", ticker),
                "price": round(current, 2),
                "change": round(change, 2),
                "change_pct": round(pct, 2),
                "currency": getattr(info, "currency", "USD"),
                "market_cap": getattr(info, "market_cap", None),
                "volume": getattr(info, "three_month_average_volume", None),
            })
        except Exception as exc:
            logger.warning("Stock fetch failed for %s: %s", ticker, exc)
    return results


def get_stock_history(ticker: str, period: str = "1mo") -> Optional[dict]:
    """Return OHLCV history for charting."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period)
        if hist.empty:
            return None
        return {
            "dates": [str(d.date()) for d in hist.index],
            "close": hist["Close"].round(2).tolist(),
            "volume": hist["Volume"].tolist(),
        }
    except Exception as exc:
        logger.warning("History fetch failed for %s: %s", ticker, exc)
        return None


# ---------------------------------------------------------------------------
# Crypto
# ---------------------------------------------------------------------------

def get_crypto_data(coin_ids: list[str]) -> list[dict]:
    """Fetch latest crypto prices from CoinGecko."""
    if not coin_ids:
        return []
    try:
        data = _cg.get_price(
            ids=",".join(coin_ids),
            vs_currencies="usd",
            include_24hr_change="true",
            include_market_cap="true",
        )
        results = []
        for coin_id, vals in data.items():
            results.append({
                "id": coin_id,
                "name": coin_id.title(),
                "price": vals.get("usd", 0),
                "change_24h": vals.get("usd_24h_change", 0),
                "market_cap": vals.get("usd_market_cap", 0),
                "currency": "USD",
            })
        return results
    except Exception as exc:
        logger.warning("CoinGecko fetch failed: %s", exc)
        return []


def get_market_summary(stocks: list[str], cryptos: list[str]) -> dict:
    """Single call that returns both stock and crypto data."""
    return {
        "stocks": get_stock_data(stocks),
        "crypto": get_crypto_data(cryptos),
    }
