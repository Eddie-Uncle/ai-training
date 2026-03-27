#!/usr/bin/env bash
# deploy_vercel.sh — deploy the AI Code Review Bot frontend to Vercel
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# ── colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[vercel]${NC} $*"; }
warn() { echo -e "${YELLOW}[vercel]${NC} $*"; }
die()  { echo -e "${RED}[vercel] ERROR:${NC} $*" >&2; exit 1; }

# ── preflight ─────────────────────────────────────────────────────────────────
command -v vercel >/dev/null 2>&1 || die "Vercel CLI not found. Install: npm i -g vercel"
command -v npm    >/dev/null 2>&1 || die "npm not found"

info "Checking Vercel authentication…"
if ! vercel whoami >/dev/null 2>&1; then
  warn "Not logged in — opening browser for Vercel login…"
  vercel login
fi

# ── resolve VITE_API_URL ──────────────────────────────────────────────────────
VITE_API_URL="${VITE_API_URL:-}"

# Try frontend/.env
if [[ -z "$VITE_API_URL" && -f "$FRONTEND_DIR/.env" ]]; then
  VITE_API_URL=$(grep "^VITE_API_URL=" "$FRONTEND_DIR/.env" | cut -d= -f2- | tr -d '[:space:]' || true)
fi

# Try to pull from Railway CLI if available
if [[ -z "$VITE_API_URL" ]] && command -v railway >/dev/null 2>&1; then
  RAILWAY_DOMAIN=$(cd "$SCRIPT_DIR/python" && railway domain 2>/dev/null | tr -d '[:space:]' || true)
  [[ -n "$RAILWAY_DOMAIN" ]] && VITE_API_URL="https://${RAILWAY_DOMAIN}"
fi

if [[ -z "$VITE_API_URL" ]]; then
  warn "VITE_API_URL is not set."
  read -rp "Enter your Railway backend URL (e.g. https://code-review-bot.railway.app): " VITE_API_URL
  [[ -z "$VITE_API_URL" ]] && die "Backend URL is required. Run deploy_railway.sh first."
fi

info "Backend URL: $VITE_API_URL"

# ── write frontend .env ───────────────────────────────────────────────────────
echo "VITE_API_URL=$VITE_API_URL" > "$FRONTEND_DIR/.env"
info "Wrote VITE_API_URL to frontend/.env"

# ── install & build ───────────────────────────────────────────────────────────
cd "$FRONTEND_DIR"

info "Installing npm dependencies…"
npm install --silent

info "Building for production…"
npm run build

# ── deploy to Vercel ──────────────────────────────────────────────────────────
info "Deploying to Vercel…"

VERCEL_OUTPUT=$(vercel --prod --yes --name "code-review-bot-ui" \
  --env "VITE_API_URL=$VITE_API_URL" \
  --build-env "VITE_API_URL=$VITE_API_URL" 2>&1)

echo "$VERCEL_OUTPUT"

FRONTEND_URL=$(echo "$VERCEL_OUTPUT" | grep -Eo 'https://[^ ]+\.vercel\.app' | tail -1 || true)

echo ""
echo -e "${GREEN}✓ Frontend deployed!${NC}"
if [[ -n "$FRONTEND_URL" ]]; then
  echo -e "  URL : $FRONTEND_URL"
  echo ""
  echo -e "${YELLOW}Optional:${NC} restrict CORS on Railway to this origin:"
  echo -e "  cd python && railway variables --set \"ALLOWED_ORIGINS=$FRONTEND_URL\""
fi
echo ""

# ── smoke test ────────────────────────────────────────────────────────────────
if [[ -n "$FRONTEND_URL" ]] && command -v curl >/dev/null 2>&1; then
  info "Running frontend smoke test…"
  sleep 4
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" || true)
  if [[ "$HTTP" == "200" ]]; then
    info "Frontend reachable (HTTP 200) ✓"
  else
    warn "Got HTTP $HTTP — the deployment may still be propagating."
  fi
fi
