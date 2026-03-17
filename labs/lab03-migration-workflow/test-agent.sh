#!/usr/bin/env bash
# test-agent.sh — Lab 03 Migration Workflow Agent test runner
# Usage: bash test-agent.sh [--url http://localhost:8003]

set -euo pipefail

BASE_URL="${1:-http://localhost:8003}"
PASS=0
FAIL=0

# ── helpers ────────────────────────────────────────────────────────────────────

green()  { printf "\033[0;32m%s\033[0m\n" "$*"; }
red()    { printf "\033[0;31m%s\033[0m\n" "$*"; }
yellow() { printf "\033[0;33m%s\033[0m\n" "$*"; }
header() { printf "\n\033[1;34m══ %s ══\033[0m\n" "$*"; }

pass() { green "  ✓ $*"; ((PASS++)) || true; }
fail() { red   "  ✗ $*"; ((FAIL++)) || true; }

check_field() {
  local label="$1" json="$2" field="$3" expected="$4"
  local actual
  actual=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d$field)" 2>/dev/null || echo "__error__")
  if [[ "$actual" == "$expected" ]]; then
    pass "$label"
  else
    fail "$label (got: $actual)"
  fi
}

check_contains() {
  local label="$1" json="$2" needle="$3"
  if echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$needle' in str(d)" 2>/dev/null; then
    pass "$label"
  else
    fail "$label (\"$needle\" not found)"
  fi
}

check_truthy() {
  local label="$1" json="$2" field="$3"
  local actual
  actual=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); v=d$field; print(bool(v))" 2>/dev/null || echo "False")
  if [[ "$actual" == "True" ]]; then
    pass "$label"
  else
    fail "$label"
  fi
}

# ── wait for server ─────────────────────────────────────────────────────────────

header "Waiting for server at $BASE_URL"
for i in {1..10}; do
  if curl -sf "$BASE_URL/health" > /dev/null 2>&1; then
    green "  Server is up"
    break
  fi
  if [[ $i -eq 10 ]]; then
    red "  Server not reachable after 10s. Start it first:"
    echo "    cd python && source \$HOME/.venv/bin/activate && uvicorn main:app --reload --port 8003"
    exit 1
  fi
  sleep 1
done

# ── TEST 1: Health ──────────────────────────────────────────────────────────────

header "Test 1: Health check"
RESP=$(curl -sf "$BASE_URL/health")
echo "  $RESP"
check_field "status is healthy"  "$RESP" "['status']"   "healthy"
check_field "provider is set"    "$RESP" "['provider']"  "anthropic"

# ── TEST 2: Frameworks ──────────────────────────────────────────────────────────

header "Test 2: List supported frameworks"
RESP=$(curl -sf "$BASE_URL/frameworks")
echo "  $RESP" | python3 -m json.tool 2>/dev/null | head -6
check_contains "express listed"  "$RESP" "express"
check_contains "fastapi listed"  "$RESP" "fastapi"

# ── TEST 3: Express → FastAPI single file ──────────────────────────────────────

header "Test 3: Express → FastAPI (single route)"
RESP=$(curl -sf -X POST "$BASE_URL/migrate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_framework": "express",
    "target_framework": "fastapi",
    "files": {
      "routes/users.js": "const express = require(\"express\");\nconst router = express.Router();\nrouter.get(\"/users\", async (req, res) => {\n    const users = await db.getUsers();\n    res.json(users);\n});\nmodule.exports = router;"
    }
  }')
echo "$RESP" | python3 -m json.tool 2>/dev/null
check_field  "success is true"             "$RESP" "['success']"         "True"
check_truthy "migrated_files populated"    "$RESP" "['migrated_files']"
check_truthy "plan_executed populated"     "$RESP" "['plan_executed']"
check_field  "errors list is empty"        "$RESP" "['errors']"          "[]"
# Planning agent telemetry
ITERS=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['iterations_count'])" 2>/dev/null || echo 0)
TCELLS=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['tool_calls_count'])" 2>/dev/null || echo 0)
[[ "$ITERS" -gt 0 ]]  && pass "iterations_count > 0 (got $ITERS)"  || fail "iterations_count = 0"
[[ "$TCELLS" -ge 4 ]] && pass "tool_calls_count >= 4 (got $TCELLS)" || fail "tool_calls_count < 4 (got $TCELLS)"

