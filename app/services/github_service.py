"""
Flora OS — GitHub Trending Service
Scrapes github.com/trending since there's no official API for it.
Falls back to GitHub search API for recent popular repos.
"""

import requests
from bs4 import BeautifulSoup

from app.utils.logger import get_logger

logger = get_logger("services.github")

_TRENDING_URL = "https://github.com/trending"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_trending_repos(language: str = "", since: str = "daily", limit: int = 10) -> list[dict]:
    """
    Scrape GitHub trending repos.
    language: e.g. 'python', 'javascript', '' for all
    since: daily | weekly | monthly
    """
    try:
        url = _TRENDING_URL
        if language:
            url += f"/{language}"
        resp = requests.get(url, params={"since": since}, headers=_HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        repos = []

        for article in soup.select("article.Box-row")[:limit]:
            # Name
            h2 = article.select_one("h2 a")
            if not h2:
                continue
            full_name = h2.get("href", "").strip("/")
            if not full_name or "/" not in full_name:
                continue

            # Description
            desc_el = article.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            # Stars
            stars_el = article.select_one("a[href$='/stargazers']")
            stars = stars_el.get_text(strip=True).replace(",", "") if stars_el else "0"

            # Language
            lang_el = article.select_one("[itemprop='programmingLanguage']")
            lang = lang_el.get_text(strip=True) if lang_el else ""

            # Stars today
            today_el = article.select_one("span.d-inline-block.float-sm-right")
            stars_today = today_el.get_text(strip=True) if today_el else ""

            repos.append({
                "full_name": full_name,
                "name": full_name.split("/")[1],
                "owner": full_name.split("/")[0],
                "description": description,
                "url": f"https://github.com/{full_name}",
                "stars": stars,
                "stars_today": stars_today,
                "language": lang,
            })

        logger.info("Fetched %s trending repos (lang=%s)", len(repos), language or "all")
        return repos

    except Exception as exc:
        logger.warning("GitHub trending scrape failed: %s", exc)
        return _fallback_github_search()


def _fallback_github_search() -> list[dict]:
    """Use GitHub Search API as fallback — no auth needed for limited queries."""
    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={
                "q": "stars:>100 pushed:>2024-01-01",
                "sort": "stars",
                "order": "desc",
                "per_page": 10,
            },
            headers={"Accept": "application/vnd.github+json"},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [
            {
                "full_name": r["full_name"],
                "name": r["name"],
                "owner": r["owner"]["login"],
                "description": r.get("description") or "",
                "url": r["html_url"],
                "stars": str(r.get("stargazers_count", 0)),
                "stars_today": "",
                "language": r.get("language") or "",
            }
            for r in items
        ]
    except Exception as exc:
        logger.warning("GitHub search API fallback failed: %s", exc)
        return []
