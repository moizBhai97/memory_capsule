"""
Anthropic LLM provider.

Uses Anthropic's tool_use feature to enforce structured JSON output.
"""

from ..base import LLMResult, LLMProvider
from .prompts import EXTRACTION_PROMPT, EXTRACTION_SCHEMA


class AnthropicLLM(LLMProvider):
    def __init__(self, api_key: str, model: str):
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            raise ImportError("Run: pip install anthropic")
        self.model = model

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
            "name": "extract_capsule_info",
            "description": "Extract structured memory capsule information from content",
            "input_schema": EXTRACTION_SCHEMA,
        }

        response = await self._client.messages.create(
            model=self.model,
            max_tokens=512,
            tools=[tool],
            tool_choice={"type": "tool", "name": "extract_capsule_info"},
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )

        # Anthropic returns tool_use blocks in content
        result = {}
        for block in response.content:
            if block.type == "tool_use":
                result = block.input
                break

        return LLMResult(
            summary=result.get("summary", ""),
            tags=[t.lower().replace(" ", "-") for t in result.get("tags", [])[:10]],
            action_items=result.get("action_items", []),
            language=result.get("language", "en"),
            reminders=result.get("reminders", []),
        )

    async def health_check(self) -> bool:
        return self._client is not None
