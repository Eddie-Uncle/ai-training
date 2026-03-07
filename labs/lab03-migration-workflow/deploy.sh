#!/usr/bin/env bash
# deploy.sh — Deploy Lab 03 Migration Workflow Agent
# Supports Railway (preferred for Python/FastAPI) and Vercel (via serverless adapter)
#
# Usage:
#   bash deploy.sh railway    # deploy to Railway
#   bash deploy.sh vercel     # deploy to Vercel
#   bash deploy.sh            # deploy to Railway (default)
#
# Prerequisites:
#   Railway: railway CLI installed and logged in  (npm i -g @railway/cli)
#   Vercel:  vercel CLI installed and logged in   (npm i -g vercel)
#            ANTHROPIC_API_KEY set in Vercel project environment

set -euo pipefail

TARGET="${1:-railway}"
PYTHON_DIR="$(cd "$(dirname "$0")/python" && pwd)"
LAB_NAME="lab03-migration-workflow"

# Load ANTHROPIC_API_KEY from $HOME/.env if not already in environment
if [[ -z "${ANTHROPIC_API_KEY:-}" && -f "$HOME/.env" ]]; then
  ANTHROPIC_API_KEY=$(grep -E '^ANTHROPIC_API_KEY=' "$HOME/.env" | cut -d= -f2- | tr -d '"'"'" 2>/dev/null || echo "")
  export ANTHROPIC_API_KEY
fi

green()  { printf "\033[0;32m%s\033[0m\n" "$*"; }
red()    { printf "\033[0;31m%s\033[0m\n" "$*"; }
yellow() { printf "\033[0;33m%s\033[0m\n" "$*"; }
header() { printf "\n\033[1;34m══ %s ══\033[0m\n" "$*"; }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

check_cli() {
  local cli="$1"
  if ! command -v "$cli" &>/dev/null; then
    red "ERROR: '$cli' CLI not found."
    case "$cli" in
      railway) echo "  Install: npm install -g @railway/cli" ;;
      vercel)  echo "  Install: npm install -g vercel" ;;
    esac
    exit 1
  fi
}

check_env_var() {
  local var="$1"
  if [[ -z "${!var:-}" ]]; then
    yellow "WARNING: $var is not set in the current shell."
    yellow "         Make sure it is configured in the deployment platform."
  fi
}

# ---------------------------------------------------------------------------
# Railway deploy
# ---------------------------------------------------------------------------

deploy_railway() {
  header "Deploying to Railway"
  check_cli railway

  check_env_var ANTHROPIC_API_KEY

  echo "  Working directory: $PYTHON_DIR"
  cd "$PYTHON_DIR"

  # Ensure config files are present
  if [[ ! -f railway.json ]]; then
    red "ERROR: railway.json not found in $PYTHON_DIR"
    exit 1
  fi
  if [[ ! -f Procfile ]]; then
    red "ERROR: Procfile not found in $PYTHON_DIR"
    exit 1
  fi

  # Update anthropic version pin in requirements.txt to match what's installed
  INSTALLED_ANTHROPIC=$(python3 -c "import anthropic; print(anthropic.__version__)" 2>/dev/null || echo "")
  if [[ -n "$INSTALLED_ANTHROPIC" ]]; then
    yellow "  Pinning anthropic==$INSTALLED_ANTHROPIC in requirements.txt"
    sed -i.bak "s/^anthropic==.*/anthropic==$INSTALLED_ANTHROPIC/" requirements.txt && rm -f requirements.txt.bak
  fi

  # Vendor llm_client.py from lab02 — Railway only sees this directory
  LABS_DIR="$(dirname "$(dirname "$PYTHON_DIR")")"
  LAB02_CLIENT="$LABS_DIR/lab02-code-analyzer-agent/python/llm_client.py"
  if [[ -f "$LAB02_CLIENT" ]]; then
    cp "$LAB02_CLIENT" "$PYTHON_DIR/llm_client.py"
    echo "  Vendored llm_client.py from lab02"
  else
    red "ERROR: cannot find lab02 llm_client.py at $LAB02_CLIENT"
    exit 1
  fi

  # Init project if not already linked (.railway/config.json absent)
  if [[ ! -f .railway/config.json ]]; then
    echo "  Initialising Railway project (default workspace)..."
    railway init --name "$LAB_NAME"
  else
    echo "  Already linked to Railway project."
  fi

  # Check if a service is linked; if not, do a foreground deploy first so the
  # CLI registers the new service in .railway/config.json before we set vars.
  LINKED_SERVICE=$(railway status 2>/dev/null | grep -E '^Service:' | awk '{print $2}' || echo "None")
  if [[ "$LINKED_SERVICE" == "None" || -z "$LINKED_SERVICE" ]]; then
    echo "  No service linked — running initial deploy to create service..."
    railway up   # foreground; writes service ID into .railway/config.json
  fi

  # Set environment variables (service now exists and is linked)
  echo "  Setting environment variables..."
  railway variables set LLM_PROVIDER=anthropic
  if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    railway variables set ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
  fi
  if [[ -n "${ANTHROPIC_MODEL:-}" ]]; then
    railway variables set ANTHROPIC_MODEL="${ANTHROPIC_MODEL}"
  fi

  # Redeploy detached now that vars are set (picks up new env)
  echo "  Redeploying with environment variables applied..."
  railway up --detach

  green "  Railway deploy triggered."
  echo ""
  echo "  Tail logs:  railway logs --tail"
  echo "  Open app:   railway open"
  echo "  Status:     railway status"
  echo "  Start svc:  railway start"
}

