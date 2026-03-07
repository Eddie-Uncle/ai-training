"""
Lab 03 — Migration Workflow Agent
FastAPI application exposing the 4-phase planning agent.
"""
import sys
import os
import json
from dotenv import load_dotenv
load_dotenv()   # picks up ./python/.env  (contains ANTHROPIC_API_KEY)

# Try local vendored copy first (Railway/production), fall back to lab02 source
try:
    from llm_client import get_llm_client
except ImportError:
    sys.path.append(
        os.path.join(os.path.dirname(__file__), "../../lab02-code-analyzer-agent/python")
    )
    from llm_client import get_llm_client

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

from agent import MigrationAgent
from state import MigrationState

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Migration Workflow Agent",
    description="4-phase planning agent: analysis → planning → execution → verification",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

provider = os.getenv("LLM_PROVIDER", "anthropic")
llm = get_llm_client(provider)

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class MigrationRequest(BaseModel):
    source_framework: str
    target_framework: str
    files: Dict[str, str]   # filename → source content


class StepResult(BaseModel):
    id: int
    description: str
    status: str
    input_files: List[str] = []
    output_files: List[str] = []
    complexity: str = "medium"
    result: Optional[str] = None


class MigrationResponse(BaseModel):
    success: bool
    source_framework: str
    target_framework: str
    # Phase results
    migrated_files: Dict[str, str]
    plan_executed: List[StepResult]
    verification: Optional[Dict[str, Any]]
    # Agentic loop telemetry — proves the planning pattern ran
    iterations_count: int      # total agentic loop iterations across all phases
    tool_calls_count: int      # total tool calls made by the agent
    errors: List[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "healthy", "provider": provider}


@app.get("/frameworks")
async def list_frameworks():
    return {
        "sources": ["express", "koa", "hapi", "flask", "django"],
        "targets": ["fastapi", "flask", "django"],
    }


@app.post("/migrate", response_model=MigrationResponse)
async def migrate(request: MigrationRequest):
    """Run the full 4-phase migration workflow (blocking)."""
    if not request.files:
        raise HTTPException(status_code=422, detail="files map must not be empty")

    state = MigrationState(
        source_framework=request.source_framework,
        target_framework=request.target_framework,
        source_files=request.files,
    )

    try:
        result = MigrationAgent(llm).run(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return MigrationResponse(
        success=not result.errors,
        source_framework=result.source_framework,
        target_framework=result.target_framework,
        migrated_files=result.migrated_files,
        plan_executed=[
            StepResult(
                id=s.id,
                description=s.description,
                status=s.status,
                input_files=s.input_files,
                output_files=s.output_files,
                complexity=s.complexity,
                result=s.result,
            )
            for s in result.plan
        ],
        verification=result.verification_result,
        iterations_count=result.iterations_count,
        tool_calls_count=result.tool_calls_count,
        errors=result.errors,
    )


@app.post("/migrate/stream")
async def migrate_stream(request: MigrationRequest):
    """
    SSE endpoint — streams phase + tool-call progress events as the agent works.
    Each line is:  data: {"phase": "...", "message": "..."}
    Final line is: data: {"phase": "complete", "success": true, ...}
    """
    if not request.files:
        raise HTTPException(status_code=422, detail="files map must not be empty")

    state = MigrationState(
        source_framework=request.source_framework,
        target_framework=request.target_framework,
        source_files=request.files,
    )

    async def event_stream():
        events: list[str] = []

        def collect(phase: str, message: str):
            events.append(json.dumps({"phase": phase, "message": message}))

        result = MigrationAgent(llm).run(state, progress_callback=collect)

        # Yield all buffered progress events
        for ev in events:
            yield f"data: {ev}\n\n"

        # Final summary event
        yield f"data: {json.dumps({'phase': 'complete', 'success': not result.errors, 'migrated_files': list(result.migrated_files.keys()), 'iterations': result.iterations_count, 'tool_calls': result.tool_calls_count, 'errors': result.errors})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
