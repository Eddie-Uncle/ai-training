#!/usr/bin/env bash
# deploy-frontend.sh — Deploy the Next.js frontend to Vercel
# Run from: ai-training/labs/lab04-rag-system/frontend/
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[info]${NC}  $*"; }
success() { echo -e "${GREEN}[ok]${NC}    $*"; }
die()     { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── 1. Pre-flight ──────────────────────────────────────────────────────────
info "Checking prerequisites…"
command -v vercel >/dev/null 2>&1 || die "Vercel CLI not found. Install: npm i -g vercel"
command -v npm    >/dev/null 2>&1 || die "npm not found."

# ── 2. Install dependencies ────────────────────────────────────────────────
info "Installing npm dependencies…"
npm install --silent
success "Dependencies installed."

# ── 3. Set the Railway API URL ─────────────────────────────────────────────
API_URL="${NEXT_PUBLIC_API_URL:-https://api-production-7a05.up.railway.app}"
info "Backend API URL: $API_URL"

# ── 4. Deploy to Vercel ────────────────────────────────────────────────────
info "Deploying to Vercel (production)…"
vercel deploy --prod \
  --build-env NEXT_PUBLIC_API_URL="$API_URL" \
  --env       NEXT_PUBLIC_API_URL="$API_URL" \
  --yes

success "Frontend deployed!"
echo ""
echo "  Dashboard:  vercel --cwd . inspect"
echo "  Logs:       vercel logs"
echo "  Redeploy:   vercel deploy --prod --yes"
