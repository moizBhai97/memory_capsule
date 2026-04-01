/**
 * Background service worker.
 * Handles context menu, sends captures to Memory Capsule API.
 */

// Create context menu items on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "capture-selection",
    title: "Capture selection → Memory Capsule",
    contexts: ["selection"],
  });

  chrome.contextMenus.create({
    id: "capture-page",
    title: "Capture this page → Memory Capsule",
    contexts: ["page"],
  });

  chrome.contextMenus.create({
    id: "capture-image",
    title: "Capture image → Memory Capsule",
    contexts: ["image"],
  });

  chrome.contextMenus.create({
    id: "capture-link",
    title: "Capture link → Memory Capsule",
    contexts: ["link"],
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const settings = await getSettings();

  if (info.menuItemId === "capture-selection" && info.selectionText) {
    await captureText(info.selectionText, tab.url, tab.title, settings);
  } else if (info.menuItemId === "capture-page") {
    await capturePage(tab.url, tab.title, settings);
  } else if (info.menuItemId === "capture-image" && info.srcUrl) {
    await captureUrl(info.srcUrl, tab.url, settings);
  } else if (info.menuItemId === "capture-link" && info.linkUrl) {
    await captureUrl(info.linkUrl, tab.url, settings);
  }
});

// Handle messages from popup and content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender).then(sendResponse);
  return true; // keep channel open for async response
});

async function handleMessage(message, sender) {
  const settings = await getSettings();

  switch (message.action) {
    case "capture-selection":
      return captureText(message.text, message.url, message.title, settings);
    case "capture-page":
      return capturePage(message.url, message.title, settings);
    case "capture-url":
      return captureUrl(message.url, message.sourceUrl, settings);
    case "test-connection":
      return testConnection(settings);
    default:
      return { error: "Unknown action" };
  }
}

async function captureText(text, pageUrl, pageTitle, settings) {
  try {
    const resp = await fetch(`${settings.apiUrl}/api/capsules`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(settings.apiKey ? { "X-Api-Key": settings.apiKey } : {}),
      },
      body: JSON.stringify({
        text,
        source_app: "browser",
        source_url: pageUrl,
        source_chat: pageTitle,
        metadata: { page_title: pageTitle, page_url: pageUrl },
      }),
    });

    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    notify("Captured!", `Text from "${pageTitle}" saved to memory.`);
    return { success: true };
  } catch (err) {
    notify("Capture failed", err.message);
    return { error: err.message };
  }
}

async function capturePage(url, title, settings) {
  try {
    const resp = await fetch(`${settings.apiUrl}/api/capsules`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(settings.apiKey ? { "X-Api-Key": settings.apiKey } : {}),
      },
      body: JSON.stringify({
        url,
        source_app: "browser",
        source_chat: title,
        metadata: { page_title: title },
      }),
    });

    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    notify("Captured!", `Page "${title}" saved to memory.`);
    return { success: true };
  } catch (err) {
    notify("Capture failed", err.message);
    return { error: err.message };
  }
}

async function captureUrl(url, sourceUrl, settings) {
  return capturePage(url, url, settings);
}

async function testConnection(settings) {
  try {
    const resp = await fetch(`${settings.apiUrl}/health`, {
      headers: settings.apiKey ? { "X-Api-Key": settings.apiKey } : {},
    });
    return { ok: resp.ok, status: resp.status };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

function notify(title, message) {
  chrome.notifications.create({
    type: "basic",
    iconUrl: "icons/icon48.png",
    title,
    message,
  });
}

async function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(
      { apiUrl: "http://localhost:8000", apiKey: "" },
      resolve
    );
  });
}
