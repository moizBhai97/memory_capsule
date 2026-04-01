/**
 * Open Memory Capsule — JavaScript/Node.js SDK
 *
 * Usage (Node.js):
 *   const { MemoryCapsule } = require('open-memory-capsule')
 *   const mc = new MemoryCapsule({ baseUrl: 'http://localhost:8000' })
 *   await mc.add({ text: 'Meeting notes...' })
 *   const results = await mc.search('quote from Ahmed')
 *
 * Usage (Browser / ES modules):
 *   import { MemoryCapsule } from 'open-memory-capsule'
 */

class MemoryCapsule {
  /**
   * @param {Object} options
   * @param {string} options.baseUrl - URL of your Memory Capsule instance
   * @param {string} [options.apiKey] - Optional API key
   * @param {number} [options.timeout] - Request timeout in ms (default: 60000)
   */
  constructor({ baseUrl = "http://localhost:8000", apiKey = "", timeout = 60000 } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.apiKey = apiKey;
    this.timeout = timeout;
  }

  /**
   * Capture content into memory.
   *
   * @param {Object} options
   * @param {string} [options.text] - Text to capture
   * @param {string} [options.url] - URL to fetch and capture
   * @param {string} [options.file] - File path (Node.js only) or File object (browser)
   * @param {string} [options.sourceApp] - Source platform e.g. "whatsapp", "meeting"
   * @param {string} [options.sender] - Who sent this
   * @param {string} [options.chat] - Chat/channel name
   * @param {Object} [options.metadata] - Extra platform-specific data
   * @returns {Promise<Object>}
   */
  async add({ text, url, file, sourceApp = "sdk", sender, chat, metadata } = {}) {
    if (file) {
      return this._uploadFile(file, sourceApp, sender, chat, metadata);
    } else if (text || url) {
      return this._postText(text, url, sourceApp, sender, chat, metadata);
    } else {
      throw new Error("Provide file, text, or url");
    }
  }

  /**
   * Search your memory with natural language.
   *
   * @param {string} query - Natural language query e.g. "quote from Ahmed last week"
   * @param {Object} [options]
   * @param {number} [options.limit] - Max results (default: 10)
   * @param {string} [options.source] - Filter by source app
   * @param {string} [options.sourceType] - Filter by content type (audio, image, pdf, text)
   * @param {string} [options.fromDate] - ISO date string
   * @param {string} [options.toDate] - ISO date string
   * @returns {Promise<Array>}
   */
  async search(query, { limit = 10, source, sourceType, fromDate, toDate } = {}) {
    const params = new URLSearchParams({ q: query, limit: String(limit) });
    if (source) params.set("source_app", source);
    if (sourceType) params.set("source_type", sourceType);
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);

    const data = await this._get(`/api/search?${params}`);
    return (data.results || []).map((r) => ({
      id: r.capsule.id,
      summary: r.capsule.summary,
      tags: r.capsule.tags,
      actionItems: r.capsule.action_items,
      sourceApp: r.capsule.source_app,
      sender: r.capsule.source_sender,
      chat: r.capsule.source_chat,
      timestamp: r.capsule.timestamp,
      snippet: r.snippet,
      score: r.score,
      rawContent: r.capsule.raw_content,
    }));
  }

  /**
   * List recent capsules.
   *
   * @param {Object} [options]
   * @param {number} [options.limit]
   * @param {string} [options.source]
   * @returns {Promise<Array>}
   */
  async list({ limit = 20, source } = {}) {
    const params = new URLSearchParams({ limit: String(limit) });
    if (source) params.set("source_app", source);
    const data = await this._get(`/api/capsules?${params}`);
    return data.capsules || [];
  }

  /**
   * Get a single capsule by ID.
   * @param {string} id
   * @returns {Promise<Object|null>}
   */
  async get(id) {
    try {
      return await this._get(`/api/capsules/${id}`);
    } catch (err) {
      if (err.status === 404) return null;
      throw err;
    }
  }

  /**
   * Check API and provider health.
   * @returns {Promise<Object>}
   */
  async health() {
    return this._get("/health/providers");
  }

  async _postText(text, url, sourceApp, sender, chat, metadata) {
    const body = { source_app: sourceApp };
    if (text) body.text = text;
    if (url) body.url = url;
    if (sender) body.source_sender = sender;
    if (chat) body.source_chat = chat;
    if (metadata) body.metadata = metadata;

    return this._post("/api/capsules", body);
  }

  async _uploadFile(file, sourceApp, sender, chat, metadata) {
    // Node.js: file is a path string
    if (typeof file === "string") {
      const fs = require("fs");
      const path = require("path");
      const FormData = require("form-data");

      const form = new FormData();
      form.append("file", fs.createReadStream(file), { filename: path.basename(file) });
      form.append("source_app", sourceApp);
      if (sender) form.append("source_sender", sender);
      if (chat) form.append("source_chat", chat);
      if (metadata) form.append("metadata", JSON.stringify(metadata));

      const resp = await fetch(`${this.baseUrl}/api/capsules/upload`, {
        method: "POST",
        headers: { ...this._authHeaders(), ...form.getHeaders() },
        body: form,
        signal: AbortSignal.timeout(this.timeout),
      });
      if (!resp.ok) throw Object.assign(new Error(await resp.text()), { status: resp.status });
      return resp.json();
    }

    // Browser: file is a File object
    const form = new FormData();
    form.append("file", file);
    form.append("source_app", sourceApp);
    if (sender) form.append("source_sender", sender);
    if (chat) form.append("source_chat", chat);

    const resp = await fetch(`${this.baseUrl}/api/capsules/upload`, {
      method: "POST",
      headers: this._authHeaders(),
      body: form,
      signal: AbortSignal.timeout(this.timeout),
    });
    if (!resp.ok) throw Object.assign(new Error(await resp.text()), { status: resp.status });
    return resp.json();
  }

  async _get(path) {
    const resp = await fetch(`${this.baseUrl}${path}`, {
      headers: this._authHeaders(),
      signal: AbortSignal.timeout(this.timeout),
    });
    if (!resp.ok) throw Object.assign(new Error(await resp.text()), { status: resp.status });
    return resp.json();
  }

  async _post(path, body) {
    const resp = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...this._authHeaders() },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(this.timeout),
    });
    if (!resp.ok) throw Object.assign(new Error(await resp.text()), { status: resp.status });
    return resp.json();
  }

  _authHeaders() {
    return this.apiKey ? { "X-Api-Key": this.apiKey } : {};
  }
}

// Export for both CommonJS and ES modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = { MemoryCapsule };
} else {
  // Browser / ES module
  export { MemoryCapsule };
}
