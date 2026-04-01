#!/bin/bash
# Open Memory Capsule — cURL examples
# Replace http://localhost:8000 with your server URL

BASE_URL="http://localhost:8000"

# --- Health check ---
curl "$BASE_URL/health"

# --- Upload a voice note ---
curl -X POST "$BASE_URL/api/capsules/upload" \
  -F "file=@voice_note.ogg" \
  -F "source_app=whatsapp_personal" \
  -F "source_sender=Ahmed"

# --- Upload a PDF ---
curl -X POST "$BASE_URL/api/capsules/upload" \
  -F "file=@invoice.pdf" \
  -F "source_app=email" \
  -F "source_sender=client@company.com" \
  -F "source_chat=Project Invoice"

# --- Capture text ---
curl -X POST "$BASE_URL/api/capsules" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Client confirmed budget is $15k for the website project",
    "source_app": "whatsapp_personal",
    "source_sender": "Ahmed Hassan",
    "source_chat": "Ahmed Client"
  }'

# --- Capture a URL ---
curl -X POST "$BASE_URL/api/capsules" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article", "source_app": "browser"}'

# --- Natural language search ---
curl "$BASE_URL/api/search?q=quote+from+Ahmed"

# --- Search with date filter ---
curl "$BASE_URL/api/search?q=invoice+last+month&source_app=email"

# --- Search within date range ---
curl "$BASE_URL/api/search?q=project+budget&from_date=2024-03-01&to_date=2024-03-31"

# --- List recent capsules ---
curl "$BASE_URL/api/capsules?limit=10"

# --- Filter by source ---
curl "$BASE_URL/api/capsules?source_app=telegram&limit=20"

# --- Generic webhook (Zapier, n8n, Make) ---
curl -X POST "$BASE_URL/api/webhooks/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "New lead from contact form: John Smith, budget $20k",
    "source_app": "zapier",
    "source_sender": "Contact Form",
    "metadata": {"zap_id": "123", "form_name": "Contact"}
  }'
