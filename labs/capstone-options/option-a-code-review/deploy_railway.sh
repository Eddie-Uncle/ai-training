#!/usr/bin/env bash
# deploy_railway.sh — deploy the AI Code Review Bot Python backend to Railway
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_DIR="$SCRIPT_DIR/python"

# ── colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[railway]${NC} $*"; }
warn() { echo -e "${YELLOW}[railway]${NC} $*"; }
die()  { echo -e "${RED}[railway] ERROR:${NC} $*" >&2; exit 1; }

# ── preflight ─────────────────────────────────────────────────────────────────
command -v railway >/dev/null 2>&1 || die "Railway CLI not found. Install: brew install railway"

info "Checking Railway authentication…"
if ! railway whoami >/dev/null 2>&1; then
  warn "Not logged in — opening browser for Railway login…"
  railway login
fi

# ── resolve ANTHROPIC_API_KEY ─────────────────────────────────────────────────
ANTHROPIC_KEY="${ANTHROPIC_API_KEY:-}"

if [[ -z "$ANTHROPIC_KEY" && -f "$HOME/.env" ]]; then
  ANTHROPIC_KEY=$(grep "^ANTHROPIC_API_KEY=" "$HOME/.env" | cut -d= -f2- | tr -d '[:space:]' || true)
fi

if [[ -z "$ANTHROPIC_KEY" && -f "$PYTHON_DIR/.env" ]]; then
  ANTHROPIC_KEY=$(grep "^ANTHROPIC_API_KEY=" "$PYTHON_DIR/.env" | cut -d= -f2- | tr -d '[:space:]' || true)
fi

[[ -z "$ANTHROPIC_KEY" ]] && die "ANTHROPIC_API_KEY is not set. Export it or add it to \$HOME/.env or python/.env"

info "API key found (${ANTHROPIC_KEY:0:14}…)"

# ── resolve optional ALLOWED_ORIGINS ─────────────────────────────────────────
ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-}"

if [[ -z "$ALLOWED_ORIGINS" ]]; then
  warn "ALLOWED_ORIGINS is not set."
  read -rp "Enter the Vercel frontend URL (or press Enter to skip / set later): " ALLOWED_ORIGINS
fi

# ── link or create Railway project ───────────────────────────────────────────
cd "$PYTHON_DIR"

info "Checking Railway project link…"
if ! railway status 2>/dev/null | grep -q "Project:"; then
  warn "No project linked — creating a new Railway project…"
  railway init --name "code-review-bot"
fi

# ── deploy ────────────────────────────────────────────────────────────────────
info "Deploying backend to Railway…"
railway up --detach

# give Railway a moment to register the service before setting vars
sleep 5

# ── set environment variables ─────────────────────────────────────────────────
info "Setting environment variables on Railway…"
railway variables --set "ANTHROPIC_API_KEY=$ANTHROPIC_KEY"
railway variables --set "LLM_MODEL=claude-3-5-haiku-20241022"

if [[ -n "$ALLOWED_ORIGINS" ]]; then
  railway variables --set "ALLOWED_ORIGINS=$ALLOWED_ORIGINS"
fi

# ── post-deploy info ──────────────────────────────────────────────────────────
info "Fetching deployment URL…"
BACKEND_URL=$(railway domain 2>/dev/null | tr -d '[:space:]' || true)

echo ""
echo -e "${GREEN}✓ Backend deployed!${NC}"
if [[ -n "$BACKEND_URL" ]]; then
  echo -e "  URL      : https://${BACKEND_URL}"
  echo -e "  Health   : https://${BACKEND_URL}/health"
  echo -e "  API docs : https://${BACKEND_URL}/docs"
  echo ""
  echo -e "${YELLOW}Next step:${NC} pass this URL to the frontend deploy:"
  echo -e "  VITE_API_URL=https://${BACKEND_URL} ./deploy_vercel.sh"
else
  warn "Could not determine URL automatically."
  echo -e "  Run ${YELLOW}cd python && railway domain${NC} to get your URL, then run:"
  echo -e "  ${YELLOW}VITE_API_URL=https://<your-url> ./deploy_vercel.sh${NC}"
fi
echo ""

# ── smoke test (only if curl available and URL known) ────────────────────────
if [[ -n "$BACKEND_URL" ]] && command -v curl >/dev/null 2>&1; then
  info "Running health check against deployed backend…"
  sleep 8
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" "https://${BACKEND_URL}/health" || true)
  if [[ "$HTTP" == "200" ]]; then
    info "Health check passed (HTTP 200) ✓"
  else
    warn "Health check returned HTTP $HTTP — the service may still be booting."
  fi
fi
