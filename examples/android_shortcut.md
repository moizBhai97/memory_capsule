# Android Share Sheet Setup

Share anything from any app on Android to Memory Capsule in one tap.
No app needed — uses [HTTP Shortcuts](https://http-shortcuts.rmy.ch/) (free, open source).

## Setup (5 minutes, one time)

1. Install **HTTP Shortcuts** from the Play Store (free)
2. Open HTTP Shortcuts → tap **+** → **Regular Shortcut**
3. Configure:

**Basic Settings:**
- Name: `Memory Capsule`
- Method: `POST`
- URL: `http://YOUR_SERVER_IP:8000/api/capsules/upload`

**Request Body** (select: Form Data):
```
file    → {shared_file}
source_app → android_share
```

**For text sharing** (create a second shortcut):
- URL: `http://YOUR_SERVER_IP:8000/api/webhooks/ingest`
- Body (JSON):
```json
{
  "text": "{shared_text}",
  "source_app": "android_share"
}
```

4. Tap **Save**
5. In HTTP Shortcuts settings → **Allow sharing** → enable

## How to use

From **any app** (WhatsApp, Signal, Files, Camera, Chrome):
1. Long press any file, image, or text
2. Tap **Share**
3. Select **Memory Capsule**
4. Done — captured automatically

## Works with
- WhatsApp voice notes (share → Memory Capsule)
- Downloaded files
- Screenshots from gallery
- Text from any app
- Images
- PDFs
