/**
 * Popup UI logic.
 */

const statusDot = document.getElementById("status-dot");
const statusMsg = document.getElementById("status-msg");
const textInput = document.getElementById("text-input");

// Check connection on open
chrome.runtime.sendMessage({ action: "test-connection" }, (resp) => {
  if (resp?.ok) {
    statusDot.classList.remove("offline");
    statusDot.title = "Connected";
  } else {
    statusDot.classList.add("offline");
    statusDot.title = "Cannot reach Memory Capsule API";
  }
});

// Capture typed/pasted text
document.getElementById("btn-capture-text").addEventListener("click", async () => {
  const text = textInput.value.trim();
  if (!text) return;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  setStatus("Capturing...");

  chrome.runtime.sendMessage({
    action: "capture-selection",
    text,
    url: tab?.url || "",
    title: tab?.title || "",
  }, (resp) => {
    if (resp?.success) {
      textInput.value = "";
      setStatus("Captured!", false);
    } else {
      setStatus(resp?.error || "Failed", true);
    }
  });
});

// Capture current page
document.getElementById("btn-capture-page").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url) return;

  setStatus("Capturing page...");
  chrome.runtime.sendMessage({
    action: "capture-page",
    url: tab.url,
    title: tab.title,
  }, (resp) => {
    if (resp?.success) {
      setStatus("Page captured!", false);
    } else {
      setStatus(resp?.error || "Failed", true);
    }
  });
});

// Capture current selection
document.getElementById("btn-capture-selection").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  // Get selection from content script
  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => window.getSelection()?.toString().trim(),
  }, (results) => {
    const selection = results?.[0]?.result;
    if (!selection) {
      setStatus("No text selected on page", true);
      return;
    }

    setStatus("Capturing...");
    chrome.runtime.sendMessage({
      action: "capture-selection",
      text: selection,
      url: tab.url,
      title: tab.title,
    }, (resp) => {
      if (resp?.success) {
        setStatus("Selection captured!", false);
      } else {
        setStatus(resp?.error || "Failed", true);
      }
    });
  });
});

// Open settings page
document.getElementById("settings-link").addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

function setStatus(msg, isError = false) {
  statusMsg.textContent = msg;
  statusMsg.className = isError ? "error" : "";
  statusMsg.style.display = "block";
  if (!isError) {
    setTimeout(() => { statusMsg.style.display = "none"; }, 2500);
  }
}
