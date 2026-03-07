"""
Migration Workflow Agent — Tool Schemas & System Prompts.

Each phase of the planning agent uses:
  - A focused system prompt that tells the LLM exactly what to do
  - A restricted set of tools so the agent can only take appropriate actions
    in that phase (prevents premature execution or skipping steps)
"""

# ---------------------------------------------------------------------------
# TOOL DEFINITIONS  (Anthropic tool-use JSON schema)
# Tool names match _execute_tool() dispatcher in agent.py
# ---------------------------------------------------------------------------

TOOL_ANALYZE_CODE = {
    "name": "analyze_code",
    "description": (
        "Record the analysis of the source files. Call this once with a complete "
        "breakdown of components, dependencies, framework patterns and migration "
        "challenges. The planning phase depends entirely on this output."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "components": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Named components found: classes, functions, routes, middlewares"
            },
            "dependencies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "External libraries / packages used in the source"
            },
            "patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Framework-specific patterns (e.g. 'Express Router', 'middleware chain')"
            },
            "challenges": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Potential migration pain-points or incompatibilities"
            },
            "summary": {
                "type": "string",
                "description": "One-paragraph plain-English summary of the source codebase"
            }
        },
        "required": ["components", "dependencies", "patterns", "challenges", "summary"]
    }
}

TOOL_CREATE_PLAN = {
    "name": "create_plan",
    "description": (
        "Create the step-by-step migration plan. Each step must be independently "
        "executable and map source files to output files. Call this once."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "description": {"type": "string"},
                        "input_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Source files this step consumes"
                        },
                        "output_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Target files this step produces"
                        },
                        "complexity": {
                            "type": "string",
                            "enum": ["low", "medium", "high"]
                        }
                    },
                    "required": ["id", "description", "input_files", "output_files", "complexity"]
                }
            },
            "estimated_risk": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Overall migration risk level"
            }
        },
        "required": ["steps", "estimated_risk"]
    }
}

TOOL_WRITE_FILE = {
    "name": "write_migrated_file",
    "description": (
        "Write one migrated output file. Call this once per output file — "
        "do NOT combine multiple files into one call. "
        "Code must be complete and runnable; no placeholders or TODOs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Target filename, e.g. 'routers/users.py'"
            },
            "content": {
                "type": "string",
                "description": "Full migrated source code"
            },
            "step_id": {
                "type": "integer",
                "description": "Plan step ID this file belongs to"
            },
            "notes": {
                "type": "string",
                "description": "Brief explanation of what changed from source"
            }
        },
        "required": ["filename", "content", "step_id"]
    }
}

TOOL_VALIDATE_SYNTAX = {
    "name": "validate_python_syntax",
    "description": (
        "Check that a migrated Python file has valid syntax using ast.parse(). "
        "Call this for every .py file in migrated_files before calling report_verification."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Filename from migrated_files to validate"
            }
        },
        "required": ["filename"]
    }
}

TOOL_REPORT_VERIFICATION = {
    "name": "report_verification",
    "description": (
        "Submit the final verification report after reviewing all migrated files. "
        "Call this once after running validate_python_syntax on every file."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "valid": {
                "type": "boolean",
                "description": "True only if all files passed validation"
            },
            "validations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {"type": "string"},
                        "valid": {"type": "boolean"},
                        "notes": {"type": "string"}
                    },
                    "required": ["file", "valid", "notes"]
                }
            },
            "issues": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Issues found (empty list if all valid)"
            },
            "recommendations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional improvement suggestions"
            }
        },
        "required": ["valid", "validations", "issues"]
    }
}

TOOL_COMPLETE_PHASE = {
    "name": "complete_phase",
    "description": (
        "Signal that all work for the current phase is done and the agent "
        "should advance to the next phase. Always call this last in every phase."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "phase": {
                "type": "string",
                "description": "Name of the phase being completed"
            },
            "summary": {
                "type": "string",
                "description": "One-sentence summary of what was accomplished"
            }
        },
        "required": ["phase", "summary"]
    }
}

