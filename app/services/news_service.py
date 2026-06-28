"""
Flora OS — News Service
Fetches news from NewsAPI + curated RSS feeds.
Returns raw article dicts normalized to a common schema.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser
import requests
from newsapi import NewsApiClient

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("services.news")

# Curated RSS feeds per category
_RSS_FEEDS: dict[str, list[str]] = {
    "AI & Machine Learning": [
        "https://www.artificialintelligence-news.com/feed/",
        "https://venturebeat.com/category/ai/feed/",
        "https://www.marktechpost.com/feed/",
        "https://feeds.feedburner.com/oreilly/radar",
    ],
    "Data Science": [
        "https://towardsdatascience.com/feed",
        "https://www.kdnuggets.com/feed",
        "https://www.datascienceweekly.org/rss",
    ],
    "GenAI & LLMs": [
        "https://thesequence.substack.com/feed",
        "https://www.interconnects.ai/feed",
        "https://bair.berkeley.edu/blog/feed.xml",
    ],
    "Research Papers": [
        "https://rss.arxiv.org/rss/cs.AI",
        "https://rss.arxiv.org/rss/cs.LG",
        "https://rss.arxiv.org/rss/cs.CL",
    ],
    "Technology": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.wired.com/feed/rss",
    ],
    "Startups": [
        "https://techcrunch.com/category/startups/feed/",
        "https://yourstory.com/feed",
        "https://inc42.com/feed/",
    ],
    "Indian News": [
        "https://timesofindia.indiatimes.com/rssfeeds/1081479906.cms",
        "https://feeds.feedburner.com/ndtvnews-india-news",
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    ],
    "Indian Markets": [
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://www.moneycontrol.com/rss/buzzingstocks.xml",
        "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
        "https://www.livemint.com/rss/markets",
    ],
    "Sports": [
        "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
        "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms",
        "https://feeds.feedburner.com/ndtvnews-sports",
        "https://sportstar.thehindu.com/rss/",
    ],
    "World News": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    ],
    "Business": [
        "https://economictimes.indiatimes.com/rss.cms",
        "https://www.livemint.com/rss/news",
    ],
    "Finance & Investing": [
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://www.moneycontrol.com/rss/MCtopnews.xml",
    ],
    "GitHub & Open Source": [
        "https://github.blog/feed/",
        "https://opensource.com/feed",
    ],
    "Career & Jobs": [
        "https://in.indeed.com/rss?q=data+scientist&l=India&fromage=1",
        "https://in.indeed.com/rss?q=machine+learning+engineer&l=India&fromage=1",
    ],
    "Science": [
        "https://www.sciencedaily.com/rss/top/science.xml",
        "https://www.newscientist.com/feed/home/",
    ],
    "Crypto": [
        "https://cointelegraph.com/rss",
        "https://coindesk.com/arc/outboundfeeds/rss/",
    ],
    "Product & Design": [
        "https://www.producthunt.com/feed",
        "https://uxdesign.cc/feed",
    ],
    # Legacy keys (kept for backward compat)
    "AI": [
        "https://www.artificialintelligence-news.com/feed/",
        "https://venturebeat.com/category/ai/feed/",
    ],
    "GenAI": [
        "https://thesequence.substack.com/feed",
    ],
    "Research": [
        "https://rss.arxiv.org/rss/cs.AI",
        "https://rss.arxiv.org/rss/cs.LG",
    ],
    "GitHub": [
        "https://github.blog/feed/",
    ],
}

_NEWSAPI_CATEGORY_MAP: dict[str, str] = {
    "Technology": "technology",
    "Business": "business",
    "Science": "science",
}


def _normalize_rss_entry(entry: dict, category: str) -> Optional[dict]:
    title = entry.get("title", "").strip()
    if not title:
        return None

    url = entry.get("link", "")
    summary = entry.get("summary", entry.get("description", ""))
    # Strip HTML tags
    if summary:
        import re
        summary = re.sub(r"<[^>]+>", "", summary).strip()[:500]

    published = entry.get("published_parsed")
    pub_dt = None
    if published:
        try:
            pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
        except Exception:
            pass

    # Dedupe key
    uid = hashlib.md5(url.encode()).hexdigest()

    return {
        "id": uid,
        "title": title,
        "summary": summary,
        "url": url,
        "source": entry.get("source", {}).get("title", category),
        "category": category,
        "image_url": None,
        "published_at": pub_dt,
    }


def fetch_rss_feed(url: str, category: str, max_items: int = 10) -> list[dict]:
    try:
        feed = feedparser.parse(url)
        results = []
        for entry in feed.entries[:max_items]:
            item = _normalize_rss_entry(entry, category)
            if item:
                results.append(item)
        return results
    except Exception as exc:
        logger.warning("RSS fetch failed for %s: %s", url, exc)
        return []


def fetch_newsapi(query: str, category: str, days_back: int = 1, max_items: int = 10) -> list[dict]:
    if not settings.news_api_key:
        return []
    try:
        client = NewsApiClient(api_key=settings.news_api_key)
        from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        resp = client.get_everything(
            q=query,
            language="en",
            sort_by="relevancy",
            page_size=max_items,
            from_param=from_date,
        )
        articles = resp.get("articles", [])
        results = []
        for a in articles:
            uid = hashlib.md5((a.get("url") or "").encode()).hexdigest()
            pub_dt = None
            if a.get("publishedAt"):
                try:
                    pub_dt = datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
                except Exception:
                    pass
            results.append({
                "id": uid,
                "title": (a.get("title") or "").strip(),
                "summary": (a.get("description") or "").strip()[:500],
                "url": a.get("url", ""),
                "source": a.get("source", {}).get("name", "NewsAPI"),
                "category": category,
                "image_url": a.get("urlToImage"),
                "published_at": pub_dt,
            })
        return results
    except Exception as exc:
        logger.warning("NewsAPI fetch failed for query=%s: %s", query, exc)
        return []


def fetch_all_news(categories: list[str], max_per_category: int = 8) -> list[dict]:
    """Fetch news for given categories from all available sources."""
    all_articles: list[dict] = []
    seen_ids: set[str] = set()

    for cat in categories:
        feeds = _RSS_FEEDS.get(cat, [])
        for feed_url in feeds[:2]:  # max 2 feeds per category
            items = fetch_rss_feed(feed_url, cat, max_items=max_per_category)
            for item in items:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    all_articles.append(item)

        # Supplement with NewsAPI for major categories
        if cat in _NEWSAPI_CATEGORY_MAP and len([a for a in all_articles if a["category"] == cat]) < 4:
            items = fetch_newsapi(cat, cat, max_items=5)
            for item in items:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    all_articles.append(item)

    logger.info("Fetched %s articles across %s categories", len(all_articles), len(categories))
    return all_articles
