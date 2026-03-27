# Test Guide — AI Code Review Bot (Capstone Option A)

This guide walks through testing the system both locally and against the production deployment.

---

## How It Works

```
                    ┌──────────────────┐
    POST /review    │                  │   anthropic.messages.create
  ──────────────►  │   FastAPI Backend  │ ──────────────────────────►  Claude
    { code,         │   (Python)        │ ◄──────────────────────────
      language }    │                  │   structured JSON review
                    └──────────────────┘
                             ▲
                             │ VITE_API_URL
                    ┌──────────────────┐
                    │  React / Vite UI  │  (TypeScript · dark theme)
                    └──────────────────┘
```

**Review flow:**

1. Client sends `POST /review` with `{ code, language, filename? }`
2. `main.py` validates the request (max 50 000 chars, rate limit 20 req/min/IP)
3. `reviewer.py` builds the Claude prompt via `prompts.py` and calls `llm_client.py`
4. Claude returns a raw JSON string following the schema
5. `reviewer.py` parses → validates with Pydantic → returns `ReviewResponse`
6. Frontend renders issues sorted by severity, a score bar, and general suggestions

---

## URLs at a Glance

| Environment | Component   | URL |
|-------------|-------------|-----|
| Local       | Backend API | `http://localhost:8000` |
| Local       | Frontend UI | `http://localhost:5173` |
| Local       | Swagger docs| `http://localhost:8000/docs` |
| Production  | Backend API | *(set by Railway — see deploy output)* |
| Production  | Frontend UI | *(set by Vercel — see deploy output)* |

---

## Part 1 — Local Testing

### 1.1 Backend setup

```bash
cd ai-training/labs/capstone-options/option-a-code-review/python

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — paste your ANTHROPIC_API_KEY
```

### 1.2 Start the backend

```bash
uvicorn main:app --port 8000 --reload
```

Wait for:
```
Application startup complete.
```

---

### 1.3 Health check

```bash
curl http://localhost:8000/health
```

Expected:
```json
{ "status": "healthy", "model": "claude-3-5-haiku-20241022" }
```

---

### 1.4 Review: Python — SQL injection vulnerability

```bash
curl -s -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{
    "language": "python",
    "filename": "db.py",
    "code": "def get_user(username):\n    query = \"SELECT * FROM users WHERE name = '\" + username + \"'\"\n    return db.execute(query)"
  }' | python3 -m json.tool
```

Expected: at least one issue with `"category": "security"` and `"severity": "critical"` or `"high"`.

---

### 1.5 Review: JavaScript — eval() security risk

```bash
curl -s -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{
    "language": "javascript",
    "code": "function runUserCode(input) {\n  return eval(input);\n}"
  }' | python3 -m json.tool
```

Expected: security issue flagging `eval()` as dangerous.

---

### 1.6 Review: Clean Python — expect a high score

```bash
curl -s -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{
    "language": "python",
    "code": "def add(a: int, b: int) -> int:\n    return a + b"
  }' | python3 -m json.tool
```

Expected: `"overall_score"` ≥ 8, `"issues": []` or only low-severity style notes.

---

### 1.7 Edge cases

**Empty code — HTTP 422:**
```bash
curl -i -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{"code": "", "language": "python"}'
```

**Code too long — HTTP 422:**
```bash
python3 -c "print('x' * 50001)" | \
  python3 -c "
import sys, json
code = sys.stdin.read()
print(json.dumps({'code': code, 'language': 'python'}))
" | curl -i -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d @-
```

**Rate limit test (21 rapid requests — last ones return HTTP 429):**
```bash
for i in $(seq 1 21); do
  curl -s -o /dev/null -w "req $i: HTTP %{http_code}\n" \
    -X POST http://localhost:8000/review \
    -H "Content-Type: application/json" \
    -d '{"code": "x = 1", "language": "python"}'
done
```

---

### 1.8 Swagger UI

Open [http://localhost:8000/docs](http://localhost:8000/docs) in a browser.

- Use the `POST /review` form to send a request interactively.
- Inspect the response schema under **Schemas → ReviewResponse**.

---

### 1.9 Frontend setup

```bash
cd ai-training/labs/capstone-options/option-a-code-review/frontend

cp .env.example .env            # VITE_API_URL=http://localhost:8000

npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

**End-to-end walkthrough:**

| Step | Action | Expected |
|------|--------|----------|
| 1 | Select **python** from the language dropdown | Dropdown updates |
| 2 | Paste the SQL injection snippet from §1.4 | Code area fills |
| 3 | Click **Review Code** (or press ⌘+Enter) | Button shows animated loader |
| 4 | Wait ~5–15 s | Results render below |
| 5 | Check **Issues** section | Security badge (red) visible |
| 6 | Click **Suggestion** on the issue | Inline suggestion expands |
| 7 | Check **score bar** | Score ≤ 6 for the insecure snippet |
| 8 | Paste the clean `add()` snippet | Score ≥ 8, minimal or zero issues |

---

## Part 2 — Remote (Production) Testing

### 2.1 Deploy the backend to Railway

```bash
cd ai-training/labs/capstone-options/option-a-code-review
./deploy_railway.sh
```

The script will:
- Log you in to Railway (if not already)
- Create project **code-review-bot**
- Deploy `python/` as the service
- Set `ANTHROPIC_API_KEY` and `LLM_MODEL` as environment variables
- Print the public URL

Take note of the printed URL — you need it for the next step.

### 2.2 Deploy the frontend to Vercel

```bash
VITE_API_URL=https://<your-railway-url> ./deploy_vercel.sh
```

The script will:
- Log you in to Vercel (if not already)
- Run `npm install && npm run build`
- Deploy `frontend/dist/` as project **code-review-bot-ui**
- Print the Vercel URL

### 2.3 Lock down CORS (optional but recommended)

```bash
cd python
railway variables --set "ALLOWED_ORIGINS=https://code-review-bot-ui.vercel.app"
```

Replace the URL with the one printed by `deploy_vercel.sh`.

---

### 2.4 Production health check

```bash
curl https://<your-railway-url>/health
```

Expected:
```json
{ "status": "healthy", "model": "claude-3-5-haiku-20241022" }
```

---

### 2.5 Production review test

```bash
curl -s -X POST https://<your-railway-url>/review \
  -H "Content-Type: application/json" \
  -d '{
    "language": "python",
    "filename": "db.py",
    "code": "def get_user(username):\n    query = \"SELECT * FROM users WHERE name = '\" + username + \"'\"\n    return db.execute(query)"
  }' | python3 -m json.tool
```

---

### 2.6 Production UI smoke test

1. Open your Vercel URL in a browser.
2. Paste any code snippet.
3. Select the language and click **Review Code**.
4. Confirm results render correctly and the score bar appears.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `502` on `/review` | LLM returned non-JSON | Check Railway logs: `railway logs` |
| `401` from Anthropic | Wrong or missing API key | `railway variables --set "ANTHROPIC_API_KEY=..."` |
| `429` from backend | Exceeded 20 req/min | Wait 60 s or adjust `slowapi` limit in `main.py` |
| CORS error in browser | `ALLOWED_ORIGINS` mismatch | Set to exact Vercel URL (no trailing slash) |
| Vercel build fails | `VITE_API_URL` not set | Re-run `deploy_vercel.sh` with `VITE_API_URL=...` |
| Frontend shows blank page | JS error | Open DevTools Console; check `VITE_API_URL` in the built bundle |
