"""
LLM prompts and output schema used across all provider implementations.
Centralised here so every provider uses the same extraction behaviour.
"""

# User-facing instruction — no JSON format instructions needed here because
# each provider enforces structure via its native mechanism (tool calling /
# response schema / json_schema response format), not via prompt.
EXTRACTION_PROMPT = """You are a personal memory assistant. Extract structured information from the content below.

Source: {source_app}
{sender_line}
Content type: {source_type}

Content:
{raw_content}

Tag guidelines:
- Include: person names, company names, project names, amounts/prices, topics, platform names
- Keep tags lowercase, use hyphens for spaces (e.g. "ahmed-hassan", "website-project")
- Max 10 tags
- Only include reminders if a specific date/deadline is explicitly mentioned
- Be concise. Do not invent information not present in the content."""


# JSON Schema for LLMResult — passed to each provider's native structured
# output API so the model is forced to conform, not just prompted to.
EXTRACTION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "1-2 sentence summary of what this content is about",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Relevant tags: people, companies, projects, amounts, topics",
        },
        "action_items": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tasks or follow-ups mentioned. Empty list if none.",
        },
        "language": {
            "type": "string",
            "description": "2-letter ISO language code of the content (en, ar, fr, etc.)",
        },
        "reminders": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD or relative like 'Friday'"},
                    "note": {"type": "string", "description": "What to remember"},
                },
                "required": ["date", "note"],
                "additionalProperties": False,
            },
            "description": "Only if a specific date/deadline is mentioned. Empty list otherwise.",
        },
    },
    "required": ["summary", "tags", "action_items", "language", "reminders"],
    "additionalProperties": False,
}
