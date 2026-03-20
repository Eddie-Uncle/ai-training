# Test Guide — Multi-Agent Workspace

Two ways to test the system: **curl** (terminal) and the **Frontend UI** (browser).

---

## Prerequisites

Make sure the backend is running before any test.

```bash
# From the python/ directory
cd ai-training/labs/lab05-multi-agent/python
source venv/bin/activate
python -m uvicorn main:app --port 8000
```

> Server ready when you see `Application startup complete.`  
> Docs available at **http://localhost:8000/docs**

---

## 1 · curl Tests

### 1.1 Health check

Verify the server is up and using the correct LLM provider.

```bash
curl http://localhost:8000/health
```

**Expected response**

```json
{ "status": "healthy", "provider": "anthropic" }
```

---

### 1.2 Basic research task

The core workflow: Researcher gathers info, Writer produces polished output.

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Write a brief explanation of how RAG systems work for a technical blog post",
    "max_iterations": 5
  }'
```

**Expected response shape**

```json
{
  "result": "# Retrieval-Augmented Generation ...",
  "steps_taken": 2
}
```

- `steps_taken: 2` → Researcher ran (step 1), Writer ran (step 2), Supervisor output FINAL
- `result` is Markdown — ready to render

---

### 1.3 Different topics

Try swapping the `task` to confirm the agents work on any subject.

```bash
# DevOps topic
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Explain GitOps and ArgoCD for a technical blog post aimed at platform engineers",
    "max_iterations": 5
  }'
```

```bash
# Short-form explainer
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Write a 3-paragraph intro to WebAssembly for a developer newsletter",
    "max_iterations": 5
  }'
```

---

### 1.4 Pretty-print the result

Pipe through `jq` to read the Markdown result cleanly in the terminal.

```bash
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Summarise the CAP theorem for a distributed systems primer", "max_iterations": 5}' \
  | jq -r '.result'
```

---

### 1.5 Edge cases

**Empty task** — server should return HTTP 422 (Pydantic validation error):

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"task": ""}'
```

**Missing body** — server should return HTTP 422:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Max iterations 1** — supervisor may not finish the full flow; `_force_final` kicks in:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Explain Kubernetes", "max_iterations": 1}'
```

---

## 2 · Frontend UI Tests

### 2.1 Start the dev server

```bash
cd ai-training/labs/lab05-multi-agent/frontend
npx vite --port 3000
```

Open **http://localhost:3000** in your browser.

> The UI reads `VITE_API_URL` from the environment.  
> When not set it defaults to `http://localhost:8000` — the local backend.

---

### 2.2 End-to-end happy path

| Step | Action | Expected |
|------|--------|----------|
| 1 | Type a task in the text area | Textarea grows to fit text |
| 2 | Select **Max steps = 5** from the dropdown | Dropdown updates |
| 3 | Click **Run** | Button disables, animated dot + "Agents at work…" appears |
| 4 | Wait for completion (~10–20 s) | Markdown output renders; "2 steps" chip appears in header |
| 5 | Scroll through the result | Headings, bold, code blocks all styled correctly |

---

### 2.3 Keyboard shortcut

1. Type a task.
2. Press **⌘ + ↵** (macOS) or **Ctrl + ↵** (Windows/Linux).
3. Agents should start without clicking Run.

---

### 2.4 Error state — server offline

1. Stop the backend (`Ctrl + C` in its terminal).
2. Submit any task in the UI.
3. Expected: red error message — `Cannot reach server — is it running?`
4. Restart the backend; the error clears on the next submission.

---

### 2.5 Multiple tasks in a row

1. Run the first task and wait for the result.
2. Clear the textarea, type a new task, click **Run**.
3. Expected: previous output disappears, loading state shows, new result populates.

---

## 3 · Production smoke tests (after deploy)

Replace the URLs once Railway and Vercel deployments are live.

```bash
BACKEND=https://your-app.railway.app

# Health
curl $BACKEND/health

# Full workflow
curl -X POST $BACKEND/run \
  -H "Content-Type: application/json" \
  -d '{"task": "What is a vector database and when should you use one?", "max_iterations": 5}' \
  | jq '{steps_taken: .steps_taken, preview: .result[:200]}'
```

Open **https://your-app.vercel.app** and repeat the UI tests from section 2.

---

## Checklist

- [ ] `GET /health` returns `{ "status": "healthy", "provider": "anthropic" }`
- [ ] `POST /run` returns `steps_taken: 2` and non-empty Markdown result
- [ ] UI shows loading state while agents run
- [ ] UI renders Markdown (headings, code blocks, bold text)
- [ ] UI shows error message when backend is unreachable
- [ ] Multiple back-to-back tasks work without page refresh
- [ ] Production backend health check passes
- [ ] Production frontend loads and completes a task
