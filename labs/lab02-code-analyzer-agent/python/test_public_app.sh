#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-https://code-analyzer-agent-production.up.railway.app}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-30}"

if ! command -v curl >/dev/null 2>&1; then
  echo "❌ curl is required but not installed."
  exit 1
fi

JSON_PRETTY=""
if command -v python >/dev/null 2>&1; then
  JSON_PRETTY="python -m json.tool"
elif command -v python3 >/dev/null 2>&1; then
  JSON_PRETTY="python3 -m json.tool"
fi

pass_count=0
fail_count=0

print_result() {
  local name="$1"
  local ok="$2"
  local detail="$3"

  if [[ "$ok" == "true" ]]; then
    echo "✅ PASS: ${name}"
    ((pass_count+=1))
  else
    echo "❌ FAIL: ${name}"
    echo "   ${detail}"
    ((fail_count+=1))
  fi
}

call_endpoint() {
  local method="$1"
  local path="$2"
  local data="$3"

  local url="${BASE_URL}${path}"
  local body_file
  body_file="$(mktemp)"
  local http_code

  if [[ -n "$data" ]]; then
    http_code=$(curl -sS --max-time "$TIMEOUT_SECONDS" -o "$body_file" -w "%{http_code}" -X "$method" "$url" \
      -H "Content-Type: application/json" \
      -d "$data")
  else
    http_code=$(curl -sS --max-time "$TIMEOUT_SECONDS" -o "$body_file" -w "%{http_code}" -X "$method" "$url")
  fi

  local body
  body="$(cat "$body_file")"
  rm -f "$body_file"

  REPLY_HTTP_CODE="$http_code"
  REPLY_BODY="$body"
}

check_has_analysis_shape() {
  local body="$1"
  if command -v python >/dev/null 2>&1; then
    python - "$body" <<'PY' >/dev/null 2>&1
import json, sys
try:
    data = json.loads(sys.argv[1])
    assert isinstance(data.get("summary"), str)
    assert isinstance(data.get("issues"), list)
    assert isinstance(data.get("suggestions"), list)
    assert isinstance(data.get("metrics"), dict)
except Exception:
    raise SystemExit(1)
PY
  elif command -v python3 >/dev/null 2>&1; then
    python3 - "$body" <<'PY' >/dev/null 2>&1
import json, sys
try:
    data = json.loads(sys.argv[1])
    assert isinstance(data.get("summary"), str)
    assert isinstance(data.get("issues"), list)
    assert isinstance(data.get("suggestions"), list)
    assert isinstance(data.get("metrics"), dict)
except Exception:
    raise SystemExit(1)
PY
  else
    echo "$body" | grep -q '"summary"' && \
    echo "$body" | grep -q '"issues"' && \
    echo "$body" | grep -q '"suggestions"' && \
    echo "$body" | grep -q '"metrics"'
  fi
}

echo "🔎 Testing public app: ${BASE_URL}"
echo ""

# 1) Health
call_endpoint "GET" "/health" ""
if [[ "$REPLY_HTTP_CODE" == "200" ]] && echo "$REPLY_BODY" | grep -q '"status"'; then
  print_result "GET /health" true ""
else
  print_result "GET /health" false "HTTP ${REPLY_HTTP_CODE} body=${REPLY_BODY}"
fi

# 2) General analysis
general_payload='{"code":"def add(a,b):\n    return a+b","language":"python"}'
call_endpoint "POST" "/analyze" "$general_payload"
if [[ "$REPLY_HTTP_CODE" == "200" ]] && check_has_analysis_shape "$REPLY_BODY"; then
  print_result "POST /analyze" true ""
else
  print_result "POST /analyze" false "HTTP ${REPLY_HTTP_CODE} body=${REPLY_BODY}"
fi

# 3) Security analysis
security_payload='{"code":"query = f\"SELECT * FROM users WHERE name = '\''{user}'\''\"","language":"python"}'
call_endpoint "POST" "/analyze/security" "$security_payload"
if [[ "$REPLY_HTTP_CODE" == "200" ]] && check_has_analysis_shape "$REPLY_BODY"; then
  print_result "POST /analyze/security" true ""
else
  print_result "POST /analyze/security" false "HTTP ${REPLY_HTTP_CODE} body=${REPLY_BODY}"
fi

# 4) Performance analysis
performance_payload='{"code":"for i in range(n):\n    for j in range(n):\n        pass","language":"python"}'
call_endpoint "POST" "/analyze/performance" "$performance_payload"
if [[ "$REPLY_HTTP_CODE" == "200" ]] && check_has_analysis_shape "$REPLY_BODY"; then
  print_result "POST /analyze/performance" true ""
else
  print_result "POST /analyze/performance" false "HTTP ${REPLY_HTTP_CODE} body=${REPLY_BODY}"
fi

echo ""
echo "📊 Summary: ${pass_count} passed, ${fail_count} failed"

if [[ "$fail_count" -gt 0 ]]; then
  exit 1
fi

echo "🎉 All checks passed"
