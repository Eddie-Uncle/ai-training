# Code Analyzer API - Testing Guide

This guide covers how to test all API endpoints locally and in production (Railway).

## Quick Start

### 1. Start Local Server

```bash
cd python
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

### 2. Run All Tests

**Test locally:**
```bash
./test_api.sh
```

**Test Railway production:**
```bash
./test_api.sh https://code-analyzer-agent-production.up.railway.app
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check and provider info |
| `/analyze` | POST | General code analysis |
| `/analyze/security` | POST | Security-focused analysis |
| `/analyze/performance` | POST | Performance-focused analysis |

---

## Manual Testing

### Test 1: Health Check

**Request:**
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "provider": "google"
}
```

**What to Look For:**
- ✅ Status 200
- ✅ Returns `"status": "healthy"`
- ✅ Shows correct provider (google/openai/anthropic)

---

### Test 2: General Code Analysis

**Request:**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def calculate_total(items):\n    total = 0\n    for i in range(len(items)):\n        total += items[i]\n    return total",
    "language": "python"
  }' | python -m json.tool
```

**Expected Response Structure:**
```json
{
  "summary": "Analysis of the code...",
  "issues": [
    {
      "severity": "medium",
      "line": 3,
      "category": "style",
      "description": "Using range(len()) is not Pythonic...",
      "suggestion": "Use enumerate() or iterate directly..."
    }
  ],
  "suggestions": [
    "Add type hints to function parameters",
    "Add docstring to document function purpose"
  ],
  "metrics": {
    "complexity": "low",
    "readability": "good",
    "test_coverage_estimate": "good"
  }
}
```

**What to Look For:**
- ✅ Status 200
- ✅ Contains `summary`, `issues`, `suggestions`, `metrics`
- ✅ Issues have severity levels (critical/high/medium/low)
- ✅ Suggestions are actionable

---

### Test 3: Security-Focused Analysis

**Request:**
```bash
curl -X POST http://localhost:8000/analyze/security \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import os\npassword = \"admin123\"\nquery = \"SELECT * FROM users WHERE id = \" + user_id\neval(user_code)",
    "language": "python"
  }' | python -m json.tool
```

**Expected Issues:**
- 🔴 **Critical**: Hardcoded password
- 🔴 **Critical**: SQL injection vulnerability
- 🔴 **Critical**: Arbitrary code execution via `eval()`

**What to Look For:**
- ✅ Detects all 3 critical security vulnerabilities
- ✅ Provides specific line numbers
- ✅ Suggests secure alternatives (environment variables, parameterized queries, `ast.literal_eval()`)

---

### Test 4: Performance-Focused Analysis

**Request:**
```bash
curl -X POST http://localhost:8000/analyze/performance \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def find_duplicates(arr):\n    duplicates = []\n    for i in range(len(arr)):\n        for j in range(len(arr)):\n            if i != j and arr[i] == arr[j] and arr[i] not in duplicates:\n                duplicates.append(arr[i])\n    return duplicates",
    "language": "python"
  }' | python -m json.tool
```

**Expected Issues:**
- 🟠 **High**: O(n²) nested loops
- 🟠 **High**: O(n³) worst-case complexity with `arr[i] not in duplicates`
- 🟡 **Medium**: Redundant iterations

**What to Look For:**
- ✅ Identifies O(n²) or O(n³) complexity
- ✅ Suggests O(n) solution using sets
- ✅ Metrics show `"complexity": "high"`

---

## Automated Testing with `test_api.sh`

The `test_api.sh` script tests all 4 endpoints automatically.

### Usage

**Local Testing:**
```bash
./test_api.sh
```

**Production Testing:**
```bash
./test_api.sh https://code-analyzer-agent-production.up.railway.app
```

### What It Tests

1. **Health Check** - Verifies server is running
2. **General Analysis** - Tests code analysis with style issues
3. **Security Analysis** - Tests with vulnerable code (SQL injection, hardcoded secrets)
4. **Performance Analysis** - Tests with O(n²) nested loops

### Expected Output

```
════════════════════════════════════════════════════════════════════════════════
🧪 CODE ANALYZER API - ENDPOINT TESTING
════════════════════════════════════════════════════════════════════════════════
🔗 Testing: http://localhost:8000

────────────────────────────────────────────────────────────────────────────────
TEST 1: Health Check (GET /health)
────────────────────────────────────────────────────────────────────────────────
✅ PASSED
Response: {"status":"healthy","provider":"google"}

────────────────────────────────────────────────────────────────────────────────
TEST 2: General Code Analysis (POST /analyze)
────────────────────────────────────────────────────────────────────────────────
Testing with Python function that has style issues...
✅ PASSED
Issues Found: 2

────────────────────────────────────────────────────────────────────────────────
TEST 3: Security Analysis (POST /analyze/security)
────────────────────────────────────────────────────────────────────────────────
Testing with vulnerable code (SQL injection, hardcoded password)...
✅ PASSED
Critical/High Security Issues: 2

────────────────────────────────────────────────────────────────────────────────
TEST 4: Performance Analysis (POST /analyze/performance)
────────────────────────────────────────────────────────────────────────────────
Testing with O(n²) nested loop code...
✅ PASSED
Complexity Rating: HIGH

════════════════════════════════════════════════════════════════════════════════
📊 TEST SUMMARY
════════════════════════════════════════════════════════════════════════════════
✅ Passed: 4/4
❌ Failed: 0/4

🎉 ALL TESTS PASSED!
```

