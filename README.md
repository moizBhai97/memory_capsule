<div align="center">

# 🧠 Open Memory Capsule

### Your memory, running in the background. Ask it anything.

**Capture everything. Remember forever. Search naturally.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

## The Problem

You lose important context every day.

- A client sends a voice note on WhatsApp → you forget what they said
- A PDF quote arrives by email → buried in your inbox
- A screenshot of a bank slip → lost in your camera roll
- A meeting recording → never reviewed
- A random idea you voice-noted to yourself at 2am → gone

None of these fit neatly into a note app. You're not going to "organize" them. They just disappear.

---

## What This Is

**Open Memory Capsule is not a note app.**

It's a passive background daemon that:
1. **Automatically captures** content from everywhere you already are — WhatsApp, email, Telegram, your files, meeting recordings
2. **Processes it silently** — transcribes audio, reads images, parses PDFs, extracts meaning
3. **Makes it searchable forever** — ask in plain English, get answers

> "Show me that quote Ahmed sent about the website project 2 weeks ago"
> → Returns the WhatsApp voice note transcript with the exact price, automatically tagged with Ahmed's name, project, and amount.

**You set it up once. Then forget it exists. Until you need something.**

---

## How It Works

```
Your existing apps (unchanged)
        │
        ▼
┌───────────────────────────────────────────────┐
│           Capture Layer (automatic)           │
│                                               │
│  WhatsApp ──┐                                 │
│  Telegram ──┤                                 │
│  Email ─────┼──→ Normalizer → Standard Input  │
│  Screenshots┤                                 │
│  Downloads ─┤                                 │
│  Zoom ──────┘                                 │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│           Processing Pipeline                 │
│                                               │
│  Audio → Whisper (transcribe)                 │
│  Image → EasyOCR (extract text)               │
│  PDF   → PyMuPDF (parse)                      │
│  Text  → cleaned & normalized                 │
│       ↓                                       │
│  LLM  → summary + tags + action items         │
│  Embed → nomic-embed-text (vector)            │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│           Storage (local, private)            │
│                                               │
│  SQLite ── metadata, full text, tags          │
│  ChromaDB ─ embeddings for semantic search    │
│  Files ──── original files preserved          │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│           Search                              │
│                                               │
│  "quote from Ahmed 2 weeks ago"               │
│       ↓                                       │
│  NLP date parser + vector search + filters    │
│       ↓                                       │
│  Ranked results with context                  │
└───────────────────────────────────────────────┘
```

---

## Features

### Capture (Automatic — zero effort after setup)
- **WhatsApp Personal** — QR scan once, captures all messages & media silently
- **WhatsApp Business** — Official Meta API webhook
- **Telegram** — Userbot watches all your chats automatically
- **Email** — IMAP IDLE push: Gmail, Outlook, Yahoo, ProtonMail, any IMAP
- **Screenshots** — Auto-watches your OS screenshot folder
- **Downloads** — Auto-watches your Downloads folder
- **Zoom recordings** — Watches local Zoom recordings folder
- **Watch folders** — Any folder you specify (works with Dropbox, Drive, OneDrive)

### Capture (One-tap)
- **Android** — Share sheet via HTTP Shortcuts app → any app
- **iPhone** — iOS Shortcut → share from any app
- **Browser** — Chrome/Firefox extension: highlight text + 1 click (or Alt+Shift+C)
- **Slack** — Bot watches specific channels
- **Discord** — Bot watches specific channels

### Processing
- Audio transcription with Whisper (auto language detection)
- Image & screenshot OCR with EasyOCR
- PDF text extraction with PyMuPDF
- AI summary, tags, action items extracted per capsule
- Sender/source context preserved (who sent it, from where)

### Search
- Natural language queries: *"invoice from client last month"*
- Semantic similarity search (vector)
- Keyword search
- Date range: *"2 weeks ago"*, *"last Tuesday"*, *"March"*
- Filter by source: *"WhatsApp voice notes"*, *"emails from Ahmed"*

### Integration Surface (for builders)
- REST API — integrate from any language
- Webhooks — receive from Zapier, n8n, Make.com
- Python SDK — `pip install open-memory-capsule`
- JavaScript SDK — `npm install open-memory-capsule`
- CLI — `capsule search "quote from Ahmed"`

---

## Quick Start

### Option 1: Docker (Recommended — one command)

