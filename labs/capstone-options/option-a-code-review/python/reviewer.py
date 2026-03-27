from __future__ import annotations

import json
import logging
from typing import Literal

from pydantic import BaseModel, Field

from llm_client import LLMClient
from prompts import build_review_prompt

logger = logging.getLogger(__name__)


# ── Pydantic models ────────────────────────────────────────────────────────────

class ReviewIssue(BaseModel):
    severity: Literal["critical", "high", "medium", "low"]
    category: Literal["bug", "security", "performance", "style"]
    line: int | None = None
    description: str
    suggestion: str


class ReviewMetrics(BaseModel):
    overall_score: int = Field(ge=1, le=10)
    complexity: Literal["low", "medium", "high"]
    maintainability: Literal["poor", "fair", "good", "excellent"]


class ReviewResponse(BaseModel):
    summary: str
    issues: list[ReviewIssue] = []
    suggestions: list[str] = []
    metrics: ReviewMetrics


# ── Reviewer ───────────────────────────────────────────────────────────────────

class CodeReviewer:
    def __init__(self) -> None:
        self._llm = LLMClient()

    def review(
        self,
        code: str,
        language: str,
        filename: str | None = None,
    ) -> ReviewResponse:
        system, user = build_review_prompt(code, language, filename)
        raw = self._llm.complete(system=system, user=user)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Strip markdown fences the model may have added despite instructions
            stripped = raw.strip()
            if stripped.startswith("```"):
                lines = stripped.splitlines()
                stripped = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                logger.error("LLM returned non-JSON response: %s", raw[:500])
                raise ValueError(f"LLM did not return valid JSON: {exc}") from exc

        return ReviewResponse.model_validate(data)