# ── TEST 4: Express → FastAPI multi-file ──────────────────────────────────────

header "Test 4: Express → FastAPI (multi-file)"
RESP=$(curl -sf -X POST "$BASE_URL/migrate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_framework": "express",
    "target_framework": "fastapi",
    "files": {
      "routes/users.js": "const router = require(\"express\").Router();\nrouter.get(\"/users\", async (req, res) => { res.json(await db.getUsers()); });\nmodule.exports = router;",
      "routes/products.js": "const router = require(\"express\").Router();\nrouter.get(\"/products\", async (req, res) => { res.json(await db.getProducts()); });\nrouter.post(\"/products\", async (req, res) => { const p = await db.createProduct(req.body); res.status(201).json(p); });\nmodule.exports = router;"
    }
  }')
echo "$RESP" | python3 -m json.tool 2>/dev/null
check_field  "success is true"          "$RESP" "['success']"   "True"
check_truthy "migrated_files populated" "$RESP" "['migrated_files']"
check_field  "errors list is empty"     "$RESP" "['errors']"    "[]"

# ── TEST 5: Flask → FastAPI ────────────────────────────────────────────────────

header "Test 5: Flask → FastAPI"
RESP=$(curl -sf -X POST "$BASE_URL/migrate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_framework": "flask",
    "target_framework": "fastapi",
    "files": {
      "app.py": "from flask import Flask, jsonify\napp = Flask(__name__)\n\n@app.route(\"/items\", methods=[\"GET\"])\ndef get_items():\n    return jsonify([{\"id\": 1, \"name\": \"Item One\"}])\n\n@app.route(\"/items/<int:item_id>\", methods=[\"GET\"])\ndef get_item(item_id):\n    return jsonify({\"id\": item_id, \"name\": \"Item One\"})\n\nif __name__ == \"__main__\":\n    app.run(debug=True)"
    }
  }')
echo "$RESP" | python3 -m json.tool 2>/dev/null
check_field  "success is true"          "$RESP" "['success']"   "True"
check_truthy "migrated_files populated" "$RESP" "['migrated_files']"
check_field  "errors list is empty"     "$RESP" "['errors']"    "[]"

# ── TEST 6: Empty files → 422 ─────────────────────────────────────────────────

header "Test 6: Empty files payload → HTTP 422"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/migrate" \
  -H "Content-Type: application/json" \
  -d '{"source_framework":"express","target_framework":"fastapi","files":{}}')
echo "  HTTP $HTTP_CODE"
[[ "$HTTP_CODE" == "422" ]] && pass "returns 422 for empty files" || fail "expected 422, got $HTTP_CODE"

# ── TEST 7: SSE streaming endpoint ────────────────────────────────────────────

header "Test 7: SSE /migrate/stream"
STREAM=$(curl -sf --max-time 120 -X POST "$BASE_URL/migrate/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "source_framework": "express",
    "target_framework": "fastapi",
    "files": {
      "app.js": "const express = require(\"express\");\nconst app = express();\napp.get(\"/ping\", (req, res) => res.json({pong: true}));\napp.listen(3000);"
    }
  }' 2>/dev/null || echo "")
FINAL_LINE=$(echo "$STREAM" | grep '^data:' | tail -1 | sed 's/^data: //')
if [[ -n "$FINAL_LINE" ]]; then
  pass "SSE stream produced events"
  HAS_COMPLETE=$(echo "$FINAL_LINE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('phase',''))" 2>/dev/null || echo "")
  [[ "$HAS_COMPLETE" == "complete" ]] && pass "final event has phase=complete" || fail "final event phase: $HAS_COMPLETE"
else
  fail "SSE stream returned no events"
fi

# ── Summary ────────────────────────────────────────────────────────────────────

printf "\n\033[1m═══════════════════════════\033[0m\n"
printf "\033[1mResults: "
green "$PASS passed" | tr -d '\n'
printf "  "
if [[ $FAIL -gt 0 ]]; then
  red "$FAIL failed"
else
  green "0 failed"
fi
printf "\033[0m\n"

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
