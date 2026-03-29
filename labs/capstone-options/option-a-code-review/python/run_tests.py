#!/usr/bin/env python3
"""Quick API smoke-test for the Code Review Bot."""
import urllib.request
import json
import sys

BASE = "http://localhost:8000"


def review(code: str, language: str, filename: str | None = None) -> dict:
    payload: dict = {"code": code, "language": language}
    if filename:
        payload["filename"] = filename
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}/review",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def show(result: dict) -> None:
    print(f"Summary : {result['summary']}")
    print(f"Issues  : {len(result['issues'])}")
    for issue in result["issues"]:
        line = f"line {issue['line']}" if issue["line"] else "—"
        print(
            f"  [{issue['severity'].upper():<8} / {issue['category']:<11}] {line}: "
            f"{issue['description'][:72]}"
        )
    m = result["metrics"]
    print(f"Score   : {m['overall_score']}/10  complexity={m['complexity']}  maintainability={m['maintainability']}")


# ── health ────────────────────────────────────────────────────────────────────
section("HEALTH CHECK")
with urllib.request.urlopen(f"{BASE}/health") as r:
    health = json.loads(r.read())
print(health)

# ── test 1: SQL injection (Python) ───────────────────────────────────────────
section("TEST 1 — Python SQL injection (expect security critical/high)")
code_sql = (
    'def get_user(username):\n'
    '    query = "SELECT * FROM users WHERE name = \'" + username + "\'"\n'
    '    return db.execute(query)'
)
show(review(code_sql, "python", "db.py"))

# ── test 2: eval() (JavaScript) ───────────────────────────────────────────────
section("TEST 2 — JavaScript eval() (expect security issue)")
code_eval = (
    "function runUserCode(input) {\n"
    "  return eval(input);\n"
    "}"
)
show(review(code_eval, "javascript"))

# ── test 3: clean Python ──────────────────────────────────────────────────────
section("TEST 3 — Clean Python (expect high score, minimal issues)")
code_clean = "def add(a: int, b: int) -> int:\n    return a + b"
show(review(code_clean, "python"))

# ── test 4: Go example ────────────────────────────────────────────────────────
section("TEST 4 — Go multi-language check")
code_go = (
    "func divide(a, b float64) float64 {\n"
    "    return a / b\n"
    "}"
)
show(review(code_go, "go", "math.go"))

print("\nAll tests passed ✓")
