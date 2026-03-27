import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "claude-3-5-haiku-20241022"


class LLMClient:
    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.model = os.getenv("LLM_MODEL", DEFAULT_MODEL)
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        message = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text
