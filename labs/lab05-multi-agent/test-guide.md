# Test Guide — Multi-Agent System (Lab 05)

This guide covers everything from understanding how the system works to running tests locally and in production.

---

## How the Multi-Agent Architecture Works

The system implements the **Supervisor Pattern** — one coordinating agent that delegates work to specialized workers and synthesizes the final output.

```
                    ┌─────────────────┐
                    │  SUPERVISOR     │  ← receives your task, decides who does what
                    │     AGENT       │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
       ┌──────────┐  ┌──────────────┐  ┌──────────┐
       │RESEARCHER│  │    WRITER    │  │ REVIEWER │
       │  AGENT   │  │    AGENT     │  │  AGENT   │
       └──────────┘  └──────────────┘  └──────────┘
```

**Step-by-step flow for every task:**

1. **You send a task** (e.g. `"Write a blog post about RAG systems"`)
2. **Supervisor receives it** and reasons about which agents to use
3. **Supervisor → Researcher**: outputs `DELEGATE: Researcher` + `TASK: ...`
4. **Researcher executes**: gathers key facts, concepts, and relationships on the topic
5. **Researcher result → Supervisor**: the research is fed back into the conversation
6. **Supervisor → Writer**: outputs `DELEGATE: Writer` + `TASK: ... + [research context]`
7. **Writer executes**: turns the raw research into polished, formatted prose
8. **Writer result → Supervisor**: the draft is fed back in
9. **Supervisor outputs** `FINAL: ...` — the synthesized, ready-to-read result

The `DELEGATE: / TASK: / FINAL:` token protocol is how the supervisor communicates its decisions to the orchestration loop in `supervisor.py`. The loop parses these tokens, routes work to the correct worker, and continues iterating until `FINAL` appears or `max_iterations` is reached.

> **Why `steps_taken: 2`?** — Researcher counts as step 1, Writer as step 2. With the default 5 max iterations, the system completes well within budget.

---

## Lab Requirements — How They Were Met

| Lab Requirement | Implementation |
|----------------|---------------|
| ✅ Working multi-agent system | FastAPI backend (`main.py`) + `SupervisorAgent` orchestration loop |
| ✅ Supervisor + at least 2 worker agents | `SupervisorAgent` in `supervisor.py` + `ResearcherAgent` + `WriterAgent` (+ optional `ReviewerAgent`) in `agents.py` |
| ✅ Tested end-to-end workflow | Verified locally (`steps_taken: 2`, full Markdown blog post returned) and in production |

**Additional deliverables built beyond the requirements:**

- Minimalistic React/Vite frontend UI for task submission and Markdown rendering
- One-command deploy scripts (`deploy_railway.sh`, `deploy_vercel.sh`)
- Production deployment on Railway (backend) and Vercel (frontend)

---

## URLs at a Glance

| Environment | Component | URL |
|------------|-----------|-----|
| **Local** | Backend API | `http://localhost:8000` |
| **Local** | Frontend UI | `http://localhost:3000` |
| **Local** | API docs (Swagger) | `http://localhost:8000/docs` |
| **Production** | Backend API | `https://multi-agent-backend-production.up.railway.app` |
| **Production** | Frontend UI | `https://lab05-multi-agent.vercel.app` |

---

## Part 1 — Local Testing

### Start the local backend

```bash
cd ai-training/labs/lab05-multi-agent/python
source venv/bin/activate
python -m uvicorn main:app --port 8000
```

> Wait for `Application startup complete.` before running any tests.

---

### 1.1 Health check

Verify the server is alive and using the correct LLM provider.

```bash
curl http://localhost:8000/health
```

Expected:

```json
{ "status": "healthy", "provider": "anthropic" }
```

---

### 1.2 Core workflow — Researcher → Writer

This is the primary lab deliverable: a supervisor that delegates to two specialized agents.

```bash
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Write a brief explanation of how RAG systems work for a technical blog post",
    "max_iterations": 5
  }' | jq .
```

Expected response shape:

```json
{
  "result": "# Retrieval-Augmented Generation\n\n...",
  "steps_taken": 2
}
```

- `steps_taken: 2` confirms both Researcher and Writer ran before `FINAL` was output
- `result` is Markdown — copy it into any Markdown renderer to see formatted output

---

### 1.3 Try different topics

The system works on any topic — swap the task to explore.