# ---------------------------------------------------------------------------
# PER-PHASE TOOL SETS
# Each phase only receives the tools appropriate for that phase.
# ---------------------------------------------------------------------------

ANALYSIS_TOOLS = [TOOL_ANALYZE_CODE, TOOL_COMPLETE_PHASE]
PLANNING_TOOLS = [TOOL_CREATE_PLAN, TOOL_COMPLETE_PHASE]
EXECUTION_TOOLS = [TOOL_WRITE_FILE, TOOL_COMPLETE_PHASE]
VERIFICATION_TOOLS = [TOOL_VALIDATE_SYNTAX, TOOL_REPORT_VERIFICATION, TOOL_COMPLETE_PHASE]

# ---------------------------------------------------------------------------
# SYSTEM PROMPTS (one per phase)
# ---------------------------------------------------------------------------

def make_analysis_prompt(source: str, target: str, files: dict) -> str:
    file_section = "\n\n".join(
        f"### {name}\n```\n{content}\n```"
        for name, content in files.items()
    )
    return f"""You are a senior software architect performing a migration analysis.

Source framework : {source}
Target framework : {target}
Files to analyze : {list(files.keys())}

{file_section}

Your task
---------
1. Read every file above carefully.
2. Call `analyze_code` with a complete structured analysis — be thorough,
   the planning phase depends entirely on this.
3. Call `complete_phase` when done.

Do NOT skip any file. Do NOT produce migrated code yet."""


def make_planning_prompt(source: str, target: str, analysis: dict) -> str:
    return f"""You are a senior software architect creating a migration plan.

Source framework : {source}
Target framework : {target}

Analysis results
----------------
Components  : {analysis.get('components', [])}
Dependencies: {analysis.get('dependencies', [])}
Patterns    : {analysis.get('patterns', [])}
Challenges  : {analysis.get('challenges', [])}
Summary     : {analysis.get('summary', '')}

Source files: {list(analysis.get('source_files', []))}

Your task
---------
1. Call `create_plan` with an ordered list of steps.
2. Every source file MUST appear in at least one step's input_files.
3. Every output file MUST have the correct target extension
   (e.g. .py for {target}).
4. Call `complete_phase` when done.

File naming rules for {target}:
- Route/controller files  → routers/<name>.py
- Model files             → models/<name>.py
- Utility files           → utils/<name>.py
- App entry point         → main.py"""


def make_execution_prompt(source: str, target: str, plan_steps: list, source_files: dict) -> str:
    steps_text = "\n".join(
        f"  Step {s['id']}: {s['description']}\n"
        f"    input : {s['input_files']}\n"
        f"    output: {s['output_files']}"
        for s in plan_steps
    )
    file_section = "\n\n".join(
        f"### {name}\n```\n{content}\n```"
        for name, content in source_files.items()
    )
    return f"""You are a senior developer migrating code from {source} to {target}.

Migration plan
--------------
{steps_text}

Source files
------------
{file_section}

Your task
---------
1. Execute each step in order.
2. For each output file in the plan, call `write_migrated_file` with the
   COMPLETE migrated code — one call per file, no placeholders.
3. Call `complete_phase` after all files are written.

Migration rules for {target}
-----------------------------
- Use async/await throughout where the source uses async patterns.
- Add Python type hints to all function signatures.
- Replace all {source}-specific imports and decorators with {target} equivalents.
- Keep business logic identical — only change framework glue code.
- Include ALL necessary imports at the top of every file."""


def make_verification_prompt(target: str, migrated_files: dict) -> str:
    file_section = "\n\n".join(
        f"### {name}\n```python\n{content}\n```"
        for name, content in migrated_files.items()
    )
    filenames = list(migrated_files.keys())
    return f"""You are a senior {target} developer performing a post-migration code review.

Migrated files
--------------
{file_section}

Your task
---------
1. Call `validate_python_syntax` for EACH of these files: {filenames}
   (call it once per file, not once for all files together)
2. Review each file for correct {target} idioms, proper imports, type hints,
   and no leftover {target}-incompatible code.
3. Call `report_verification` with your complete findings.
4. Call `complete_phase` when done.

Be strict: flag anything that would cause a runtime error."""

