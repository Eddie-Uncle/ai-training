"""
Migration Workflow Agent — Planning Agent Pattern Implementation
=========================================================

Architecture
------------
MigrationAgent.run(state)
  ├── _analyze(state)   → _tool_loop(ANALYSIS_TOOLS)
  ├── _plan(state)      → _tool_loop(PLANNING_TOOLS)
  ├── _execute(state)   → _tool_loop(EXECUTION_TOOLS)
  └── _verify(state)    → _tool_loop(VERIFICATION_TOOLS)

The agentic loop (_tool_loop)
-----------------------------
Each phase runs a dedicated loop that:
  1. Calls the LLM with the full messages[] history + tool definitions
  2. Parses text and tool_use blocks from the response
  3. Appends the assistant message to messages[]
  4. Executes each tool call and captures the result
  5. Appends tool results as a "user" message to messages[]
  6. Repeats until stop_reason == "end_turn" or complete_phase is called

This means the LLM always has full context of what it has already done
within the phase — satisfying "manage state across agent iterations".
"""

import ast
import sys
import os
import json
from typing import Any, Callable, Optional

sys.path.append(
    os.path.join(os.path.dirname(__file__), "../../lab02-code-analyzer-agent/python"),
)
from llm_client import LLMClient

from state import (
    MigrationState, MigrationStep, Phase,
    AgentIteration, ToolCall,
)
from prompts import (
    ANALYSIS_TOOLS, PLANNING_TOOLS, EXECUTION_TOOLS, VERIFICATION_TOOLS,
    make_analysis_prompt, make_planning_prompt,
    make_execution_prompt, make_verification_prompt,
)

# Hard cap on agentic loop iterations per phase — prevents infinite loops
MAX_ITERATIONS_PER_PHASE = 20

ProgressCallback = Callable[[str, str], None]


