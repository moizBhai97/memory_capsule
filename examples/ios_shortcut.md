# iOS Share Sheet Setup

Share anything from any app on iPhone/iPad to Memory Capsule in one tap.
Uses the built-in **Shortcuts** app — no extra install needed.

## Setup (5 minutes, one time)

1. Open the **Shortcuts** app
2. Tap **+** (new shortcut)
3. Tap **Add Action** → search for **URL**
4. Set URL to: `http://YOUR_SERVER_IP:8000/api/capsules/upload`

### For file sharing:

Add these actions in order:
1. **Receive** → `Any` (from Share Sheet)
2. **Get File** from input
3. **Get Contents of URL** (POST):
   - URL: `http://YOUR_SERVER_IP:8000/api/capsules/upload`
   - Method: POST
   - Request Body: Form
     - `file` → Shortcut Input
     - `source_app` → `ios_share`

### For text sharing:

1. **Receive** → `Text` (from Share Sheet)
2. **Get Contents of URL** (POST):
   - URL: `http://YOUR_SERVER_IP:8000/api/webhooks/ingest`
   - Method: POST
   - Request Body: JSON
     ```json
     {
       "text": "[Shortcut Input]",
       "source_app": "ios_share"
     }
     ```

5. Name the shortcut: **Memory Capsule**
6. In shortcut settings → enable **Show in Share Sheet**

## How to use

From **any app** (WhatsApp, Mail, Files, Photos, Safari):
1. Tap the Share button
2. Scroll down → tap **Memory Capsule**
3. Done

## Works with
- Voice notes shared from WhatsApp
- Photos and screenshots
- PDFs from Mail
- Text selections from Safari
- Files from iCloud Drive