# ---------------------------------------------------------------------------
# Vercel deploy
# ---------------------------------------------------------------------------

deploy_vercel() {
  header "Deploying to Vercel"
  check_cli vercel

  check_env_var ANTHROPIC_API_KEY

  # Vercel serves Python via serverless functions — we need api/index.py
  local api_dir="$PYTHON_DIR/../vercel-api"
  mkdir -p "$api_dir/api"

  # Write api/index.py wrapping the FastAPI app
  cat > "$api_dir/api/index.py" <<'PYEOF'
"""Vercel serverless entry-point for the Migration Workflow Agent."""
import sys
import os

# Add the python/ dir so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../python"))

from main import app  # noqa: F401  — Vercel picks up 'app' automatically
PYEOF

  # Write vercel.json
  cat > "$api_dir/vercel.json" <<'JSONEOF'
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ],
  "env": {
    "LLM_PROVIDER": "anthropic"
  }
}
JSONEOF

  # Copy requirements.txt so Vercel can install deps
  cp "$PYTHON_DIR/requirements.txt" "$api_dir/requirements.txt"

  echo "  Vercel adapter written to: $api_dir"
  echo ""

  cd "$api_dir"

  echo "  Deploying to Vercel..."
  if [[ "${VERCEL_PROD:-}" == "1" ]]; then
    vercel --prod --yes \
      -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
      -e LLM_PROVIDER=anthropic
  else
    vercel --yes \
      -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
      -e LLM_PROVIDER=anthropic
  fi

  green "  Vercel deploy complete."
  echo ""
  echo "  To deploy to production:  VERCEL_PROD=1 bash deploy.sh vercel"
  echo "  Manage env vars:          vercel env add ANTHROPIC_API_KEY"
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

header "Pre-flight: $LAB_NAME"

# Quick syntax check
echo "  Checking Python syntax..."
python3 -c "
import ast, os, sys
files = ['state.py','prompts.py','agent.py','main.py']
errors = []
for f in files:
    path = os.path.join('$PYTHON_DIR', f)
    try:
        ast.parse(open(path).read())
        print(f'  OK  {f}')
    except SyntaxError as e:
        print(f'  ERR {f}: {e}')
        errors.append(f)
if errors:
    sys.exit(1)
"

green "  All files OK"

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

case "$TARGET" in
  railway) deploy_railway ;;
  vercel)  deploy_vercel  ;;
  *)
    red "Unknown target: $TARGET"
    echo "Usage: bash deploy.sh [railway|vercel]"
    exit 1
    ;;
esac
