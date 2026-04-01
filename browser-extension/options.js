const apiUrlInput = document.getElementById("api-url");
const apiKeyInput = document.getElementById("api-key");
const savedMsg = document.getElementById("saved");

// Load existing settings
chrome.storage.sync.get({ apiUrl: "http://localhost:8000", apiKey: "" }, (settings) => {
  apiUrlInput.value = settings.apiUrl;
  apiKeyInput.value = settings.apiKey;
});

document.getElementById("save").addEventListener("click", () => {
  const apiUrl = apiUrlInput.value.trim().replace(/\/$/, "") || "http://localhost:8000";
  const apiKey = apiKeyInput.value.trim();

  chrome.storage.sync.set({ apiUrl, apiKey }, () => {
    savedMsg.style.display = "inline";
    setTimeout(() => { savedMsg.style.display = "none"; }, 2000);
  });
});