---

## Request/Response Schemas

### Request Schema (for POST endpoints)

```json
{
  "code": "string (required)",
  "language": "string (optional, default: python)"
}
```

### Response Schema (for all analysis endpoints)

```json
{
  "summary": "string - Overall analysis summary",
  "issues": [
    {
      "severity": "critical | high | medium | low",
      "line": "number | null",
      "category": "bug | security | performance | style | maintainability",
      "description": "string - What the issue is",
      "suggestion": "string - How to fix it"
    }
  ],
  "suggestions": [
    "string - General improvement suggestions"
  ],
  "metrics": {
    "complexity": "low | medium | high",
    "readability": "poor | fair | good | excellent",
    "test_coverage_estimate": "none | partial | good"
  }
}
```

---

## Common Testing Scenarios

### Scenario 1: Testing Security Fixes

**Before (Vulnerable):**
```python
password = "admin123"
query = "SELECT * FROM users WHERE id = " + user_id
```

**After (Fixed):**
```python
import os
password = os.getenv("PASSWORD")
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```

**Test both versions** to verify the API detects vulnerabilities in the first and approves the second.

---

### Scenario 2: Testing Performance Improvements

**Before (O(n²)):**
```python
for i in range(len(arr)):
    for j in range(len(arr)):
        if arr[i] == arr[j]:
            print(arr[i])
```

**After (O(n)):**
```python
seen = set()
for item in arr:
    if item in seen:
        print(item)
    seen.add(item)
```

**Test both versions** to compare complexity ratings.

---

## Troubleshooting Tests

### Issue: Connection Refused

**Cause:** Server not running

**Solution:**
```bash
# Start the server first
cd python
source venv/bin/activate
uvicorn main:app --reload
```

---

### Issue: 500 Internal Server Error

**Cause:** Invalid JSON or missing API key

**Solution:**
- Check JSON syntax (use online JSON validator)
- Verify `.env` file has `GOOGLE_API_KEY` set
- Check server logs for detailed error

---

### Issue: 429 Rate Limit Exceeded

**Cause:** Hit API rate limits (Google free tier: ~20 requests/day)

**Solution:**
- Wait for quota to reset
- Use different API key
- Upgrade to paid tier
- Switch to different provider (OpenAI, Anthropic)

---

### Issue: Tests Pass Locally but Fail on Railway

**Possible Causes:**
1. Environment variables not set in Railway
2. Different Python version
3. Rate limits hit

**Solution:**
```bash
# Check Railway environment
railway variables

# Set missing variables
railway variables set GOOGLE_API_KEY=your-key
railway variables set LLM_PROVIDER=google

# Check logs
railway logs
```

---

## Testing Different LLM Providers

The API supports multiple LLM providers. Test with each:

### Google Gemini (Current)
```bash
# .env
GOOGLE_API_KEY=your-key
LLM_PROVIDER=google
```

### OpenAI
```bash
# .env
OPENAI_API_KEY=your-key
LLM_PROVIDER=openai
```

### Anthropic Claude
```bash
# .env
ANTHROPIC_API_KEY=your-key
LLM_PROVIDER=anthropic
```

**After changing providers**, restart the server and run tests again.

---

## Best Practices

### 1. Test After Every Change
```bash
# Make code change
# Restart server (if not using --reload)
./test_api.sh
```

### 2. Test Multiple Code Samples
- Simple functions (sanity check)
- Complex nested logic (performance)
- Security vulnerabilities (security)
- Edge cases (empty code, very long code)

### 3. Verify All Severity Levels
Make sure the API can detect:
- 🔴 Critical issues (security holes, major bugs)
- 🟠 High issues (performance problems, security risks)
- 🟡 Medium issues (code smells)
- 🟢 Low issues (style suggestions)

### 4. Check Both Local and Production
```bash
# Local
./test_api.sh

# Production
./test_api.sh https://your-app.railway.app
```

---

## Advanced Testing

### Load Testing
```bash
# Test with multiple concurrent requests
for i in {1..10}; do
  curl -X POST http://localhost:8000/analyze \
    -H "Content-Type: application/json" \
    -d '{"code":"def test(): pass","language":"python"}' &
done
wait
```

### Testing Error Handling
```bash
# Test with invalid JSON
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{invalid json}'

# Test with missing field
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"language":"python"}'

# Test with empty code
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"code":"","language":"python"}'
```

---

## Integration with CI/CD

Add testing to your deployment pipeline:

```yaml
# Example GitHub Actions workflow
name: Test API
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          cd python
          pip install -r requirements.txt
      - name: Start server
        run: |
          cd python
          uvicorn main:app --reload &
          sleep 5
      - name: Run tests
        run: |
          cd python
          ./test_api.sh
```

---

## Summary

✅ **Use `./test_api.sh`** for quick automated testing

✅ **Test locally first** before deploying

✅ **Verify all 4 endpoints** work correctly

✅ **Check rate limits** when testing frequently

✅ **Test with realistic code samples** that match your use cases

For deployment instructions, see [README.md](../README.md).
