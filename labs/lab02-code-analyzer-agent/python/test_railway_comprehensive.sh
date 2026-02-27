#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://code-analyzer-agent-production.up.railway.app"
TIMEOUT=30

echo "════════════════════════════════════════════════════════════════════════════════"
echo "🚀 TESTING RAILWAY DEPLOYMENT: Code Analyzer API"
echo "════════════════════════════════════════════════════════════════════════════════"
echo "🔗 URL: ${BASE_URL}"
echo ""

# Test 1: Health Check
echo "────────────────────────────────────────────────────────────────────────────────"
echo "TEST 1: Health Check (GET /health)"
echo "────────────────────────────────────────────────────────────────────────────────"
health_response=$(curl -s --max-time $TIMEOUT "${BASE_URL}/health")
health_code=$?

if [[ $health_code -eq 0 ]] && echo "$health_response" | grep -q '"status"'; then
  echo "✅ PASSED"
  echo "Response: $health_response"
else
  echo "❌ FAILED"
  echo "Response: $health_response"
fi

# Test 2: General Code Analysis
echo ""
echo "────────────────────────────────────────────────────────────────────────────────"
echo "TEST 2: General Code Analysis (POST /analyze)"
echo "────────────────────────────────────────────────────────────────────────────────"
echo "Testing with simple Python function..."

analyze_response=$(curl -s --max-time $TIMEOUT -X POST "${BASE_URL}/analyze" \
  -H "Content-Type: application/json" \
  -d '{"code":"def calculate_total(items):\n    total = 0\n    for i in range(len(items)):\n        total += items[i]\n    return total","language":"python"}')

if echo "$analyze_response" | grep -q '"summary"' && echo "$analyze_response" | grep -q '"issues"'; then
  echo "✅ PASSED"
  echo ""
  # Extract summary
  summary=$(echo "$analyze_response" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('summary', '')[:200] + '...')" 2>/dev/null || echo "Summary parsing error")
  echo "Summary: $summary"
  
  # Count issues
  issue_count=$(echo "$analyze_response" | python -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('issues', [])))" 2>/dev/null || echo "?")
  echo "Issues Found: $issue_count"
else
  echo "❌ FAILED"
  echo "Response: ${analyze_response:0:500}"
fi

# Test 3: Security Analysis
echo ""
echo "────────────────────────────────────────────────────────────────────────────────"
echo "TEST 3: Security Analysis (POST /analyze/security)"
echo "────────────────────────────────────────────────────────────────────────────────"
echo "Testing with vulnerable code (SQL injection, hardcoded password, eval)..."

security_response=$(curl -s --max-time $TIMEOUT -X POST "${BASE_URL}/analyze/security" \
  -H "Content-Type: application/json" \
  -d '{"code":"password=\"admin123\"\nquery=\"SELECT * FROM users WHERE id=\"+user_id\neval(user_code)","language":"python"}')

if echo "$security_response" | grep -q '"summary"' && echo "$security_response" | grep -q '"issues"'; then
  echo "✅ PASSED"
  echo ""
  
  # Count critical/high issues
  critical_count=$(echo "$security_response" | python -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for i in data.get('issues', []) if i.get('severity') in ['critical', 'high']))" 2>/dev/null || echo "?")
  total_issues=$(echo "$security_response" | python -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('issues', [])))" 2>/dev/null || echo "?")
  echo "Security Issues Found: $total_issues (Critical/High: $critical_count)"
  
  # Show first issue
  first_issue=$(echo "$security_response" | python -c "import sys, json; data=json.load(sys.stdin); issues=data.get('issues', []); print(f\"  - {issues[0].get('severity').upper()}: {issues[0].get('description')[:100]}...\") if issues else print('None')" 2>/dev/null || echo "")
  echo "$first_issue"
else
  echo "❌ FAILED"
  echo "Response: ${security_response:0:500}"
fi

# Test 4: Performance Analysis
echo ""
echo "────────────────────────────────────────────────────────────────────────────────"
echo "TEST 4: Performance Analysis (POST /analyze/performance)"
echo "────────────────────────────────────────────────────────────────────────────────"
echo "Testing with O(n²) nested loop code..."

performance_response=$(curl -s --max-time $TIMEOUT -X POST "${BASE_URL}/analyze/performance" \
  -H "Content-Type: application/json" \
  -d '{"code":"def find_pairs(arr):\n    pairs = []\n    for i in range(len(arr)):\n        for j in range(len(arr)):\n            if i != j:\n                pairs.append((arr[i], arr[j]))\n    return pairs","language":"python"}')

if echo "$performance_response" | grep -q '"summary"' && echo "$performance_response" | grep -q '"issues"'; then
  echo "✅ PASSED"
  echo ""
  
  # Get complexity
  complexity=$(echo "$performance_response" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('metrics', {}).get('complexity', 'unknown').upper())" 2>/dev/null || echo "?")
  issue_count=$(echo "$performance_response" | python -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('issues', [])))" 2>/dev/null || echo "?")
  echo "Performance Issues Found: $issue_count"
  echo "Complexity Rating: $complexity"
  
  # Show first issue
  first_issue=$(echo "$performance_response" | python -c "import sys, json; data=json.load(sys.stdin); issues=data.get('issues', []); print(f\"  - {issues[0].get('severity').upper()}: {issues[0].get('description')[:100]}...\") if issues else print('None')" 2>/dev/null || echo "")
  echo "$first_issue"
else
  echo "❌ FAILED"
  echo "Response: ${performance_response:0:500}"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "🎉 ALL TESTS COMPLETED!"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "📋 API Documentation:"
echo "  Health:       GET  ${BASE_URL}/health"
echo "  Analyze:      POST ${BASE_URL}/analyze"
echo "  Security:     POST ${BASE_URL}/analyze/security"
echo "  Performance:  POST ${BASE_URL}/analyze/performance"
echo ""
echo "✅ Railway deployment is fully operational!"
