"""
Flora OS — Gemini AI Service
Centralized wrapper around Google Gemini 2.5 Flash.
All agents call through this — never import genai directly.
"""

import json
import time
from typing import Any, Optional

import google.generativeai as genai

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("services.ai")

_MODEL_NAME = "gemini-2.5-flash"
_model: Optional[genai.GenerativeModel] = None


def _get_model() -> genai.GenerativeModel:
    global _model
    if _model is None:
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(
            model_name=_MODEL_NAME,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=4096,
            ),
        )
    return _model


def generate(prompt: str, temperature: float = 0.3, retries: int = 2) -> str:
    """Send a prompt to Gemini and return the text response."""
    model = _get_model()
    for attempt in range(retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=4096,
                    thinking_config={"thinking_budget": 0},
                ),
            )
            return response.text.strip()
        except Exception as exc:
            logger.warning("Gemini attempt %s/%s failed: %s", attempt + 1, retries, exc)
            if attempt < retries - 1:
                time.sleep(3)
    logger.error("Gemini generation failed after %s retries.", retries)
    return ""


def generate_json(prompt: str, temperature: float = 0.2) -> Any:
    """
    Ask Gemini to respond with valid JSON.
    Returns parsed Python object or empty dict on failure.
    """
    json_prompt = (
        f"{prompt}\n\n"
        "IMPORTANT: Respond ONLY with valid JSON. No markdown fences, no explanation, no extra text."
    )
    raw = generate(json_prompt, temperature=temperature)
    # Strip accidental markdown fences
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse error: %s | raw=%s", exc, raw[:200])
        return {}


def summarize(text: str, max_words: int = 40) -> str:
    """Summarize a piece of text in max_words words."""
    return generate(
        f"Summarize the following in exactly {max_words} words or fewer. "
        f"Be concise, informative, and professional:\n\n{text}",
        temperature=0.2,
    )


def score_importance(title: str, summary: str, user_interests: list[str]) -> float:
    """
    Score an article's importance for a user (1.0–10.0).
    Based on title, summary, and user interest tags.
    """
    result = generate_json(
        f"""Score the importance of this article for a user interested in: {', '.join(user_interests)}.

Article title: {title}
Article summary: {summary}

Return JSON: {{"score": <float 1.0-10.0>, "reason": "<10 words>"}}"""
    )
    try:
        return float(result.get("score", 5.0))
    except (TypeError, ValueError):
        return 5.0
