# Memory Capsule Browser Extension

Capture any text, page, or link to your Memory Capsule from Chrome or Firefox with one click.

## Install (Developer Mode — until published to store)

### Chrome / Edge
1. Open `chrome://extensions`
2. Enable **Developer mode** (top right toggle)
3. Click **Load unpacked**
4. Select this `browser-extension/` folder
5. Pin the extension to your toolbar

### Firefox
1. Open `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on**
3. Select `manifest.json` from this folder

## Setup
1. Click the 🧠 icon in toolbar
2. Click **Settings**
3. Set your server URL (default: `http://localhost:8000`)
4. Save

## How to Use

### From popup
- Paste or type text → **Capture Text**
- Click **Capture This Page** to save the current page
- Click **Capture Selected Text** to save highlighted text

### Right-click context menu
- Select text on any page → Right click → **Capture selection → Memory Capsule**
- Right click any page → **Capture this page → Memory Capsule**
- Right click any image → **Capture image → Memory Capsule**
- Right click any link → **Capture link → Memory Capsule**

### Keyboard shortcut
- Select text on any page
- Press **Alt+Shift+C**
- Done — toast confirmation appears
