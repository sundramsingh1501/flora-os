"""
Flora OS — AI Research Agent
Fetches latest ArXiv papers + GitHub trending repos.
Summarizes papers for non-academic consumption.
"""

from app.services.news_service import fetch_rss_feed
from app.services.github_service import get_trending_repos
from app.services.ai_service import summarize, generate_json
from app.utils.logger import get_logger

logger = get_logger("agents.research")

_ARXIV_FEEDS = {
    "cs.AI": "https://rss.arxiv.org/rss/cs.AI",
    "cs.LG": "https://rss.arxiv.org/rss/cs.LG",
    "cs.CL": "https://rss.arxiv.org/rss/cs.CL",
    "cs.CV": "https://rss.arxiv.org/rss/cs.CV",
}


def run(user_id: int, preferences: dict) -> dict:
    """
    Fetch and process research papers + trending repos.

    Returns dict with:
      - papers: list of enriched paper dicts
      - trending_repos: list of GitHub trending repos
      - ai_tool_of_day: dict
    """
    categories = preferences.get("news_categories") or []
    tech = preferences.get("tech_stack") or []

    # Decide which arxiv feeds to include
    feeds_to_fetch = ["cs.AI", "cs.LG"]
    if any("cv" in c.lower() or "vision" in c.lower() for c in categories):
        feeds_to_fetch.append("cs.CV")
    if any("nlp" in c.lower() or "language" in c.lower() for c in categories):
        feeds_to_fetch.append("cs.CL")

    logger.info("ResearchAgent running for user_id=%s", user_id)

    # Papers
    papers = []
    for feed_key in feeds_to_fetch:
        raw = fetch_rss_feed(_ARXIV_FEEDS[feed_key], "Research", max_items=5)
        for paper in raw:
            plain_summary = summarize(
                f"{paper['title']}. {paper['summary']}",
                max_words=40
            )
            papers.append({
                **paper,
                "summary": plain_summary,
                "importance_score": 7.0,
                "read_time_minutes": 8,
                "user_id": user_id,
            })

    # GitHub trending (prefer user's tech stack language)
    lang = ""
    if tech:
        lang_map = {
            "python": "python", "javascript": "javascript", "typescript": "typescript",
            "go": "go", "rust": "rust", "java": "java", "c++": "cpp",
        }
        for t in tech:
            if t.lower() in lang_map:
                lang = lang_map[t.lower()]
                break

    trending = get_trending_repos(language=lang, since="daily", limit=10)

    # AI Tool of the Day — ask Gemini
    tool_of_day = _get_ai_tool_of_day(categories, tech)

    return {
        "papers": papers[:8],
        "trending_repos": trending,
        "ai_tool_of_day": tool_of_day,
    }


def _get_ai_tool_of_day(categories: list[str], tech: list[str]) -> dict:
    data = generate_json(
        f"""Recommend one AI tool or library released or updated recently that would be useful
for someone interested in: {', '.join(categories + tech)}.

Return JSON:
{{
  "name": "<tool name>",
  "tagline": "<one-line description>",
  "why": "<2-sentence explanation of why this is useful>",
  "url": "<official URL>",
  "category": "<AI Tool | Library | Framework | API | Dataset>"
}}"""
    )
    return data or {
        "name": "LangChain",
        "tagline": "Build applications powered by language models",
        "why": "LangChain provides composable tools for building LLM-powered pipelines and agents.",
        "url": "https://langchain.com",
        "category": "Framework",
    }
