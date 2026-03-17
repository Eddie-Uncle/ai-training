****# Lab 04 — RAG System: Testing Guide

## Prerequisites

```bash
# Must be set in ~/.env or exported
echo $ANTHROPIC_API_KEY   # for LLM generation & LLM-as-judge
echo $VOYAGE_API_KEY      # for voyage-code-2 embeddings
```

---

## Two testing targets

| Target | Base URL | When to use |
|--------|----------|-------------|
| **Local** | `http://localhost:8008` | Development / fast iteration |
| **Railway** | `https://api-production-7a05.up.railway.app` | Staging / final deliverable |

Set once, use everywhere:

```bash
# Local
export BASE_URL=http://localhost:8008

# Railway (deployed)
export BASE_URL=https://api-production-7a05.up.railway.app
```

---

## 1. Start the server (local only)

```bash
cd ai-training/labs/lab04-rag-system/python
source venv/bin/activate
uvicorn main:app --port 8008 --reload
```

---

## 2. Health check

```bash
curl -s $BASE_URL/health | python3 -m json.tool
```

**Expected:**
```json
{
    "status": "healthy",
    "provider": "anthropic"
}
```

---

## 3. Index files

### 3a. Index via JSON body

```bash
curl -s -X POST $BASE_URL/index/files \
  -H "Content-Type: application/json" \
  -d '{
    "files": {
      "auth.py": "def login(user, password):\n    \"\"\"Validate credentials and return token.\"\"\"\n    if not user or not password:\n        raise ValueError(\"Missing credentials\")\n    return \"token_xyz\"\n\ndef logout(token):\n    \"\"\"Invalidate a session token.\"\"\"\n    pass",
      "api.py": "def get_users():\n    \"\"\"Return all users from the database.\"\"\"\n    return db.query(User).all()\n\ndef create_user(name, email):\n    \"\"\"Create a new user record.\"\"\"\n    user = User(name=name, email=email)\n    db.session.add(user)\n    return user"
    }
  }' | python3 -m json.tool
```

**Expected:**
```json
{
    "indexed_chunks": 4,
    "files": ["auth.py", "api.py"]
}
```

### 3b. Index the lab04 codebase itself (local only)

```bash
# First, make sure the server is running locally
curl -s -X POST $BASE_URL/index/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/Users/eagle/code/ai-training/labs/lab04-rag-system/python",
    "extensions": [".py"]
  }' | python3 -m json.tool
```

**Expected:** `indexed_chunks` will be 40–60 depending on codebase state.

---

## 4. Check index stats

```bash
curl -s $BASE_URL/stats | python3 -m json.tool
```

**Expected:**
```json
{
    "count": 4,
    "name": "codebase"
}
```

---

## 5. Query the codebase

```bash
curl -s -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How does the login function validate credentials?",
    "n_results": 3
  }' | python3 -m json.tool
```

**Expected shape:**
```json
{
    "answer": "The login function checks ...",
    "sources": [
        {
            "file": "auth.py",
            "type": "function",
            "name": "login",
            "line": 1,
            "relevance": 0.73
        }
    ],
    "context_used": "--- File: auth.py | function: login | Line: 1 ---\n..."
}
```

**What to verify:**
- `answer` is grounded in the code context (not hallucinated)
- `sources[0].file` matches the file you'd expect
- `relevance` scores are > 0.5 for top results

### More test queries

```bash
# Test language filtering
curl -s -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How are users created?", "n_results": 3, "filter_language": "python"}' \
  | python3 -m json.tool

# Test a question with no good answer
curl -s -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How does the payment processing system work?", "n_results": 3}' \
  | python3 -m json.tool
# Expect: answer says "no relevant code found" or similar hedge
```

---

## 6. Evaluation

### 6a. Custom evaluation examples (POST /evaluate)

```bash
curl -s -X POST $BASE_URL/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "examples": [
      {
        "question": "How does the login function validate credentials?",
        "expected_answer": "The login function checks if user or password is empty, raises ValueError if missing, then returns a token.",
        "relevant_files": ["auth.py"]
      },
      {
        "question": "What does get_users return?",
        "expected_answer": "get_users queries the database and returns all User records.",
        "relevant_files": ["api.py"]
      }
    ]
  }' | python3 -m json.tool
```

