from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from reviewer import CodeReviewer, ReviewResponse

# ── bootstrap ─────────────────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

MAX_CODE_LENGTH = 50_000

SUPPORTED_LANGUAGES = {
    "python", "javascript", "typescript", "java", "go",
    "rust", "c", "cpp", "ruby", "php", "swift", "kotlin",
    "scala", "bash", "shell", "sql", "html", "css",
}

# ── rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["20/minute"])

# ── lifespan (instantiate reviewer once at startup) ───────────────────────────
reviewer: CodeReviewer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global reviewer
    reviewer = CodeReviewer()
    logger.info("CodeReviewer ready (model: %s)", reviewer._llm.model)
    yield


# ── app ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Code Review Bot",
    description="Submit code and receive structured, categorized feedback from Claude.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── request / response models ─────────────────────────────────────────────────
class ReviewRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Source code to review")
    language: str = Field(..., min_length=1, description="Programming language (e.g. python)")
    filename: str | None = Field(None, description="Optional filename for context")

    @field_validator("code")
    @classmethod
    def code_not_too_long(cls, v: str) -> str:
        if len(v) > MAX_CODE_LENGTH:
            raise ValueError(f"code exceeds maximum length of {MAX_CODE_LENGTH:,} characters")
        return v

    @field_validator("language")
    @classmethod
    def language_supported(cls, v: str) -> str:
        normalised = v.lower().strip()
        if normalised not in SUPPORTED_LANGUAGES:
            # Warn but don't reject — the LLM may still do a reasonable job
            logger.warning("Language '%s' not in known list; proceeding anyway", v)
        return normalised


# ── routes ────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", summary="Health check")
async def health() -> dict:
    model = reviewer._llm.model if reviewer else "not initialised"
    return {"status": "healthy", "model": model}


@app.post("/review", response_model=ReviewResponse, summary="Review code")
@limiter.limit("20/minute")
async def review_code(request: Request, body: ReviewRequest) -> ReviewResponse:
    logger.info(
        "Review request — language=%s  filename=%s  chars=%d",
        body.language,
        body.filename or "(none)",
        len(body.code),
    )

    if reviewer is None:
        raise HTTPException(status_code=503, detail="Reviewer not initialised")

    try:
        result = reviewer.review(
            code=body.code,
            language=body.language,
            filename=body.filename,
        )
    except ValueError as exc:
        logger.error("Review failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info(
        "Review complete — issues=%d  score=%s",
        len(result.issues),
        result.metrics.overall_score,
    )
    return result