```bash
git clone https://github.com/yourusername/open-memory-capsule
cd open-memory-capsule
cp config.yaml config.local.yaml
# Edit config.local.yaml to enable integrations you want
docker compose up -d
```

That's it. Open `http://localhost:8000` to verify it's running.

### Option 2: Local Python

**Requirements:** Python 3.10+, [Ollama](https://ollama.ai) installed

```bash
git clone https://github.com/yourusername/open-memory-capsule
cd open-memory-capsule

# Install (makes 'capsule' command available globally)
pip install -e .

# Pull required AI models (one time, ~2GB)
ollama pull phi3.5:mini
ollama pull nomic-embed-text

# Copy and edit config
cp config.yaml config.local.yaml

# Run
python -m daemon    # background daemon (watchers + processor)
python -m api.main  # REST API (separate terminal)

# CLI is now available
capsule status
capsule search "quote from Ahmed"
capsule add file.pdf
```

---

## Configuration

Copy `config.yaml` to `config.local.yaml` (gitignored) and edit:

```yaml
# Which AI provider to use
# ollama = free, local, runs on your GPU
# openai / anthropic / groq = paid, cloud, better quality
provider: ollama

# Connect your platforms (enable what you use)
integrations:
  # Personal WhatsApp — scan QR once, captures everything automatically
  whatsapp_enabled: false

  # WhatsApp Business API (if you have a business account)
  whatsapp_business_enabled: false
  whatsapp_business_token: "your_token"
  whatsapp_business_phone_id: "your_phone_id"
  whatsapp_business_verify_token: "your_verify_token"

  # Telegram — enter phone number once, captures all chats automatically
  telegram_enabled: false
  telegram_api_id: "your_api_id"
  telegram_api_hash: "your_api_hash"
  telegram_phone: "+1234567890"

  # Email — works with Gmail, Outlook, Yahoo, any IMAP provider
  email_enabled: false
  email_host: "imap.gmail.com"
  email_username: "you@gmail.com"
  email_password: "your_app_password"  # use app-specific password

  # Auto-watch these folders (any path, including synced cloud folders)
  watch_downloads: true    # your Downloads folder
  watch_screenshots: true  # your Screenshots folder
  watch_folders:
    - "/path/to/any/folder"
    - "/path/to/dropbox/CapsuleInbox"

  # Zoom — auto-captures local recordings
  zoom_enabled: false
  zoom_recordings_path: "~/Documents/Zoom"
```

All sensitive values can also be set as environment variables:

```bash
OPENAI_API_KEY=sk-...
MC_TELEGRAM_API_ID=12345
MC_EMAIL_PASSWORD=...
```

---

## AI Providers

| Provider | Cost | Quality | Privacy | Setup |
|----------|------|---------|---------|-------|
| **Ollama (default)** | Free | Good | 100% local | Install Ollama |
| **Groq** | Free tier | Great | Cloud | API key |
| **OpenAI** | Paid | Best | Cloud | API key |
| **Anthropic** | Paid | Best | Cloud | API key |

Switch provider in one line:
```yaml
provider: groq  # free, fast, cloud
```

---

## REST API

Full API docs at `http://localhost:8000/docs` after starting.

### Capture content

```bash
# Upload a file
curl -X POST http://localhost:8000/api/capsules/upload \
  -F "file=@voice_note.ogg" \
  -F "source_app=whatsapp" \
  -F "source_sender=Ahmed"

# Send text/URL
curl -X POST http://localhost:8000/api/capsules \
  -H "Content-Type: application/json" \
  -d '{"text": "Quote for website project: $15,000", "source_app": "manual"}'
```

### Search

```bash
# Natural language search
curl "http://localhost:8000/api/search?q=quote+from+Ahmed&limit=5"

# With date filter
curl "http://localhost:8000/api/search?q=invoice&from_date=2024-03-01&to_date=2024-03-31"

# Filter by source
curl "http://localhost:8000/api/search?q=project+price&source_app=whatsapp"
```

### Webhook receiver (for Zapier, n8n, Make)

```bash
# Any platform can POST to this endpoint
curl -X POST http://localhost:8000/api/webhooks/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Client confirmed $15k budget",
    "source_app": "zapier",
    "metadata": {"zap_name": "Gmail to Capsule"}
  }'
```

---

## Python SDK

```python
from memory_capsule import MemoryCapsule

mc = MemoryCapsule(base_url="http://localhost:8000")

# Capture
mc.add(file="voice_note.ogg", source_app="whatsapp", sender="Ahmed")
mc.add(text="Project budget confirmed at 15k", source_app="meeting")

# Search
results = mc.search("quote from Ahmed")
for r in results:
    print(r.summary)
    print(r.tags)
    print(r.action_items)
```

---

## JavaScript SDK

```javascript
import { MemoryCapsule } from 'open-memory-capsule'

const mc = new MemoryCapsule({ baseUrl: 'http://localhost:8000' })

// Capture
await mc.add({ text: 'Client confirmed budget', sourceApp: 'slack' })

// Search
const results = await mc.search('quote from Ahmed last week')
console.log(results[0].summary)
```

---

## Integrations Guide

### WhatsApp Personal Setup
1. Enable in `config.local.yaml`: `whatsapp_enabled: true`
2. Start daemon: `python -m daemon`
3. In a separate terminal: `cd integrations/whatsapp && npm install && node bridge.js`
4. Scan QR code shown in terminal (one time only)
5. Done — all new messages & media captured automatically

### WhatsApp Business Setup
1. Create [Meta Developer Account](https://developers.facebook.com)
2. Set up WhatsApp Business API (free up to 1000 conversations/month)
3. Set webhook URL to `http://yourserver:8000/api/webhooks/whatsapp-business`
4. Add credentials to `config.local.yaml`

### Telegram Setup
1. Get API credentials at [my.telegram.org](https://my.telegram.org)
2. Add to config: `telegram_api_id`, `telegram_api_hash`, `telegram_phone`
3. Enable: `telegram_enabled: true`
4. First run: enter OTP sent to your Telegram
5. Done — all chats captured automatically

### Gmail / Email Setup
1. For Gmail: enable IMAP + create [App Password](https://myaccount.google.com/apppasswords)
2. For Outlook: enable IMAP in settings
3. For any IMAP provider: use your email credentials
4. Add to config, enable `email_enabled: true`

### n8n Setup
1. Import the ready-made workflow from [`examples/n8n_workflow.json`](examples/n8n_workflow.json)
   - Open n8n → **Workflows** → **Import from file**
2. Replace `YOUR_SERVER` with your server URL in the HTTP Request nodes
3. Connect your Gmail (or any trigger) credentials
4. Activate the workflow

Or manually: add an **HTTP Request** node to any existing workflow:
- Method: `POST`
- URL: `http://yourserver:8000/api/webhooks/ingest`
- Body (JSON):
```json
{
  "text": "{{ $json.body }}",
  "source_app": "n8n",
  "source_sender": "{{ $json.from }}",
  "metadata": {}
}
```

### Zapier / Make.com
See full setup guide in [`examples/zapier_setup.md`](examples/zapier_setup.md).

Point any Zap/scenario action to: `POST http://yourserver:8000/api/webhooks/ingest`

### Browser Extension Setup (Chrome / Firefox / Edge)
1. Open `chrome://extensions` → enable **Developer mode**
2. Click **Load unpacked** → select the `browser-extension/` folder
3. Click 🧠 in toolbar → Settings → set your server URL
4. Done — right-click anything on any page to capture it

See [`browser-extension/README.md`](browser-extension/README.md) for Firefox and full usage guide.

### Android Share Sheet
1. Install [HTTP Shortcuts](https://http-shortcuts.rmy.ch/) app (free)
2. Follow setup guide in [`examples/android_shortcut.md`](examples/android_shortcut.md)
3. Long-press any file/text in any app → Share → Memory Capsule
4. Done

### iOS Shortcut
1. Follow setup guide in [`examples/ios_shortcut.md`](examples/ios_shortcut.md)
2. Share from any app → Memory Capsule

### Slack Bot Setup
1. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps)
2. Add Bot Token Scopes: `channels:history`, `files:read`, `users:read`
3. Install to workspace, copy Bot Token
4. Add to config: `slack_bot_token`, `slack_channel_ids`, enable `slack_enabled: true`
5. Invite bot to channels you want to watch: `/invite @MemoryCapsule`

### Discord Bot Setup
1. Create a bot at [discord.com/developers/applications](https://discord.com/developers/applications)
2. Enable: Message Content Intent, Server Members Intent
3. Invite bot with Read Messages + Read Message History permissions
4. Add to config: `discord_bot_token`, `discord_channel_ids`, enable `discord_enabled: true`

---

## Security & Privacy

**Your data never leaves your machine by default.**

| What | How |
|------|-----|
| All storage | Local SQLite + ChromaDB on your machine |
| All AI processing | Local via Ollama — no data sent anywhere |
| Credentials | Never stored in plaintext — use env vars or OS keychain |
| WhatsApp session | Encrypted locally, same as WhatsApp Web |
| API access | Optional API key auth for your REST API |
| Network | Runs on localhost by default, not exposed to internet |

**If you use cloud AI providers (OpenAI/Anthropic):**
- Only the text content of capsules is sent for processing
- Credentials are never sent
- You control this via the `provider` setting

**Want end-to-end local?**
```yaml
provider: ollama   # everything stays on your machine
```

---

## Hardware Requirements

| Setup | Minimum | Recommended |
|-------|---------|-------------|
| CPU only | 8GB RAM | 16GB RAM |
| GPU (local AI) | 4GB VRAM (RTX 3050) | 8GB VRAM |
| Storage | 5GB free | 20GB free |

**Tested on RTX 3050 4GB** — Whisper small + Phi3.5 mini + nomic-embed fit comfortably.

---

## Comparison

| Feature | Open Memory Capsule | Notion | Obsidian | Mem.ai | Rewind.ai |
|---------|--------------------|----|--------|--------|-----------|
| Auto-capture from WhatsApp | ✅ | ❌ | ❌ | ❌ | ❌ |
| Auto-capture from Email | ✅ | ❌ | ❌ | ❌ | ❌ |
| Auto-capture from Telegram | ✅ | ❌ | ❌ | ❌ | ❌ |
| Zero manual input | ✅ | ❌ | ❌ | ❌ | Partial |
| Fully local / private | ✅ | ❌ | ✅ | ❌ | ✅ |
| Open source | ✅ | ❌ | ✅ | ❌ | ❌ |
| Natural language search | ✅ | Basic | Plugin | ✅ | ✅ |
| Free forever | ✅ | Partial | ✅ | ❌ | ❌ |
| Self-hostable | ✅ | ❌ | ✅ | ❌ | ❌ |
| Runs on local GPU | ✅ | — | — | — | Mac only |

---

## Roadmap

### v0.1 (Shipped)
- [x] Core pipeline (ingest → process → store → search)
- [x] Watch folder daemon (auto-watches Downloads + Screenshots)
- [x] Email integration (IMAP — Gmail, Outlook, Yahoo, any)
- [x] Telegram userbot (all chats, automatic)
- [x] WhatsApp Personal (whatsapp-web.js bridge)
- [x] WhatsApp Business API webhook
- [x] Slack bot
- [x] Discord bot
- [x] REST API + webhooks (Zapier, n8n, Make compatible)
- [x] CLI (`capsule add / search / list / status`)
- [x] Python SDK
- [x] JavaScript SDK
- [x] Docker setup (one-command)
- [x] Android share sheet guide
- [x] iOS Shortcut guide
- [x] n8n + Zapier integration examples

### v0.2 (Next)
- [ ] Web UI (search interface — React or plain HTML)
- [ ] Browser extension (Chrome/Firefox — highlight + capture)
- [ ] Zoom recording webhook
- [ ] Google Drive folder watcher
- [ ] Reminder notifications (system tray / push)
- [ ] Google Meet / Teams via Recall.ai (paid integration)

### v0.3 (Community)
- [ ] Mobile app (React Native — iOS + Android)
- [ ] Multi-user / team sharing (paid)
- [ ] Cloud sync across devices (paid)
- [ ] MCP tool — let Claude/ChatGPT query your memory directly
- [ ] Calendar integration (auto-capture meeting context)
- [ ] OpenClaw skill — query your memory capsule from any chat app via OpenClaw assistant

---

## Contributing

Contributions are very welcome. This is built to be community-extensible.

**Easiest ways to contribute:**
- Add a new integration (see `/integrations` — each is a self-contained module)
- Add a new AI provider (see `/providers` — implement the base interface)
- Improve search ranking
- Build the web UI
- Write tests
- Translate docs

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT — free for personal and commercial use.

---

## Star History

If this project helps you, please star it. It helps others find it.

---

<div align="center">
Built by the community, for anyone who has ever lost an important message.
</div>
