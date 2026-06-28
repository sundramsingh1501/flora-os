"""
Flora OS — Job Service
Fetches personalized job openings from Adzuna API + LinkedIn RSS feed.
"""

import hashlib
from typing import Optional
import requests
import feedparser

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("services.jobs")

_ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"


def _adzuna_country(location: str) -> str:
    """Map location to Adzuna country code."""
    india_cities = {"bangalore", "mumbai", "delhi", "hyderabad", "pune", "chennai", "kolkata", "india"}
    if any(c in location.lower() for c in india_cities):
        return "in"
    uk_cities = {"london", "manchester", "birmingham", "uk", "united kingdom"}
    if any(c in location.lower() for c in uk_cities):
        return "gb"
    return "us"


def fetch_adzuna_jobs(
    roles: list[str],
    locations: list[str],
    tech_stack: list[str],
    max_results: int = 15,
) -> list[dict]:
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        return []

    query = " OR ".join(roles[:3]) if roles else "Software Engineer"
    location_str = locations[0] if locations else "Remote"
    country = _adzuna_country(location_str)

    try:
        resp = requests.get(
            f"{_ADZUNA_BASE}/{country}/search/1",
            params={
                "app_id": settings.adzuna_app_id,
                "app_key": settings.adzuna_app_key,
                "what": query,
                "where": location_str,
                "results_per_page": max_results,
                "content-type": "application/json",
            },
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        jobs = []
        for r in results:
            uid = hashlib.md5((r.get("redirect_url") or "").encode()).hexdigest()
            jobs.append({
                "id": uid,
                "title": r.get("title", ""),
                "company": r.get("company", {}).get("display_name", "Unknown"),
                "location": r.get("location", {}).get("display_name", location_str),
                "salary_min": r.get("salary_min"),
                "salary_max": r.get("salary_max"),
                "description": (r.get("description") or "")[:300],
                "url": r.get("redirect_url", ""),
                "source": "Adzuna",
                "posted_at": r.get("created"),
            })
        return jobs
    except Exception as exc:
        logger.warning("Adzuna fetch failed: %s", exc)
        return []


def fetch_linkedin_rss_jobs(roles: list[str], location: str = "remote") -> list[dict]:
    """
    LinkedIn RSS job feed (public, no auth needed).
    Format: https://www.linkedin.com/jobs/search?keywords=...&location=...&f_TPR=r86400
    """
    if not roles:
        return []
    keyword = roles[0].replace(" ", "%20")
    loc = location.replace(" ", "%20")
    url = (
        f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        f"?keywords={keyword}&location={loc}&f_TPR=r86400&start=0"
    )
    # LinkedIn blocks scrapers — use their public RSS-like XML
    rss_url = f"https://www.linkedin.com/jobs/search?keywords={keyword}&location={loc}&f_TPR=r86400&format=rss"
    try:
        feed = feedparser.parse(rss_url)
        jobs = []
        for entry in feed.entries[:10]:
            uid = hashlib.md5((entry.get("link") or "").encode()).hexdigest()
            jobs.append({
                "id": uid,
                "title": entry.get("title", ""),
                "company": entry.get("author", ""),
                "location": location,
                "salary_min": None,
                "salary_max": None,
                "description": (entry.get("summary") or "")[:300],
                "url": entry.get("link", ""),
                "source": "LinkedIn",
                "posted_at": entry.get("published"),
            })
        return jobs
    except Exception as exc:
        logger.warning("LinkedIn RSS failed: %s", exc)
        return []


def fetch_remoteok_jobs(roles: list[str], tech_stack: list[str]) -> list[dict]:
    """RemoteOK JSON API — free, no key needed."""
    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "FloraOS/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        all_jobs = resp.json()
        if not isinstance(all_jobs, list):
            return []

        keywords = set(r.lower() for r in roles + tech_stack)
        filtered = []
        for job in all_jobs[1:]:  # first item is metadata
            tags = [t.lower() for t in (job.get("tags") or [])]
            title = (job.get("position") or "").lower()
            if any(k in title or k in tags for k in keywords):
                uid = hashlib.md5((job.get("url") or "").encode()).hexdigest()
                filtered.append({
                    "id": uid,
                    "title": job.get("position", ""),
                    "company": job.get("company", ""),
                    "location": "Remote",
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                    "description": (job.get("description") or "")[:300],
                    "url": job.get("url", ""),
                    "source": "RemoteOK",
                    "posted_at": job.get("date"),
                })
            if len(filtered) >= 10:
                break
        return filtered
    except Exception as exc:
        logger.warning("RemoteOK fetch failed: %s", exc)
        return []


def fetch_fresher_aiml_jobs() -> list[dict]:
    """
    Fetch Data Science / AIML fresher jobs (0-1 year experience) from
    Indeed India RSS + RemoteOK. No API key needed.
    """
    all_jobs: list[dict] = []
    seen: set[str] = set()

    # Indeed India RSS — entry level DS/ML
    indeed_queries = [
        "data+scientist+fresher",
        "machine+learning+engineer+entry+level",
        "AI+engineer+fresher",
        "data+analyst+fresher",
        "NLP+engineer",
    ]
    for q in indeed_queries:
        url = f"https://in.indeed.com/rss?q={q}&l=India&fromage=1&limit=5"
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                uid = hashlib.md5((entry.get("link") or "").encode()).hexdigest()
                if uid not in seen:
                    seen.add(uid)
                    all_jobs.append({
                        "id": uid,
                        "title": entry.get("title", ""),
                        "company": entry.get("author", "Various"),
                        "location": "India",
                        "description": (entry.get("summary") or "")[:300],
                        "url": entry.get("link", ""),
                        "source": "Indeed India",
                        "experience": "0–1 year",
                        "posted_at": entry.get("published"),
                    })
        except Exception as exc:
            logger.warning("Indeed RSS failed for %s: %s", q, exc)

    # RemoteOK — ML / AI / Data Science remote roles
    try:
        resp = requests.get(
            "https://remoteok.com/api?tags=machine-learning,data-science,ai",
            headers={"User-Agent": "FloraOS/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        raw = resp.json()
        if isinstance(raw, list):
            for job in raw[1:20]:
                uid = hashlib.md5((job.get("url") or "").encode()).hexdigest()
                if uid not in seen:
                    seen.add(uid)
                    all_jobs.append({
                        "id": uid,
                        "title": job.get("position", ""),
                        "company": job.get("company", ""),
                        "location": "Remote",
                        "description": (job.get("description") or "")[:300],
                        "url": job.get("url", ""),
                        "source": "RemoteOK",
                        "experience": "0–2 years",
                        "posted_at": job.get("date"),
                    })
    except Exception as exc:
        logger.warning("RemoteOK AIML fetch failed: %s", exc)

    logger.info("Fetched %s fresher AIML jobs", len(all_jobs))
    return all_jobs[:15]


def fetch_naukri_jobs(
    roles: list[str],
    locations: list[str],
    tech_stack: list[str],
    max_results: int = 15,
) -> list[dict]:
    """Fetch jobs from Naukri.com — uses a session to get cookies first, then calls their API."""
    if not roles:
        return []

    keyword = roles[0]
    location_str = (locations[0] if locations else "India")
    # Build a slug like "python-developer-jobs-in-bangalore"
    kw_slug = keyword.lower().replace(" ", "-")
    loc_slug = location_str.lower().replace(" ", "-")

    session = requests.Session()
    browser_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        # Step 1: visit homepage to get cookies
        session.get("https://www.naukri.com/", headers=browser_headers, timeout=10)

        # Step 2: call the API with session cookies + JSON headers
        api_headers = {
            **browser_headers,
            "Accept": "application/json",
            "appid": "109",
            "systemid": "109",
            "Referer": f"https://www.naukri.com/{kw_slug}-jobs-in-{loc_slug}",
        }
        params = {
            "noOfResults": max_results,
            "urlType": "search_by_keyword",
            "searchType": "adv",
            "keyword": keyword,
            "location": location_str,
            "experience": 0,
            "pageNo": 1,
        }
        resp = session.get(
            "https://www.naukri.com/jobapi/v3/search",
            headers=api_headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        job_list = data.get("jobDetails", []) or []
        results = []
        for j in job_list:
            uid = hashlib.md5((j.get("jdURL") or str(j.get("jobId", ""))).encode()).hexdigest()
            loc_label = location_str
            placeholders = j.get("placeholders") or []
            for ph in placeholders:
                if ph.get("type") == "location":
                    loc_label = ph.get("label", location_str)
                    break
            url = j.get("jdURL", "")
            if url and not url.startswith("http"):
                url = "https://www.naukri.com" + url
            results.append({
                "id": uid,
                "title": j.get("title", ""),
                "company": j.get("companyName", ""),
                "location": loc_label,
                "salary_min": None,
                "salary_max": None,
                "description": (j.get("jobDescription") or "")[:300],
                "url": url,
                "source": "Naukri",
                "posted_at": j.get("footerPlaceholderLabel", ""),
            })
        logger.info("Naukri: fetched %s jobs for '%s'", len(results), keyword)
        return results
    except Exception as exc:
        logger.warning("Naukri fetch failed: %s", exc)
        return []


def fetch_linkedin_jobs(
    roles: list[str],
    locations: list[str],
    max_results: int = 10,
) -> list[dict]:
    """Fetch jobs from LinkedIn public job search (no API key needed)."""
    if not roles:
        return []

    keyword = roles[0].replace(" ", "%20")
    location_str = (locations[0] if locations else "India").replace(" ", "%20")
    url = (
        f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        f"?keywords={keyword}&location={location_str}&f_TPR=r86400&start=0"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        from html.parser import HTMLParser

        class _LIParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.jobs: list[dict] = []
                self._cur: dict = {}
                self._in_title = self._in_company = self._in_location = False

            def handle_starttag(self, tag, attrs):
                d = dict(attrs)
                cls = d.get("class", "")
                if "base-search-card__title" in cls:
                    self._in_title = True
                elif "base-search-card__subtitle" in cls:
                    self._in_company = True
                elif "job-search-card__location" in cls:
                    self._in_location = True
                elif tag == "a" and "base-card__full-link" in cls:
                    self._cur["url"] = d.get("href", "")

            def handle_endtag(self, tag):
                self._in_title = self._in_company = self._in_location = False

            def handle_data(self, data):
                data = data.strip()
                if not data:
                    return
                if self._in_title:
                    self._cur["title"] = data
                elif self._in_company:
                    self._cur["company"] = data
                elif self._in_location:
                    self._cur["location"] = data
                    if self._cur.get("title"):
                        uid = hashlib.md5(self._cur.get("url", data).encode()).hexdigest()
                        self.jobs.append({
                            "id": uid,
                            "title": self._cur.get("title", ""),
                            "company": self._cur.get("company", ""),
                            "location": self._cur.get("location", ""),
                            "salary_min": None,
                            "salary_max": None,
                            "description": "",
                            "url": self._cur.get("url", ""),
                            "source": "LinkedIn",
                            "posted_at": None,
                        })
                        self._cur = {}

        parser = _LIParser()
        parser.feed(resp.text)
        results = parser.jobs[:max_results]
        logger.info("LinkedIn: fetched %s jobs for '%s'", len(results), roles[0])
        return results
    except Exception as exc:
        logger.warning("LinkedIn fetch failed: %s", exc)
        return []


def fetch_indeed_india_jobs(
    roles: list[str],
    locations: list[str],
    max_results: int = 10,
) -> list[dict]:
    """Fetch jobs from Indeed India via RSS — no API key needed."""
    if not roles:
        return []
    results = []
    seen: set[str] = set()
    for role in roles[:2]:
        loc = (locations[0] if locations else "India").replace(" ", "+")
        kw  = role.replace(" ", "+")
        url = f"https://in.indeed.com/rss?q={kw}&l={loc}&fromage=7&limit=10"
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_results]:
                uid = hashlib.md5((entry.get("link") or "").encode()).hexdigest()
                if uid in seen:
                    continue
                seen.add(uid)
                results.append({
                    "id": uid,
                    "title": entry.get("title", ""),
                    "company": entry.get("author", ""),
                    "location": locations[0] if locations else "India",
                    "salary_min": None,
                    "salary_max": None,
                    "description": (entry.get("summary") or "")[:300],
                    "url": entry.get("link", ""),
                    "source": "Indeed India",
                    "posted_at": entry.get("published"),
                })
        except Exception as exc:
            logger.warning("Indeed India RSS failed for %s: %s", role, exc)
    logger.info("Indeed India: fetched %s jobs", len(results))
    return results


def fetch_all_jobs(
    roles: list[str],
    locations: list[str],
    tech_stack: list[str],
) -> list[dict]:
    """Aggregate jobs from LinkedIn, Indeed India, Adzuna, RemoteOK — deduplicated."""
    all_jobs: list[dict] = []
    seen: set[str] = set()

    for source_jobs in [
        fetch_linkedin_jobs(roles, locations),
        fetch_indeed_india_jobs(roles, locations),
        fetch_adzuna_jobs(roles, locations, tech_stack),
        fetch_remoteok_jobs(roles, tech_stack),
    ]:
        for job in source_jobs:
            if job["id"] not in seen:
                seen.add(job["id"])
                all_jobs.append(job)

    logger.info("Fetched %s jobs total across all sources", len(all_jobs))
    return all_jobs
