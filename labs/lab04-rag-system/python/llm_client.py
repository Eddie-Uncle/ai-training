"""LLM client abstraction for the RAG system."""
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], system: str = "") -> str:
        """Send messages and return response text."""
        pass

    def chat_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict],
        system: str = "",
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Send messages with tool definitions. Returns dict with 'content' and 'stop_reason'."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support tool-use")


class AnthropicClient(LLMClient):
    """Anthropic Claude client."""

    def __init__(self, model: str = None):
        from anthropic import Anthropic
        self.client = Anthropic()
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

    def chat(self, messages: List[Dict[str, str]], system: str = "") -> str:
        """Plain text chat."""
        filtered = []
        sys_text = system
        for m in messages:
            if m["role"] == "system":
                sys_text = m["content"]
            else:
                filtered.append(m)
        kwargs: Dict[str, Any] = {}
        if sys_text:
            kwargs["system"] = sys_text
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=filtered,
            **kwargs
        )
        return response.content[0].text

    def chat_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict],
        system: str = "",
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages,
            tools=tools,
            **kwargs
        )

        content_blocks: List[Dict] = []
        for block in response.content:
            if block.type == "text":
                content_blocks.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                content_blocks.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        return {
            "content": content_blocks,
            "stop_reason": response.stop_reason,
        }


class OpenAIClient(LLMClient):
    """OpenAI client."""

    def __init__(self, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI()
        self.model = model

    def chat(self, messages: List[Dict[str, str]], system: str = "") -> str:
        msgs = ([{"role": "system", "content": system}] + list(messages)
                if system else list(messages))
        response = self.client.chat.completions.create(
            model=self.model,
            messages=msgs
        )
        return response.choices[0].message.content


class GoogleClient(LLMClient):
    """Google Generative AI client (Gemini)."""

    def __init__(self, model: str = "models/gemini-2.5-flash"):
        import google.generativeai as genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def chat(self, messages: List[Dict[str, str]], system: str = "") -> str:
        sys_text = system
        user_message = ""
        for m in messages:
            if m["role"] == "system":
                sys_text = m["content"]
            elif m["role"] == "user":
                user_message = m["content"]
        prompt = f"{sys_text}\n\n{user_message}" if sys_text else user_message
        response = self.model.generate_content(prompt)
        return response.text


def get_llm_client(provider: str = "anthropic") -> LLMClient:
    """Factory function to create LLM client."""
    providers = {
        "anthropic": AnthropicClient,
        "openai": OpenAIClient,
        "google": GoogleClient,
    }

    if provider not in providers:
        raise ValueError(f"Unknown provider: {provider}. Available: {list(providers.keys())}")

    return providers[provider]()