```bash
# DevOps topic
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Explain GitOps and ArgoCD for platform engineers",
    "max_iterations": 5
  }' | jq -r '.result'
```

```bash
# Short-form newsletter piece
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Write a 3-paragraph intro to WebAssembly for a developer newsletter",
    "max_iterations": 5
  }' | jq -r '.result'
```

> Piping to `jq -r '.result'` prints the raw Markdown text, which is easier to read than the JSON envelope.

---

### 1.4 Edge cases

**Empty task string** — should return HTTP 422 (Pydantic validation rejects it before the agents run):

```bash
curl -i -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"task": ""}'
```

**Missing body** — also HTTP 422:

```bash
curl -i -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Forcing a single iteration** — supervisor won't have enough turns to run both agents; `_force_final()` returns the best available result:

```bash
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Explain Kubernetes", "max_iterations": 1}' | jq .
```

---

### 1.5 Start the local frontend

```bash
cd ai-training/labs/lab05-multi-agent/frontend
npx vite --port 3000
```

Open **http://localhost:3000**.

> The frontend reads `VITE_API_URL` at build time. In local dev (no `.env` set), it falls back to `http://localhost:8000`. Make sure the local backend is running on port 8000.

**End-to-end happy path:**

| Step | Action | What you should see |
|------|--------|---------------------|
| 1 | Type a task in the textarea | Text area expands to fit |
| 2 | Choose **Max steps = 5** from the dropdown | Dropdown updates |
| 3 | Click **Run** (or press ⌘+↵) | Button disables; animated dot + "Agents at work…" label appears |
| 4 | Wait ~10–20 seconds | Markdown result renders; "2 steps" chip appears in the output header |
| 5 | Scroll the result | Headings, bold, code blocks all styled correctly |

**Keyboard shortcut:** Press **⌘ + ↵** (macOS) or **Ctrl + ↵** (Windows/Linux) to submit without clicking **Run**.

**Error state:** Stop the backend (`Ctrl + C`), then submit a task — the UI displays `Cannot reach server — is it running?` in red. Restarting the backend clears it on the next submission.

---

## Part 2 — Production Testing

Use these URLs to test the live deployments on Railway and Vercel.

```bash
BACKEND=https://multi-agent-backend-production.up.railway.app
FRONTEND=https://lab05-multi-agent.vercel.app
```

### 2.1 Backend health check

```bash
curl $BACKEND/health
```

Expected: `{ "status": "healthy", "provider": "anthropic" }`

---

### 2.2 Full workflow smoke test

```bash
curl -s -X POST $BACKEND/run \
  -H "Content-Type: application/json" \
  -d '{
    "task": "What is a vector database and when should you use one?",
    "max_iterations": 5
  }' | jq '{steps_taken: .steps_taken, preview: .result[:300]}'
```

Expected: `steps_taken: 2`, non-empty Markdown preview.

---

### 2.3 CORS preflight check

The frontend talks cross-origin to Railway. Verify the CORS headers are correct:

```bash
curl -si \
  -X OPTIONS $BACKEND/run \
  -H "Origin: $FRONTEND" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  | grep -E "HTTP/|access-control-allow"
```

Expected:

```
HTTP/2 200
access-control-allow-origin: https://lab05-multi-agent.vercel.app
access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
access-control-allow-headers: content-type
```

---

### 2.4 Production frontend

Open **https://lab05-multi-agent.vercel.app** and complete the same steps from the local UI test above (steps 1–5). The only difference is the result takes a few extra seconds on cold start.

---

## Final Checklist

### Local
- [ ] `GET /health` → `{ "status": "healthy", "provider": "anthropic" }`
- [ ] `POST /run` → `steps_taken: 2` and non-empty Markdown result
- [ ] Edge case — empty task returns HTTP 422
- [ ] Frontend loads at `http://localhost:3000`
- [ ] Frontend submits task and renders Markdown output
- [ ] Loading state (animated dot) appears while agents run
- [ ] Error banner appears when backend is stopped
- [ ] Multiple tasks in a row work without a page refresh

### Production
- [ ] Railway health check passes
- [ ] Railway `/run` returns `steps_taken: 2`
- [ ] CORS preflight returns `HTTP/2 200` with correct `access-control-allow-origin`
- [ ] Vercel frontend loads and completes a full task end-to-end
