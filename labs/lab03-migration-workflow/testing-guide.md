# Lab 03 — Migration Workflow Agent: Testing Guide

This guide walks you through testing the live migration agent deployed on Vercel. The agent uses an LLM (Anthropic Claude) to perform a 4-phase workflow: **Analyze → Plan → Execute → Verify**. Each test below targets a specific behaviour you should see when the agent is working correctly.

**Live URL:** `https://vercel-api-five-olive.vercel.app`

---

## Before You Start

Make sure the service is up and the API key is configured. Run this first — if it returns `{"status":"healthy","provider":"anthropic"}` you're good to go:

```bash
curl -s https://vercel-api-five-olive.vercel.app/health | python3 -m json.tool
```

If you see a 500 or `"provider": null`, the `ANTHROPIC_API_KEY` environment variable is missing from the Vercel project. See the deploy README for how to add it.

---

## Run the Full Automated Suite

This runs all 19 checks in one go and prints a pass/fail summary:

```bash
cd $HOME/code/ai-training/labs/lab03-migration-workflow
bash test-agent.sh https://vercel-api-five-olive.vercel.app
```

If you just want to explore manually, the individual tests below explain what each one does and what a good response looks like.

---

## Test 1 — Health Check

**What it tests:** The server is running and has a live LLM provider configured.

**Why it matters:** Every migration request hits the LLM. If the health check fails, nothing else will work.

```bash
curl -s https://vercel-api-five-olive.vercel.app/health | python3 -m json.tool
```

**Good response:**
```json
{
    "status": "healthy",
    "provider": "anthropic"
}
```

---

## Test 2 — List Supported Frameworks

**What it tests:** The API correctly advertises which source and target frameworks the agent knows how to handle.

**Why it matters:** Sending an unsupported framework name to `/migrate` would produce a confusing error. This lets clients validate inputs before sending them.

```bash
curl -s https://vercel-api-five-olive.vercel.app/providers | python3 -m json.tool
```

**Good response:** A JSON object with `source` and `target` arrays listing framework names (e.g. `"express"`, `"flask"`, `"fastapi"`).

---

## Test 3 — Flask → FastAPI (Python to Python)

**What it tests:** The agent can migrate between two Python frameworks — Flask's decorator-based routing to FastAPI's typed route functions.

**Why it matters:** This is the simplest possible migration because the language stays the same. Only the framework idioms change: `@app.route(...)` becomes `@app.get(...)`, `jsonify(...)` is replaced by returning a plain dict, and path parameters move from `<int:item_id>` to `item_id: int`.

```bash
curl -s -X POST https://vercel-api-five-olive.vercel.app/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "source_framework": "flask",
    "target_framework": "fastapi",
    "files": {
      "app.py": "from flask import Flask, jsonify\napp = Flask(__name__)\n\n@app.route(\"/items\")\ndef get_items():\n    return jsonify([{\"id\": 1, \"name\": \"Item One\"}])\n\n@app.route(\"/items/<int:item_id>\")\ndef get_item(item_id):\n    return jsonify({\"id\": item_id, \"name\": \"Item One\"})\n\nif __name__ == \"__main__\":\n    app.run(debug=True)"
    }
  }' | python3 -m json.tool
```

**What to look for:**
- `success` is `true`
- `migrated_files` contains a `.py` file using `from fastapi import FastAPI`
- `verification.issues` is empty — the LLM validated its own output

---

## Test 4 — Express → FastAPI (Single File, Cross-Language)

**What it tests:** The agent can cross a language boundary — JavaScript/Node.js to Python — for a single route file.

**Why it matters:** This is the core use case for the agent. Express uses `router.get("/path", async (req, res) => { ... })` with callback-style handlers; FastAPI uses `@router.get("/path")` with `async def` functions and typed return values. The agent must understand both frameworks deeply enough to translate patterns, not just syntax.

```bash
curl -s -X POST https://vercel-api-five-olive.vercel.app/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "source_framework": "express",
    "target_framework": "fastapi",
    "files": {
      "routes/users.js": "const express = require(\"express\");\nconst router = express.Router();\nrouter.get(\"/users\", async (req, res) => {\n    const users = await db.getUsers();\n    res.json(users);\n});\nmodule.exports = router;"
    }
  }' | python3 -m json.tool
```

**What to look for:**
- `migrated_files` has a key like `routers/users.py` (directory and extension both changed)
- The migrated file imports `APIRouter` from FastAPI
- No `res.json(...)` or `module.exports` in the output

---

## Test 5 — Express → FastAPI (Multiple Files)

**What it tests:** The agent can handle a real-world scenario where multiple route files need to be migrated in one request.

**Why it matters:** Real applications have many route files. The agent must analyse all of them together (so it can spot shared patterns and dependencies), plan a migration that covers every file, and produce a migrated output for each one — without mixing them up.

```bash
curl -s -X POST https://vercel-api-five-olive.vercel.app/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "source_framework": "express",
    "target_framework": "fastapi",
    "files": {
      "routes/users.js": "const express = require(\"express\");\nconst router = express.Router();\nrouter.get(\"/users\", async (req, res) => { res.json(await db.getUsers()); });\nmodule.exports = router;",
      "routes/products.js": "const express = require(\"express\");\nconst router = express.Router();\nrouter.get(\"/products\", async (req, res) => { res.json(await db.getProducts()); });\nrouter.post(\"/products\", async (req, res) => { const p = await db.createProduct(req.body); res.status(201).json(p); });\nmodule.exports = router;"
    }
  }' | python3 -m json.tool
```

**What to look for:**
- `migrated_files` has **two** entries — one per source file
- Both are `.py` files under `routers/`
- The POST route in `products.js` becomes a `@router.post` handler with a request body model

---

## Test 6 — Empty Files (Error Handling)

**What it tests:** The API rejects requests that have no files to migrate, rather than silently running the agent on nothing.

**Why it matters:** Sending an empty `files` object is almost certainly a client bug — a misconfigured form, a script that read the wrong directory, etc. The agent should fail fast with a clear error (HTTP 422) rather than wasting an LLM call and returning a confusing empty result.

```bash
curl -s -X POST https://vercel-api-five-olive.vercel.app/migrate \
  -H "Content-Type: application/json" \
  -d '{"source_framework":"express","target_framework":"fastapi","files":{}}' \
  | python3 -m json.tool
```

**Good response:** HTTP 422 with a validation error message — no LLM call is made.

---

## Understanding the Response

Every successful `/migrate` call returns this structure:

```json
{
    "success": true,
    "migrated_files": {
        "routers/users.py": "from fastapi import APIRouter\n..."
    },
    "plan_executed": [
        { "id": 1, "description": "Analyse source files", "status": "completed" },
        { "id": 2, "description": "Generate migration plan", "status": "completed" },
        { "id": 3, "description": "Migrate each file", "status": "completed" },
        { "id": 4, "description": "Verify output", "status": "completed" }
    ],
    "verification": {
        "files_migrated": 1,
        "steps_completed": 4,
        "issues": [],
        "validations": [{ "file": "routers/users.py", "valid": true, "notes": "..." }]
    },
    "errors": []
}
```

| Field | What it tells you |
|-------|-------------------|
| `success` | `true` means all 4 phases completed without an unrecoverable error |
| `migrated_files` | The actual migrated code — one entry per source file |
| `plan_executed[*].status` | All steps should be `"completed"`; `"failed"` means the LLM hit an issue in that phase |
| `verification.issues` | The LLM's self-review found problems — check these even when `success` is `true` |
| `errors` | Hard errors (API failures, timeouts) — should be empty |
