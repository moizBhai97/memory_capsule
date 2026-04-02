"""
OpenAI-compatible LLM provider.

Handles any provider that speaks the OpenAI Chat Completions API:
  - openai/*            → api.openai.com
  - groq/*              → api.groq.com/openai/v1
  - ollama/*            → localhost:11434/v1
  - openai-compatible/* → user-supplied base_url

JSON output is enforced via tool calling (function calling) — not prompt instructions.
This works across all OpenAI-compatible backends including Ollama.
"""

import json
import logging

from ..base import LLMResult, LLMProvider
from .prompts import EXTRACTION_PROMPT, EXTRACTION_SCHEMA
from config import ProviderConfig
from .._openai_client import build_openai_client

logger = logging.getLogger(__name__)


def _parse_tool_result(response) -> dict:
    """Extract the tool call arguments dict from a chat completion response."""
    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        return json.loads(tool_calls[0].function.arguments)
    # Fallback: model returned text instead of a tool call (shouldn't happen)
    content = response.choices[0].message.content or "{}"
    return json.loads(content)


class OpenAICompatibleLLM(LLMProvider):
    """
    LLM provider for all OpenAI-compatible backends.
    Uses tool calling to enforce structured JSON output — no if-else per provider.
    """

    def __init__(self, cfg: ProviderConfig):
        self._client = build_openai_client(cfg)
        self.model = cfg.model_id
        self.provider_id = cfg.provider_id

    async def extract_capsule_info(
        self,
        raw_content: str,
        source_app: str,
        source_sender: str | None = None,
        source_type: str = "unknown",
    ) -> LLMResult:
        sender_line = f"Sender: {source_sender}" if source_sender else ""
        prompt = EXTRACTION_PROMPT.format(
            source_app=source_app,
            sender_line=sender_line,
            source_type=source_type,
            raw_content=raw_content[:8000],
        )

        tool = {
            "type": "function",
            "function": {
                "name": "extract_capsule_info",
                "description": "Extract structured memory capsule information from content",
                "parameters": EXTRACTION_SCHEMA,
            },
        }

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            tools=[tool],
            tool_choice={"type": "function", "function": {"name": "extract_capsule_info"}},
            temperature=0.1,
            max_tokens=512,
        )

        result = _parse_tool_result(response)
        return LLMResult(
            summary=result.get("summary", ""),
            tags=[t.lower().replace(" ", "-") for t in result.get("tags", [])[:10]],
            action_items=result.get("action_items", []),
            language=result.get("language", "en"),
            reminders=result.get("reminders", []),
        )

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
