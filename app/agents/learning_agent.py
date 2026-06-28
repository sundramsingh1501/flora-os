"""
Flora OS — Learning Agent
Generates a daily learning resource, interview question, and motivational quote.
All personalized to the user's tech stack and interests.
"""

from app.services.ai_service import generate_json
from app.utils.logger import get_logger

logger = get_logger("agents.learning")


def run(user_id: int, preferences: dict) -> dict:
    """
    Returns dict with:
      - learning_resource: {title, url, type, why, duration}
      - interview_question: {question, topic, difficulty, hint, answer}
      - daily_quote: {text, author}
      - ai_recommendation: {title, description, action}
    """
    tech = preferences.get("tech_stack") or []
    roles = preferences.get("job_roles") or []
    categories = preferences.get("news_categories") or ["AI", "Technology"]

    logger.info("LearningAgent running for user_id=%s", user_id)

    profile = f"Tech stack: {', '.join(tech)}. Target roles: {', '.join(roles)}. Interests: {', '.join(categories)}."

    # Run all 4 in sequence (Gemini is fast enough; parallel would need threads)
    learning = _get_learning_resource(profile, tech, roles)
    interview_q = _get_interview_question(tech, roles)
    quote = _get_daily_quote(categories)
    recommendation = _get_ai_recommendation(profile, categories)

    return {
        "learning_resource": learning,
        "interview_question": interview_q,
        "daily_quote": quote,
        "ai_recommendation": recommendation,
    }


def _get_learning_resource(profile: str, tech: list, roles: list) -> dict:
    data = generate_json(
        f"""Recommend one specific learning resource (article, tutorial, YouTube video, course, or book chapter)
for this developer profile: {profile}

Requirements:
- Should be available free online or very widely known
- Highly relevant to their tech stack or career goals
- Something genuinely useful to read/watch today

Return JSON:
{{
  "title": "<resource title>",
  "type": "<Article | Video | Tutorial | Course | Book Chapter>",
  "source": "<publication or platform name>",
  "url": "<URL>",
  "duration": "<e.g. 15 min read | 30 min video>",
  "why": "<2-sentence explanation of why this is valuable today>"
}}"""
    )
    return data or {
        "title": "Attention Is All You Need",
        "type": "Paper",
        "source": "ArXiv",
        "url": "https://arxiv.org/abs/1706.03762",
        "duration": "45 min read",
        "why": "The foundational Transformer paper. Essential reading for anyone working with LLMs.",
    }


def _get_interview_question(tech: list, roles: list) -> dict:
    topic_hint = ", ".join((tech + roles)[:4]) or "Software Engineering"
    data = generate_json(
        f"""Generate one technical interview question for a candidate targeting: {topic_hint}.

Mix difficulty appropriately — sometimes easy, sometimes hard.

Return JSON:
{{
  "question": "<the interview question>",
  "topic": "<topic area, e.g. System Design | Algorithms | ML | Python>",
  "difficulty": "<Easy | Medium | Hard>",
  "hint": "<one-sentence hint without giving away the answer>",
  "answer": "<a thorough 3-4 sentence model answer>"
}}"""
    )
    return data or {
        "question": "Explain the difference between a process and a thread.",
        "topic": "Operating Systems",
        "difficulty": "Medium",
        "hint": "Think about memory sharing and scheduling.",
        "answer": "A process is an independent program in execution with its own memory space. "
                  "A thread is a lightweight unit of execution within a process that shares memory. "
                  "Threads are faster to create and context-switch but require synchronization.",
    }


def _get_daily_quote(categories: list) -> dict:
    theme = categories[0] if categories else "technology"
    data = generate_json(
        f"""Give me one powerful, real quote related to {theme}, innovation, learning, or success.
Must be from a real, well-known person.

Return JSON: {{"text": "<quote>", "author": "<Author Name, Title/Context>"}}"""
    )
    return data or {
        "text": "The best way to predict the future is to invent it.",
        "author": "Alan Kay, Computer Scientist",
    }


def _get_ai_recommendation(profile: str, categories: list) -> dict:
    data = generate_json(
        f"""You are Flora, a personal AI executive assistant.
Based on this user profile: {profile}

Give one specific, actionable recommendation for what this person should do or explore TODAY
to advance their career or skills.

Return JSON:
{{
  "title": "<short title, e.g. 'Explore RAG pipelines'>",
  "description": "<2-3 sentences of specific, actionable advice>",
  "action": "<concrete first step they can take in 15 minutes>",
  "category": "<Skill | Career | Tool | Research | Network>"
}}"""
    )
    return data or {
        "title": "Build a personal RAG pipeline",
        "description": "Retrieval-Augmented Generation is the most in-demand skill in AI right now. "
                        "Build a simple Q&A system over your own documents using LangChain + ChromaDB.",
        "action": "Open LangChain docs and complete the 'Q&A over Documents' quickstart — 15 minutes.",
        "category": "Skill",
    }
