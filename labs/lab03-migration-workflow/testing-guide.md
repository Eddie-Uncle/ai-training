# Lab 03 — Migration Workflow Agent: Testing Guide

## Prerequisites

- `$HOME/.venv` Python virtual environment with dependencies installed
- `$HOME/.env` contains `ANTHROPIC_API_KEY`
- Server running on `http://localhost:8003`

---

## Start the Server

```bash
cd /Users/eagle/code/ai-training/labs/lab03-migration-workflow/python
source $HOME/.venv/bin/activate
uvicorn main:app --reload --port 8003
```

---

## Run All Tests

```bash
cd /Users/eagle/code/ai-training/labs/lab03-migration-workflow
bash test-agent.sh
```

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Server health + active LLM provider |
| `GET` | `/frameworks` | Supported source/target frameworks |
| `POST` | `/migrate` | Run full 4-phase migration workflow |

---

## Test Cases

### 1. Health Check
Confirms the server is up and using the correct LLM provider.

```bash
curl -s http://localhost:8003/health | python3 -m json.tool
```

Expected:
```json
{
    "status": "healthy",
    "provider": "anthropic"
}
```

---

### 2. List Supported Frameworks
```bash
curl -s http://localhost:8003/frameworks | python3 -m json.tool
```

---

### 3. Express → FastAPI (Single Route)
Minimal migration: one Express.js route file → FastAPI router.

```bash
curl -s -X POST http://localhost:8003/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "source_framework": "express",
    "target_framework": "fastapi",
    "files": {
      "routes/users.js": "const express = require(\"express\");\nconst router = express.Router();\n\nrouter.get(\"/users\", async (req, res) => {\n    const users = await db.getUsers();\n    res.json(users);\n});\n\nmodule.exports = router;"
    }
  }' | python3 -m json.tool
```

Expected response shape:
```json
{
    "success": true,
    "migrated_files": { "routers/users.py": "..." },
    "plan_executed": [ { "id": 1, "description": "...", "status": "completed" } ],
    "verification": { "files_migrated": 1, "steps_completed": 4, "issues": [], "validations": [...] },
    "errors": []
}
```

---

### 4. Express → FastAPI (Multi-file)
Tests the agent handling multiple source files in one migration.

```bash
curl -s -X POST http://localhost:8003/migrate \
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

---

### 5. Flask → FastAPI
Tests migrating between two Python frameworks.

```bash
curl -s -X POST http://localhost:8003/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "source_framework": "flask",
    "target_framework": "fastapi",
    "files": {
      "app.py": "from flask import Flask, jsonify\napp = Flask(__name__)\n\n@app.route(\"/items\", methods=[\"GET\"])\ndef get_items():\n    return jsonify([{\"id\": 1, \"name\": \"Item One\"}])\n\n@app.route(\"/items/<int:item_id>\", methods=[\"GET\"])\ndef get_item(item_id):\n    return jsonify({\"id\": item_id, \"name\": \"Item One\"})\n\nif __name__ == \"__main__\":\n    app.run(debug=True)"
    }
  }' | python3 -m json.tool
```

---

### 6. Error Case — Empty Files
Confirms the agent handles an empty file map gracefully.

```bash
curl -s -X POST http://localhost:8003/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "source_framework": "express",
    "target_framework": "fastapi",
    "files": {}
  }' | python3 -m json.tool
```

---

## What Passes / Fails

| Check | Pass Condition |
|-------|---------------|
| `success: true` | No errors in the `errors` array |
| `migrated_files` populated | At least one file in migrated output |
| `plan_executed` all `completed` | Every step has `status: "completed"` |
| `verification.issues` empty | No issues flagged by the verifier |
| Filename transformed | `.js` → `.py`, `routes/` → `routers/` |

---

## Phase Breakdown

```
POST /migrate
  └── Phase 1: ANALYSIS
        LLM reads each source file, returns JSON of components/deps/challenges
  └── Phase 2: PLANNING
        LLM creates ordered step-by-step migration plan
  └── Phase 3: EXECUTION
        LLM migrates each step, stores output in migrated_files
  └── Phase 4: VERIFICATION
        LLM reviews each migrated file for correctness, returns valid/issues
```
