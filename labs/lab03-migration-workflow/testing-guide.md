# Lab 03 — Migration Workflow Agent: Testing Guide

**Live URL:** `https://vercel-api-five-olive.vercel.app`

---

## Run the Full Test Suite

```bash
cd /Users/eagle/code/ai-training/labs/lab03-migration-workflow
bash test-agent.sh https://vercel-api-five-olive.vercel.app
```

---

## Quick Smoke Tests

```bash
BASE=https://vercel-api-five-olive.vercel.app

# 1. Health
curl -s $BASE/health | python3 -m json.tool

# 2. Supported frameworks
curl -s $BASE/providers | python3 -m json.tool
```

---

## Migration Tests

### Flask → FastAPI
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

### Express → FastAPI (single file)
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

### Express → FastAPI (multi-file)
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

### Error case — empty files (expect 422)
```bash
curl -s -X POST https://vercel-api-five-olive.vercel.app/migrate \
  -H "Content-Type: application/json" \
  -d '{"source_framework":"express","target_framework":"fastapi","files":{}}' \
  | python3 -m json.tool
```

---

## Expected Response Shape

```json
{
    "success": true,
    "migrated_files": { "routers/users.py": "..." },
    "plan_executed": [ { "id": 1, "description": "...", "status": "completed" } ],
    "verification": { "files_migrated": 1, "steps_completed": 4, "issues": [], "validations": [] },
    "errors": []
}
```

| Field | Pass condition |
|-------|---------------|
| `success` | `true` |
| `migrated_files` | at least one entry |
| `plan_executed[*].status` | all `"completed"` |
| `verification.issues` | empty array |
| Filenames | `.js` → `.py`, `routes/` → `routers/` |
