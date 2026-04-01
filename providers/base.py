"""
Provider interfaces.
Every AI provider (Ollama, OpenAI, Anthropic, Groq) implements these.
Swap providers via config — zero code changes elsewhere.

Future: these interfaces are MCP-tool-ready and LangChain-compatible by design.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ExtractionResult:
    """Structured output from LLM processing a capsule."""
    summary: str
    tags: list[str]
    action_items: list[str]
    language: str = "en"
    reminders: list[dict] = None

    def __post_init__(self):
        if self.reminders is None:
            self.reminders = []


class LLMProvider(ABC):
    """
    Interface for LLM calls.
    One method: extract_capsule_info — given raw text + context, return structured data.
    Future: add chat(), stream() when MCP or agent orchestration is needed.
    """

    @abstractmethod
    async def extract_capsule_info(
        self,
        raw_content: str,
        source_app: str,
        source_sender: str | None = None,
        source_type: str = "unknown",
    ) -> ExtractionResult:
        """
        Given raw text from a capsule, extract:
        - A concise summary
        - Relevant tags (people, topics, amounts, companies, dates)
        - Action items if any
        - Detected language
        - Any reminders/deadlines mentioned
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Returns True if provider is reachable and working."""
        ...


class EmbedProvider(ABC):
    """
    Interface for text embeddings.
    Future: swap nomic-embed for OpenAI embeddings or any other model in one line.
    """

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts. More efficient than calling embed() in a loop."""
        ...

    @abstractmethod
    def dimension(self) -> int:
        """Return embedding vector dimension. Needed by ChromaDB on collection creation."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


# --- Shared prompt --- #
# Keeping the prompt here so all providers use the same one.
# Future: make this configurable per user for custom extraction behavior.

EXTRACTION_PROMPT = """You are a personal memory assistant. Your job is to extract structured information from content a user has captured.

Source: {source_app}
{sender_line}
Content type: {source_type}

Content:
{raw_content}

Extract the following as JSON. Be concise. Do not invent information not present in the content.

{{
  "summary": "1-2 sentence summary of what this content is about",
  "tags": ["list", "of", "relevant", "tags"],
  "action_items": ["any tasks or follow-ups mentioned, empty list if none"],
  "language": "2-letter language code of the content (en, ar, fr, etc.)",
  "reminders": [
    {{"date": "YYYY-MM-DD or relative like 'Friday'", "note": "what to remember"}}
  ]
}}

Tag guidelines:
- Include: person names, company names, project names, amounts/prices, topics, platform names
- Keep tags lowercase, use hyphens for spaces (e.g. "ahmed-hassan", "website-project")
- Max 10 tags
- Only include reminders if a specific date/deadline is mentioned

Respond with valid JSON only. No explanation."""