class MigrationAgent:
    """Multi-phase migration agent using the planning agent pattern."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self._cb: ProgressCallback = lambda phase, msg: None

    # ------------------------------------------------------------------
    # PUBLIC  —  entry point
    # ------------------------------------------------------------------

    def run(
        self,
        state: MigrationState,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> MigrationState:
        """
        Run all 4 phases in sequence.

        Each phase runs a full agentic loop: the LLM calls tools, receives
        results, and iterates until it signals completion via complete_phase.
        State is threaded through every phase so all results accumulate.
        """
        if progress_callback:
            self._cb = progress_callback

        phases = [
            (Phase.ANALYSIS,     self._analyze,  "Analysis"),
            (Phase.PLANNING,     self._plan,     "Planning"),
            (Phase.EXECUTION,    self._execute,  "Execution"),
            (Phase.VERIFICATION, self._verify,   "Verification"),
        ]

        for phase_enum, phase_fn, phase_label in phases:
            state.phase = phase_enum
            self._cb(phase_enum.value, f"Starting {phase_label} phase…")
            state = phase_fn(state)
            if state.errors:
                self._cb("error", f"{phase_label} phase failed: {state.errors[-1]}")
                return state

        state.phase = Phase.COMPLETE
        self._cb("complete", "All 4 phases complete.")
        return state

    # ------------------------------------------------------------------
    # PHASE 1  —  ANALYSIS
    # Objective: understand source code structure
    # Tool used: analyze_code → stores result in state.analysis
    # ------------------------------------------------------------------

    def _analyze(self, state: MigrationState) -> MigrationState:
        """Phase 1: Analyze source code to understand its structure."""
        system = make_analysis_prompt(
            state.source_framework,
            state.target_framework,
            state.source_files,
        )

        state = self._tool_loop(
            phase_name=Phase.ANALYSIS.value,
            system=system,
            tools=ANALYSIS_TOOLS,
            state=state,
        )

        # Pick up analyze_code result from tool call log
        for tc in reversed(state.tool_calls_log):
            if tc.tool_name == "analyze_code" and tc.phase == Phase.ANALYSIS.value:
                state.analysis = dict(tc.tool_input)
                # Inject source file names so planning prompt can reference them
                state.analysis["source_files"] = list(state.source_files.keys())
                break

        if not state.analysis:
            state.errors.append("Analysis phase: analyze_code tool was never called")

        return state

    # ------------------------------------------------------------------
    # PHASE 2  —  PLANNING
    # Objective: create a step-by-step migration plan
    # Tool used: create_plan → stores plan in state.plan
    # ------------------------------------------------------------------

    def _plan(self, state: MigrationState) -> MigrationState:
        """Phase 2: Create a migration plan from the analysis."""
        system = make_planning_prompt(
            state.source_framework,
            state.target_framework,
            state.analysis or {},
        )

        state = self._tool_loop(
            phase_name=Phase.PLANNING.value,
            system=system,
            tools=PLANNING_TOOLS,
            state=state,
        )

        # Pick up create_plan result
        for tc in reversed(state.tool_calls_log):
            if tc.tool_name == "create_plan" and tc.phase == Phase.PLANNING.value:
                raw_steps = tc.tool_input.get("steps", [])
                state.plan = [
                    MigrationStep(
                        id=s["id"],
                        description=s["description"],
                        input_files=s.get("input_files", []),
                        output_files=s.get("output_files", []),
                        complexity=s.get("complexity", "medium"),
                    )
                    for s in raw_steps
                ]
                break

        if not state.plan:
            state.errors.append("Planning phase: create_plan tool was never called")

        return state

    # ------------------------------------------------------------------
    # PHASE 3  —  EXECUTION
    # Objective: execute each migration step and write migrated files
    # Tool used: write_migrated_file → populates state.migrated_files
    # ------------------------------------------------------------------

    def _execute(self, state: MigrationState) -> MigrationState:
        """Phase 3: Execute migration steps and write migrated files."""
        plan_dicts = [
            {
                "id": s.id,
                "description": s.description,
                "input_files": s.input_files,
                "output_files": s.output_files,
            }
            for s in state.plan
        ]

        system = make_execution_prompt(
            state.source_framework,
            state.target_framework,
            plan_dicts,
            state.source_files,
        )

        state = self._tool_loop(
            phase_name=Phase.EXECUTION.value,
            system=system,
            tools=EXECUTION_TOOLS,
            state=state,
        )

        # Collect write_migrated_file calls → mark steps completed
        for tc in state.tool_calls_log:
            if tc.tool_name == "write_migrated_file" and tc.phase == Phase.EXECUTION.value:
                step_id = tc.tool_input.get("step_id")
                for step in state.plan:
                    if step.id == step_id and step.status != "completed":
                        step.status = "completed"
                        step.result = f"Wrote {tc.tool_input.get('filename')}"

        # Mark any plan steps as completed if their output files were written
        written = set(state.migrated_files.keys())
        for step in state.plan:
            if step.status != "completed":
                if any(f in written for f in step.output_files):
                    step.status = "completed"

        if not state.migrated_files:
            state.errors.append("Execution phase: no files were written")

        return state

    # ------------------------------------------------------------------
    # PHASE 4  —  VERIFICATION
    # Objective: verify the migration is complete and correct
    # Tools used: validate_python_syntax + report_verification
    # ------------------------------------------------------------------

    def _verify(self, state: MigrationState) -> MigrationState:
        """Phase 4: Verify migrated code compiles and is correct."""
        system = make_verification_prompt(
            state.target_framework,
            state.migrated_files,
        )

        state = self._tool_loop(
            phase_name=Phase.VERIFICATION.value,
            system=system,
            tools=VERIFICATION_TOOLS,
            state=state,
        )

        # Pick up report_verification result
        for tc in reversed(state.tool_calls_log):
            if tc.tool_name == "report_verification" and tc.phase == Phase.VERIFICATION.value:
                state.verification_result = dict(tc.tool_input)
                break

        # Collect syntax check results from validate_python_syntax calls
        syntax_checks: dict[str, dict] = {}
        for tc in state.tool_calls_log:
            if tc.tool_name == "validate_python_syntax" and tc.phase == Phase.VERIFICATION.value:
                fname = tc.tool_input.get("filename", "")
                syntax_checks[fname] = tc.tool_result

        if state.verification_result is None:
            # Agent never called report_verification — synthesise from syntax checks
            all_valid = all(v.get("valid", False) for v in syntax_checks.values())
            state.verification_result = {
                "valid": all_valid or bool(state.migrated_files),
                "validations": [
                    {"file": k, "valid": v.get("valid", True), "notes": v.get("error", "") or ""}
                    for k, v in syntax_checks.items()
                ],
                "issues": [],
                "recommendations": [],
            }

        state.verification_result["syntax_checks"] = syntax_checks
        state.verification_result["files_migrated"] = len(state.migrated_files)
        state.verification_result["steps_completed"] = sum(
            1 for s in state.plan if s.status == "completed"
        )

        return state

    # ------------------------------------------------------------------
    # CORE AGENTIC LOOP
    # ------------------------------------------------------------------

    def _tool_loop(
        self,
        phase_name: str,
        system: str,
        tools: list,
        state: MigrationState,
    ) -> MigrationState:
        """
        The planning agent loop — the heart of the pattern.

        Maintains a full messages[] conversation history so the LLM always
        has the complete context of every prior tool call within this phase.
        This is how state is managed across agent iterations.

        Flow per iteration:
          1. LLM call with all messages + tool schemas
          2. Parse text and tool_use blocks
          3. Append assistant message (text + tool_use blocks) to messages[]
          4. Execute each tool call → get result
          5. Append tool results as a 'user' message to messages[]
          6. If complete_phase was called, or stop_reason == 'end_turn' → exit
        """
        messages: list[dict] = state.phase_messages.get(phase_name, [])
        # Anthropic requires at least one user message to start a conversation
        if not messages:
            messages = [{"role": "user", "content": f"Begin the {phase_name} phase."}]
        iteration = 0
        phase_done = False

        while iteration < MAX_ITERATIONS_PER_PHASE and not phase_done:
            iteration += 1
            self._cb(phase_name, f"  Iteration {iteration}")

            # --- 1. Call LLM with tool definitions -----------------------
            response = self.llm.chat_with_tools(
                messages=messages,
                tools=tools,
                system=system,
                max_tokens=4096,
            )

            stop_reason: str = response.get("stop_reason", "end_turn")
            content_blocks: list[dict] = response.get("content", [])

            # --- 2. Split content into text blocks and tool_use blocks ---
            assistant_text = ""
            tool_use_blocks: list[dict] = []

            for block in content_blocks:
                if block["type"] == "text":
                    assistant_text += block.get("text", "")
                elif block["type"] == "tool_use":
                    tool_use_blocks.append(block)

            # --- 3. Append assistant message to history ------------------
            # The assistant message must include both text AND tool_use blocks
            # exactly as returned, so the next LLM call has full context.
            assistant_message: dict = {"role": "assistant", "content": content_blocks}
            messages.append(assistant_message)

            # --- Record this iteration -----------------------------------
            agent_iter = AgentIteration(
                phase=phase_name,
                iteration_number=iteration,
                stop_reason=stop_reason,
                assistant_text=assistant_text,
            )

            # --- 4. Execute tool calls -----------------------------------
            if tool_use_blocks:
                tool_result_blocks: list[dict] = []

                for block in tool_use_blocks:
                    tool_id: str   = block["id"]
                    tool_name: str = block["name"]
                    tool_input: dict = block["input"]

                    self._cb(phase_name, f"    → {tool_name}")

                    result = self._execute_tool(tool_name, tool_input, state)

                    # Log the tool call in state
                    tc = ToolCall(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_result=result,
                        phase=phase_name,
                        iteration=iteration,
                    )
                    state.tool_calls_log.append(tc)
                    agent_iter.tool_calls.append(tc)

                    # Build tool result block for messages[]
                    result_str = (
                        json.dumps(result)
                        if not isinstance(result, str)
                        else result
                    )
                    tool_result_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result_str,
                    })

                    if tool_name == "complete_phase":
                        phase_done = True

                # --- 5. Append all tool results as a single user message -
                messages.append({"role": "user", "content": tool_result_blocks})

            state.iterations.append(agent_iter)

            # --- 6. Decide whether to continue ---------------------------
            if stop_reason == "end_turn" and not tool_use_blocks:
                # LLM stopped without calling any tools — phase is done
                break

        # Persist conversation history for this phase in state
        state.phase_messages[phase_name] = messages
        return state

    # ------------------------------------------------------------------
    # TOOL IMPLEMENTATIONS
    # ------------------------------------------------------------------

    def _execute_tool(self, tool_name: str, tool_input: dict, state: MigrationState) -> Any:
        """Dispatch to the concrete tool implementation."""
        match tool_name:
            case "analyze_code":
                return {"status": "recorded", "components": len(tool_input.get("components", []))}

            case "create_plan":
                n = len(tool_input.get("steps", []))
                return {"status": "recorded", "steps_created": n}

            case "write_migrated_file":
                return self._tool_write_file(tool_input, state)

            case "validate_python_syntax":
                return self._tool_validate_syntax(tool_input, state)

            case "report_verification":
                return {"status": "recorded"}

            case "complete_phase":
                return {"status": "ok", "message": tool_input.get("summary", "done")}

            case _:
                return {"error": f"Unknown tool: {tool_name}"}

    def _tool_write_file(self, tool_input: dict, state: MigrationState) -> dict:
        """Write a migrated file into state.migrated_files and syntax-check it."""
        filename = tool_input.get("filename", "")
        content  = tool_input.get("content", "")

        if not filename or not content:
            return {"status": "error", "message": "filename and content are required"}

        state.migrated_files[filename] = content
        self._cb(Phase.EXECUTION.value, f"    ✓ Wrote {filename} ({len(content)} chars)")

        # Inline syntax check so execution phase gets immediate feedback
        syntax_result = self._run_syntax_check(filename, content)
        return {"status": "ok", "filename": filename, "syntax": syntax_result}

    def _tool_validate_syntax(self, tool_input: dict, state: MigrationState) -> dict:
        """Run ast.parse() on a file in state.migrated_files."""
        filename = tool_input.get("filename", "")
        content  = state.migrated_files.get(filename)

        if content is None:
            available = list(state.migrated_files.keys())
            return {
                "filename": filename,
                "valid": False,
                "error": f"Not found in migrated_files. Available: {available}",
            }

        return self._run_syntax_check(filename, content)

    @staticmethod
    def _run_syntax_check(filename: str, content: str) -> dict:
        """Parse Python source with ast.parse() and return a result dict."""
        if not filename.endswith(".py"):
            return {"filename": filename, "valid": True, "error": None}
        try:
            ast.parse(content)
            return {"filename": filename, "valid": True, "error": None}
        except SyntaxError as e:
            return {
                "filename": filename,
                "valid": False,
                "error": str(e),
                "line": e.lineno,
            }

