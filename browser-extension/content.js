/**
 * Content script — runs on every page.
 * Adds keyboard shortcut (Alt+Shift+C) to capture selected text.
 */

document.addEventListener("keydown", (e) => {
  // Alt+Shift+C — capture selected text
  if (e.altKey && e.shiftKey && e.key === "C") {
    const selection = window.getSelection()?.toString().trim();
    if (!selection) return;

    chrome.runtime.sendMessage({
      action: "capture-selection",
      text: selection,
      url: window.location.href,
      title: document.title,
    }, (response) => {
      if (response?.success) {
        showToast("Captured to Memory Capsule");
      } else {
        showToast("Capture failed — is the daemon running?", true);
      }
    });
  }
});

function showToast(message, isError = false) {
  const existing = document.getElementById("mc-toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.id = "mc-toast";
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: ${isError ? "#e53e3e" : "#2d3748"};
    color: white;
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 14px;
    font-family: system-ui, sans-serif;
    z-index: 999999;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    animation: mc-fadein 0.2s ease;
  `;

  const style = document.createElement("style");
  style.textContent = `@keyframes mc-fadein { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }`;
  document.head.appendChild(style);
  document.body.appendChild(toast);

  setTimeout(() => toast.remove(), 3000);
}
