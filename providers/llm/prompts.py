"""
LLM prompts used across all provider implementations.
Centralised here so every provider uses the same extraction behaviour.
Future: make this user-configurable per deployment.
"""

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