**Expected shape:**
```json
{
    "retrieval": {
        "precision@5": 0.2,
        "recall@5": 1.0,
        "mrr": 1.0,
        "n_examples": 2
    },
    "generation": {
        "relevance": 0.9,
        "accuracy": 0.85,
        "n_examples": 2
    }
}
```

**What to verify:**
- `retrieval.mrr` > 0 means the relevant file was retrieved
- `retrieval.recall@5` = 1.0 means every relevant file was found
- `generation.relevance` > 0.6 means answers are on-topic
- `generation.accuracy` > 0.6 means answers match expected content

### 6b. Built-in 12-example dataset (POST /evaluate/default)

> **Requires:** the lab04 Python codebase indexed first (Step 3b)

```bash
# 1. Index the codebase
curl -s -X POST $BASE_URL/index/directory \
  -H "Content-Type: application/json" \
  -d '{"directory": "/Users/eagle/code/ai-training/labs/lab04-rag-system/python", "extensions": [".py"]}' \
  | python3 -m json.tool

# 2. Run the built-in eval dataset
curl -s -X POST $BASE_URL/evaluate/default | python3 -m json.tool
```

**Expected retrieval metrics (rough targets):**

| Metric | Target |
|--------|--------|
| `precision@5` | ≥ 0.20 |
| `recall@5` | ≥ 0.70 |
| `mrr` | ≥ 0.60 |

> **Note:** Voyage AI free tier is limited to **3 requests/min**. The 12-example eval makes ~24 embedding calls — it will take ~8 minutes to complete or fail fast with a rate limit error. Add a payment method at [dashboard.voyageai.com](https://dashboard.voyageai.com) to remove the cap.

---

## 7. Clear and re-index

```bash
# Clear the vector store
curl -s -X DELETE $BASE_URL/index | python3 -m json.tool
# Expected: {"status": "cleared"}

# Verify empty
curl -s $BASE_URL/stats | python3 -m json.tool
# Expected: {"count": 0, "name": "codebase"}
```

---

## 8. Full end-to-end test script

Save as `test_api.sh` and run from the `python/` directory:

```bash
#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://localhost:8008}"
echo "Testing against $BASE_URL"

echo -e "\n=== 1. Health ==="
curl -sf $BASE_URL/health

echo -e "\n\n=== 2. Clear index ==="
curl -sf -X DELETE $BASE_URL/index

echo -e "\n\n=== 3. Index files ==="
curl -sf -X POST $BASE_URL/index/files \
  -H "Content-Type: application/json" \
  -d '{"files":{"auth.py":"def login(user, password):\n    if not user or not password:\n        raise ValueError(\"x\")\n    return \"tok\"\n\ndef logout(token):\n    pass","api.py":"def get_users():\n    return db.query(User).all()"}}'

echo -e "\n\n=== 4. Stats ==="
curl -sf $BASE_URL/stats

echo -e "\n\n=== 5. Query ==="
curl -sf -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"question":"How does login work?","n_results":2}' | python3 -m json.tool

echo -e "\n\n=== All checks passed ==="
```

```bash
chmod +x test_api.sh
BASE_URL=http://localhost:8008 bash test_api.sh
# or against Railway:
BASE_URL=https://api-production-7a05.up.railway.app bash test_api.sh
```

---

## 9. Railway-specific checks

```bash
# View live deployment logs
railway logs

# View build logs from last deploy
railway logs --build

# Check service status
railway status

# Redeploy (e.g. after env var change)
railway redeploy
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `{"detail":"VOYAGE_API_KEY environment variable is required"}` | Missing env var | Set `VOYAGE_API_KEY` in `.env` or Railway dashboard |
| `{"detail":"Rate limit exceeded"}` on evaluate | Voyage AI free tier (3 RPM) | Add payment method at dashboard.voyageai.com |
| `"answer":"No relevant code found"` | Index is empty | Run Step 3 to index files first |
| `500` on `/index/directory` | Path doesn't exist on Railway | Use `/index/files` with JSON body on Railway; directory indexing is local-only |
| Server doesn't start locally | Wrong venv or missing keys | `source venv/bin/activate` and check `.env` exists |
