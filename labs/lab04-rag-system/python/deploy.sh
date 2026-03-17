#!/usr/bin/env bash
# deploy.sh — Deploy Lab 04 RAG System to Railway
# Usage:  ./deploy.sh [--new]
#   --new   Force creation of a brand-new Railway project (ignores any existing link)
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[info]${NC}  $*"; }
success() { echo -e "${GREEN}[ok]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC}  $*"; }
die()     { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }

# ── Resolve script directory (always run from python/) ────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── 1. Pre-flight checks ──────────────────────────────────────────────────────
info "Checking prerequisites…"

command -v railway >/dev/null 2>&1 || die "Railway CLI not found. Install: brew install railway"

WHOAMI=$(railway whoami 2>&1) || die "Not logged in to Railway. Run: railway login"
success "Logged in as: $(echo "$WHOAMI" | grep -oE '\(.*\)' | tr -d '()')"

# ── 2. Load API keys from ~/.env if not already exported ──────────────────────
if [[ -f "$HOME/.env" ]]; then
  # shellcheck disable=SC1090
  set -o allexport; source "$HOME/.env"; set +o allexport
fi

[[ -n "${ANTHROPIC_API_KEY:-}" ]] || die "ANTHROPIC_API_KEY is not set. Add it to \$HOME/.env or export it."
[[ -n "${VOYAGE_API_KEY:-}"    ]] || die "VOYAGE_API_KEY is not set. Add it to \$HOME/.env or export it."

# ── 3. Link or create Railway project ─────────────────────────────────────────
FORCE_NEW="${1:-}"
PROJECT_NAME="lab04-rag-system"
SERVICE_NAME="api"

if [[ "$FORCE_NEW" == "--new" ]]; then
  info "Creating new Railway project '${PROJECT_NAME}'…"
  railway init --name "$PROJECT_NAME" <<<""
elif ! railway status >/dev/null 2>&1; then
  echo ""
  warn "No Railway project linked to this directory."
  echo "Choose an option:"
  echo "  1) Create a new project named '${PROJECT_NAME}'"
  echo "  2) Link an existing project"
  read -rp "Enter 1 or 2: " CHOICE
  case "$CHOICE" in
    1)
      info "Creating new Railway project '${PROJECT_NAME}'…"
      railway init --name "$PROJECT_NAME" <<<""
      ;;
    2)
      info "Launching interactive project link…"
      railway link
      ;;
    *)
      die "Invalid choice."
      ;;
  esac
else
  PROJECT_STATUS=$(railway status 2>&1)
  info "Using linked project → $(echo "$PROJECT_STATUS" | grep -i 'project' | head -1)"
fi

# ── 4. Create service with env vars (first deploy) or just update vars ────────
STATUS_OUT=$(railway status 2>&1)
if echo "$STATUS_OUT" | grep -qE "Service: None|No service linked"; then
  info "Creating service '${SERVICE_NAME}' with environment variables…"
  railway add \
    --service "$SERVICE_NAME" \
    --variables "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}" \
    --variables "VOYAGE_API_KEY=${VOYAGE_API_KEY}" \
    --variables "LLM_PROVIDER=anthropic"
  success "Service '${SERVICE_NAME}' created."
else
  info "Updating environment variables on existing service…"
  railway variable set \
    ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
    VOYAGE_API_KEY="$VOYAGE_API_KEY" \
    LLM_PROVIDER="anthropic" \
    --skip-deploys
  success "Environment variables updated."
fi

# ── 5. Deploy ─────────────────────────────────────────────────────────────────
info "Uploading and deploying…"
railway up --detach --service "$SERVICE_NAME"
success "Deployment triggered."

# ── 6. Generate / show public domain ─────────────────────────────────────────
echo ""
info "Generating public domain…"
railway domain 2>&1 || warn "Could not auto-generate domain. Run: railway domain"

# ── 7. Stream build logs ──────────────────────────────────────────────────────
echo ""
info "Streaming build logs (Ctrl-C to stop following — deploy continues in background)…"
railway logs --build 2>&1 | tail -80 || true

echo ""
success "Done!"
echo "  Dashboard: railway open"
echo "  Logs:      railway logs"
echo "  Status:    railway status"
echo "  Redeploy:  railway redeploy"

