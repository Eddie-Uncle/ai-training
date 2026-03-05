"""Migration Workflow Agent - State Management."""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class Phase(Enum):
    """Migration phases."""
    ANALYSIS = "analysis"
    PLANNING = "planning"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    COMPLETE = "complete"


@dataclass
class MigrationStep:
    """Represents a single migration step in the plan."""
    id: int
    description: str
    status: str = "pending"   # pending | in_progress | completed | failed
    input_files: List[str] = field(default_factory=list)
    output_files: List[str] = field(default_factory=list)
    complexity: str = "medium"
    result: Optional[str] = None


@dataclass
class ToolCall:
    """
    Records a single tool call made by the agent.
    Captured every time the agent invokes a tool inside the agentic loop.
    """
    tool_name: str
    tool_input: Dict[str, Any]
    tool_result: Any
    phase: str
    iteration: int


@dataclass
class AgentIteration:
    """
    Records one full cycle of the agentic loop:
      LLM call → tool calls → tool results appended to messages[]
    """
    phase: str
    iteration_number: int
    stop_reason: str           # 'end_turn' | 'tool_use'
    assistant_text: str = ""   # any free-text the LLM produced alongside tools
    tool_calls: List[ToolCall] = field(default_factory=list)


@dataclass
class MigrationState:
    """Full state of the migration workflow, passed through every phase."""

    # ---- required on construction ----
    source_framework: str
    target_framework: str
    source_files: Dict[str, str]     # filename → source content

    # ---- phase tracking ----
    phase: Phase = Phase.ANALYSIS

    # ---- phase results ----
    analysis: Optional[Dict[str, Any]] = None
    plan: List[MigrationStep] = field(default_factory=list)
    current_step: int = 0
    migrated_files: Dict[str, str] = field(default_factory=dict)   # filename → migrated content
    verification_result: Optional[Dict[str, Any]] = None

    # ---- agentic loop state (managed by agent.py) ----
    # Each phase maintains its own independent messages[] conversation history
    # so the LLM remembers every prior tool call within the phase.
    phase_messages: Dict[str, List[Dict]] = field(default_factory=dict)

    # Full audit log of every tool call made across all phases
    tool_calls_log: List[ToolCall] = field(default_factory=list)

    # Full audit log of every agentic loop iteration
    iterations: List[AgentIteration] = field(default_factory=list)

    # ---- errors ----
    errors: List[str] = field(default_factory=list)

    # ---- summary stats (populated after run completes) ----
    @property
    def iterations_count(self) -> int:
        return len(self.iterations)

    @property
    def tool_calls_count(self) -> int:
        return len(self.tool_calls_log)
