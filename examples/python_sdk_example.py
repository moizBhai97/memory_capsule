"""
Open Memory Capsule — Python SDK examples
"""

from memory_capsule import MemoryCapsule

mc = MemoryCapsule(base_url="http://localhost:8000")

# --- Capture ---

# From a file
mc.add(file="voice_note.ogg", sender="Ahmed", source="whatsapp_personal")
mc.add(file="invoice.pdf", sender="client@company.com", source="email", chat="Q1 Invoice")
mc.add(file="screenshot.png", source="api")

# From text
mc.add(text="Client confirmed $15k budget for website", sender="Ahmed", source="whatsapp_personal")

# From URL
mc.add(url="https://example.com/article", source="browser")

# With extra metadata
mc.add(
    text="Meeting agreed to launch by April 30",
    source="zoom",
    chat="Product Sync",
    metadata={"meeting_id": "abc123", "duration_minutes": 45},
)

# --- Search ---

# Natural language — date expressions work automatically
results = mc.search("quote from Ahmed")
results = mc.search("invoice last month")
results = mc.search("what did we decide 2 weeks ago")
results = mc.search("bank slip from March")

# With filters
results = mc.search("project budget", source="whatsapp_personal", limit=5)
results = mc.search("meeting notes", source_type="audio")
results = mc.search("invoice", from_date="2024-03-01", to_date="2024-03-31")

# Display results
for r in results:
    print(f"[{r.source_app}] {r.timestamp[:10]}")
    if r.source_sender:
        print(f"  From: {r.source_sender}")
    print(f"  {r.snippet}")
    print(f"  Tags: {', '.join(r.tags)}")
    if r.action_items:
        print(f"  Actions: {', '.join(r.action_items)}")
    print()

# --- List recent ---
recent = mc.list(limit=10)
for c in recent:
    print(f"{c.timestamp[:10]} [{c.source_app}] {c.summary[:60]}")

# --- Use as context manager ---
with MemoryCapsule() as mc:
    mc.add(text="Quick note to self")
    results = mc.search("quick note")
