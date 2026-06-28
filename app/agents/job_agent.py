# -*- coding: utf-8 -*-
"""
Flora OS - Job Agent
Fetches personalized job openings and ranks them by fit using AI (single batch call).
"""

from app.services.job_service import fetch_all_jobs
from app.services.ai_service import generate_json
from app.utils.logger import get_logger

logger = get_logger("agents.job")

_MIN_KEYWORD_SCORE = 3.0  # fallback score for keyword-matched jobs


def _keyword_score(job: dict, roles: list, tech: list) -> float:
    """Fast keyword-match score as fallback when AI is unavailable."""
    text = f"{job.get('title','')} {job.get('description','')}".lower()
    hits = sum(1 for r in roles if r.lower() in text)
    hits += sum(1 for t in tech if t.lower() in text)
    return min(5.0 + hits * 0.5, 9.0)


def run(user_id: int, preferences: dict) -> list[dict]:
    """
    Fetch jobs, score them for fit in a SINGLE batch AI call, return ranked list.
    Falls back to keyword scoring if AI times out.
    """
    roles     = preferences.get("job_roles") or []
    locations = preferences.get("job_locations") or ["Remote"]
    tech      = preferences.get("tech_stack") or []
    exp_years = preferences.get("experience_years") or 0

    if not roles:
        logger.info("JobAgent: no roles set for user_id=%s, skipping.", user_id)
        return []

    logger.info("JobAgent running for user_id=%s roles=%s", user_id, roles)
    raw_jobs = fetch_all_jobs(roles, locations, tech)

    if not raw_jobs:
        return []

    # Build a single prompt to score ALL jobs at once
    user_profile = (
        f"Roles: {', '.join(roles)}. "
        f"Tech: {', '.join(tech) or 'any'}. "
        f"Location: {', '.join(locations)}. "
        f"Experience: {exp_years} year(s)."
    )

    jobs_text = "\n".join(
        f"{i+1}. Title: {j['title']} | Company: {j['company']} | "
        f"Location: {j['location']} | Desc: {j.get('description','')[:120]}"
        for i, j in enumerate(raw_jobs[:20])
    )

    prompt = f"""You are a career advisor. Score each job for this candidate:
{user_profile}

Jobs:
{jobs_text}

Return a JSON array with one object per job (same order):
[{{"fit_score": <1-10 float>, "fit_reason": "<8-word reason>", "match_tags": ["tag1","tag2"]}}, ...]

Only return the JSON array, nothing else."""

    scored = []
    try:
        result = generate_json(prompt)
        if isinstance(result, list) and len(result) == len(raw_jobs[:20]):
            for i, job in enumerate(raw_jobs[:20]):
                r = result[i] if i < len(result) else {}
                try:
                    fit_score = float(r.get("fit_score", _MIN_KEYWORD_SCORE))
                except (TypeError, ValueError):
                    fit_score = _keyword_score(job, roles, tech)
                scored.append({
                    **job,
                    "fit_score": fit_score,
                    "fit_reason": r.get("fit_reason", ""),
                    "match_tags": r.get("match_tags", []),
                    "user_id": user_id,
                })
        else:
            raise ValueError("Unexpected AI response shape")
    except Exception as exc:
        logger.warning("Batch AI scoring failed (%s), using keyword scores", exc)
        for job in raw_jobs[:20]:
            scored.append({
                **job,
                "fit_score": _keyword_score(job, roles, tech),
                "fit_reason": "Keyword match",
                "match_tags": [r for r in roles if r.lower() in job.get("title","").lower()],
                "user_id": user_id,
            })

    scored.sort(key=lambda x: x["fit_score"], reverse=True)
    logger.info("JobAgent: %s scored jobs for user_id=%s", len(scored), user_id)
    return scored
