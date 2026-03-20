"""Supervisor agent that coordinates workers."""
from typing import Dict, List
from agents import ResearcherAgent, WriterAgent, ReviewerAgent

SUPERVISOR_PROMPT = """You are a supervisor managing a team of specialized agents.

Available agents:
- Researcher: Finds and summarizes information
- Writer: Creates polished content from research
- Reviewer: Reviews content for quality

You MUST follow this exact order for every task:
1. First, ALWAYS delegate to Researcher to gather information on the topic.
2. Then, ALWAYS delegate to Writer to turn that research into polished output.
3. Finally, output FINAL with the Writer's content as the result.

Do NOT skip the Researcher step. Do NOT output FINAL before both Researcher and Writer have run.

For each delegation step, output ONLY this format (nothing else):
DELEGATE: [agent_name]
TASK: [specific task for that agent]

After Writer has produced output, synthesize and output:
FINAL: [final polished content]"""


class SupervisorAgent:
    """Supervisor that coordinates worker agents."""

    def __init__(self, llm_client):
        self.llm = llm_client

        # Initialize workers
        self.workers = {
            "Researcher": ResearcherAgent(llm_client),
            "Writer": WriterAgent(llm_client),
            "Reviewer": ReviewerAgent(llm_client)
        }

        self.results: Dict[str, str] = {}

    def run(self, task: str, max_iterations: int = 5) -> str:
        """Run the multi-agent workflow."""
        messages = [
            {"role": "system", "content": SUPERVISOR_PROMPT},
            {"role": "user", "content": f"Task: {task}"}
        ]

        for i in range(max_iterations):
            # Get supervisor decision
            response = self.llm.chat(messages)
            messages.append({"role": "assistant", "content": response})

            # Check if done
            if "FINAL:" in response:
                final = response.split("FINAL:")[-1].strip()
                return final

            # Parse and execute delegation
            if "DELEGATE:" in response and "TASK:" in response:
                agent_name = response.split("DELEGATE:")[-1].split("TASK:")[0].strip()
                agent_task = response.split("TASK:")[-1].strip()

                if agent_name in self.workers:
                    # Execute worker
                    context = self._get_context()
                    result = self.workers[agent_name].execute(agent_task, context)

                    # Store result
                    self.results[f"{agent_name}_{i}"] = result

                    # Feed back to supervisor
                    messages.append({
                        "role": "user",
                        "content": f"Result from {agent_name}:\n{result}"
                    })

        return self._force_final()

    def _get_context(self) -> str:
        """Build context from previous results."""
        if not self.results:
            return ""

        parts = []
        for key, value in self.results.items():
            parts.append(f"--- {key} ---\n{value}")
        return "\n\n".join(parts)

    def _force_final(self) -> str:
        """Force final output if max iterations reached."""
        if self.results:
            # Return last writer result if available
            writer_results = [v for k, v in self.results.items() if "Writer" in k]
            if writer_results:
                return writer_results[-1]

            # Otherwise return last result
            return list(self.results.values())[-1]

        return "Unable to complete task."
