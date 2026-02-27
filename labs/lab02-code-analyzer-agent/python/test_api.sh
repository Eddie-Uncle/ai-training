#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Code Analyzer API Test Script
# Tests all 4 endpoints: health, analyze, security, performance
# =============================================================================

# Default to localhost, or pass Railway URL as argument
BASE_URL="${1:-http://localhost:8000}"
TIMEOUT=30

echo "════════════════════════════════════════════════════════════════════════════════"
echo "🧪 CODE ANALYZER API - ENDPOINT TESTING"
echo "════════════════════════════════════════════════════════════════════════════════"
echo "🔗 Testing: ${BASE_URL}"
echo ""

pass_count=0
fail_count=0

# Function to check if response has expected structure
check_analysis_structure() {
    local body="$1"
    if echo "$body" | grep -q '"summary"' && \
       echo "$body" | grep -q '"issues"' && \
       echo "$body" | grep -q '"suggestions"' && \
       echo "$body" | grep -q '"metrics"'; then
        return 0
    else
        return 1
    fi
}

# Test 1: Health Check
echo "────────────────────────────────────────────────────────────────────────────────"
echo "TEST 1: Health Check (GET /health)"
echo "────────────────────────────────────────────────────────────────────────────────"

health_response=$(curl -s --max-time $TIMEOUT "${BASE_URL}/health" 2>&1)
if echo "$health_response" | grep -q '"status"'; then
    echo "✅ PASSED"
    echo "Response: $health_response"
    ((pass_count++))
else
    echo "❌ FAILED"
    echo "Response: $health_response"
    ((fail_count++))
fi

# Test 2: General Code Analysis
echo ""
echo "────────────────────────────────────────────────────────────────────────────────"
echo "TEST 2: General Code Analysis (POST /analyze)"
echo "────────────────────────────────────────────────────────────────────────────────"
echo "Testing with Python function that has style issues..."

analyze_response=$(curl -s --max-time $TIMEOUT -X POST "${BASE_URL}/analyze" \
  -H "Content-Type: application/json" \
  -d '{"code":"def process(items):\n    result=[]\n    for i in range(len(items)):\n        result.append(items[i]*2)\n    return result","language":"python"}' 2>&1)

if check_analysis_structure "$analyze_response"; then
    echo "✅ PASSED"
    if command -v python >/dev/null 2>&1; then
        issue_count=$(echo "$analyze_response" | python -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('issues', [])))" 2>/dev/null || echo "?")
        echo "Issues Found: $issue_count"
    fi
    ((pass_count++))
else
    echo "❌ FAILED"
    echo "Response: ${analyze_response:0:300}"
    ((fail_count++))
fi

# Test 3: Security Analysis
echo ""
echo "────────────────────────────────────────────────────────────────────────────────"
echo "TEST 3: Security Analysis (POST /analyze/security)"
echo "────────────────────────────────────────────────────────────────────────────────"
echo "Testing with vulnerable code (SQL injection, hardcoded password)..."

security_response=$(curl -s --max-time $TIMEOUT -X POST "${BASE_URL}/analyze/security" \
  -H "Content-Type: application/json" \
  -d '{"code":"import os\npassword=\"admin123\"\nquery=\"SELECT * FROM users WHERE id=\"+str(user_id)","language":"python"}' 2>&1)

if check_analysis_structure "$security_response"; then
    echo "✅ PASSED"
    if command -v python >/dev/null 2>&1; then
        critical_count=$(echo "$security_response" | python -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for i in data.get('issues', []) if i.get('severity') in ['critical', 'high']))" 2>/dev/null || echo "?")
        echo "Critical/High Security Issues: $critical_count"
    fi
    ((pass_count++))
else
    echo "❌ FAILED"
    echo "Response: ${security_response:0:300}"
    ((fail_count++))
fi

# Test 4: Performance Analysis
echo ""
echo "────────────────────────────────────────────────────────────────────────────────"
echo "TEST 4: Performance Analysis (POST /analyze/performance)"
echo "────────────────────────────────────────────────────────────────────────────────"
echo "Testing with O(n²) nested loop code..."

performance_response=$(curl -s --max-time $TIMEOUT -X POST "${BASE_URL}/analyze/performance" \
  -H "Content-Type: application/json" \
  -d '{"code":"def find_pairs(arr):\n    pairs=[]\n    for i in range(len(arr)):\n        for j in range(len(arr)):\n            if i!=j: pairs.append((arr[i],arr[j]))\n    return pairs","language":"python"}' 2>&1)

if check_analysis_structure "$performance_response"; then
    echo "✅ PASSED"
    if command -v python >/dev/null 2>&1; then
        complexity=$(echo "$performance_response" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('metrics', {}).get('complexity', 'unknown').upper())" 2>/dev/null || echo "?")
        echo "Complexity Rating: $complexity"
    fi
    ((pass_count++))
else
    echo "❌ FAILED"
    echo "Response: ${performance_response:0:300}"
    ((fail_count++))
fi

# Summary
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "📊 TEST SUMMARY"
echo "════════════════════════════════════════════════════════════════════════════════"
echo "✅ Passed: ${pass_count}/4"
echo "❌ Failed: ${fail_count}/4"
echo ""

if [[ $fail_count -gt 0 ]]; then
    echo "⚠️  Some tests failed"
    echo ""
    echo "💡 Common Issues:"
    echo "   - Check if server is running (for localhost)"
    echo "   - Check API rate limits (for Railway)"
    echo "   - Verify LLM_PROVIDER and API key are set"
    exit 1
else
    echo "🎉 ALL TESTS PASSED!"
    echo ""
    echo "📋 Available Endpoints:"
    echo "   GET  ${BASE_URL}/health"
    echo "   POST ${BASE_URL}/analyze"
    echo "   POST ${BASE_URL}/analyze/security"
    echo "   POST ${BASE_URL}/analyze/performance"
fi

echo "════════════════════════════════════════════════════════════════════════════════"
