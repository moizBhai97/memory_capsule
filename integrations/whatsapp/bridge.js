/**
 * WhatsApp Web bridge — uses whatsapp-web.js to capture all messages/media.
 * Runs as a separate Node.js process alongside the Python daemon.
 *
 * Setup:
 *   cd integrations/whatsapp
 *   npm install
 *   node bridge.js
 *
 * First run: scan the QR code shown in terminal.
 * After that: session is saved, auto-reconnects on restart.
 */

const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");
const axios = require("axios");
const FormData = require("form-data");
const fs = require("fs");
const path = require("path");
const os = require("os");

const API_URL = process.env.MC_API_URL || "http://localhost:8000";
const API_KEY = process.env.MC_API_KEY || "";
const SESSION_PATH = process.env.MC_WA_SESSION_PATH || "../../data/whatsapp_session";

const HEADERS = API_KEY ? { "X-Api-Key": API_KEY } : {};

// Media types we capture
const CAPTURE_TYPES = ["audio", "image", "document", "video", "ptt"]; // ptt = push-to-talk (voice note)

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: SESSION_PATH }),
  puppeteer: {
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
  },
});

client.on("qr", (qr) => {
  console.log("\n=== Scan this QR code with your WhatsApp ===\n");
  qrcode.generate(qr, { small: true });
  console.log("\nOpen WhatsApp → Settings → Linked Devices → Link a Device\n");
});

client.on("ready", () => {
  console.log("✓ WhatsApp connected. Capturing messages automatically.");
});

client.on("disconnected", (reason) => {
  console.log("WhatsApp disconnected:", reason, "— reconnecting...");
  client.initialize();
});

client.on("message_create", async (message) => {
  // Skip messages sent by us (fromMe) — only capture received messages
  // Remove this check if you also want to capture your own messages
  if (message.fromMe) return;

  try {
    await handleMessage(message);
  } catch (err) {
    console.error("Error handling message:", err.message);
  }
});

async function handleMessage(message) {
  const contact = await message.getContact();
  const chat = await message.getChat();

  const senderName = contact.pushname || contact.name || contact.number || "Unknown";
  const chatName = chat.name || senderName;
  const timestamp = new Date(message.timestamp * 1000).toISOString();

  const metadata = {
    platform: "whatsapp_personal",
    from_number: message.from,
    message_id: message.id._serialized,
    chat_name: chatName,
    is_group: chat.isGroup,
    timestamp,
  };

  // Text message
  if (message.type === "chat" && message.body) {
    await sendText(message.body, senderName, chatName, metadata);
    return;
  }

  // Media message
  if (CAPTURE_TYPES.includes(message.type)) {
    await sendMedia(message, senderName, chatName, metadata);
  }
}

async function sendText(text, sender, chat, metadata) {
  try {
    await axios.post(
      `${API_URL}/api/webhooks/ingest`,
      {
        text,
        source_app: "whatsapp_personal",
        source_sender: sender,
        source_chat: chat,
        metadata,
      },
      { headers: HEADERS, timeout: 10000 }
    );
    console.log(`✓ Text captured from ${sender}`);
  } catch (err) {
    console.error("Failed to send text:", err.message);
  }
}

async function sendMedia(message, sender, chat, metadata) {
  let tmpPath = null;
  try {
    const media = await message.downloadMedia();
    if (!media || !media.data) return;

    // Determine file extension
    const ext = getExtension(message.type, media.mimetype);
    tmpPath = path.join(os.tmpdir(), `wa_${Date.now()}${ext}`);

    // Write to temp file
    fs.writeFileSync(tmpPath, Buffer.from(media.data, "base64"));

    // Send to API
    const form = new FormData();
    form.append("file", fs.createReadStream(tmpPath), {
      filename: path.basename(tmpPath),
      contentType: media.mimetype,
    });
    form.append("source_app", "whatsapp_personal");
    form.append("source_sender", sender);
    form.append("source_chat", chat);

    // Add caption as extra context if present
    if (message.body) {
      form.append("metadata", JSON.stringify({ ...metadata, caption: message.body }));
    } else {
      form.append("metadata", JSON.stringify(metadata));
    }

    await axios.post(`${API_URL}/api/capsules/upload`, form, {
      headers: { ...HEADERS, ...form.getHeaders() },
      timeout: 30000,
    });

    console.log(`✓ ${message.type} captured from ${sender}`);
  } catch (err) {
    console.error(`Failed to send media (${message.type}):`, err.message);
  } finally {
    if (tmpPath && fs.existsSync(tmpPath)) {
      fs.unlinkSync(tmpPath);
    }
  }
}

function getExtension(messageType, mimetype) {
  const mimeMap = {
    "audio/ogg; codecs=opus": ".ogg",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "application/pdf": ".pdf",
  };
  if (mimetype && mimeMap[mimetype]) return mimeMap[mimetype];
  if (messageType === "ptt" || messageType === "audio") return ".ogg";
  if (messageType === "image") return ".jpg";
  if (messageType === "video") return ".mp4";
  if (messageType === "document") return ".pdf";
  return ".bin";
}

console.log("Starting WhatsApp bridge...");
client.initialize();
