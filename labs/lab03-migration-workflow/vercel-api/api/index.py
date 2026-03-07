"""Vercel serverless entry-point for the Migration Workflow Agent."""
# All source files (main.py, agent.py, state.py, prompts.py, llm_client.py)
# are copied to the deploy root (/var/task/) at deploy time, so this import
# resolves correctly inside Vercel's serverless runtime.
from main import app  # noqa: F401
