#!/usr/bin/env bash
# deploy_railway.sh — deploy the multi-agent Python backend to Railway
set -euo pipefail

PYTHON_DIR="$(cd "$(dirname "$0")/python" && pwd)"

# ── colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[railway]${NC} $*"; }
warn()    { echo -e "${YELLOW}[railway]${NC} $*"; }
die()     { echo -e "${RED}[railway] ERROR:${NC} $*" >&2; exit 1; }

# ── preflight checks ─────────────────────────────────────────────────────────
command -v railway >/dev/null 2>&1 || die "Railway CLI not found. Install: brew install railway"

info "Checking Railway authentication…"
if ! railway whoami >/dev/null 2>&1; then
  warn "Not logged in. Opening browser for Railway login…"
  railway login
fi

# ── ensure ANTHROPIC_API_KEY is available ────────────────────────────────────
ANTHROPIC_KEY="${ANTHROPIC_API_KEY:-}"

if [[ -z "$ANTHROPIC_KEY" && -f "$HOME/.env" ]]; then
  ANTHROPIC_KEY=$(grep "^ANTHROPIC_API_KEY=" "$HOME/.env" | cut -d= -f2- | tr -d '[:space:]')
fi

[[ -z "$ANTHROPIC_KEY" ]] && die "ANTHROPIC_API_KEY is not set. Export it or add it to \$HOME/.env"

info "API key found (${ANTHROPIC_KEY:0:14}…)"

# ── link or create Railway project ──────────────────────────────────────────
cd "$PYTHON_DIR"

info "Checking Railway project link…"
if ! railway status 2>/dev/null | grep -q "Project:"; then
  warn "No project linked. Creating a new Railway project…"
  railway init --name "multi-agent-backend"
fi

# ── deploy first (creates the service) ───────────────────────────────────────
info "Deploying backend to Railway…"
railway up --detach

# Wait a moment for the service to register
sleep 5

# ── set environment variables on Railway ─────────────────────────────────────
info "Setting environment variables on Railway…"
railway variables --set "ANTHROPIC_API_KEY=$ANTHROPIC_KEY"
railway variables --set "LLM_PROVIDER=anthropic"

# ── post-deploy ──────────────────────────────────────────────────────────────
info "Fetching deployment URL…"
BACKEND_URL=$(railway domain 2>/dev/null || true)

echo ""
echo -e "${GREEN}✓ Backend deployed!${NC}"
if [[ -n "$BACKEND_URL" ]]; then
  echo -e "  URL      : https://${BACKEND_URL}"
  echo -e "  Health   : https://${BACKEND_URL}/health"
  echo -e "  API docs : https://${BACKEND_URL}/docs"
  echo ""
  echo -e "${YELLOW}Next step:${NC} set this in the frontend deploy:"
  echo -e "  VITE_API_URL=https://${BACKEND_URL}"
else
  echo -e "  Run ${YELLOW}railway domain${NC} inside python/ to get your URL."
fi
echo ""

# ── smoke test (optional — only if curl is available) ────────────────────────
if [[ -n "$BACKEND_URL" ]] && command -v curl >/dev/null 2>&1; then
  info "Running health check against deployed backend…"
  sleep 5  # give Railway a moment to boot
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" "https://${BACKEND_URL}/health" || true)
  if [[ "$HTTP" == "200" ]]; then
    info "Health check passed (HTTP 200) ✓"
  else
    warn "Health check returned HTTP $HTTP — the service may still be starting."
  fi
fi
