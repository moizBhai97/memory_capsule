"""
Configuration loader. Reads config.yaml + environment variables.
Environment variables always override config file (12-factor app style).
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class WhisperConfig:
    model: str = "small"       # tiny | base | small | medium — small is best balance for 4GB
    device: str = "cuda"       # cuda | cpu
    language: Optional[str] = None  # None = auto-detect


@dataclass
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    embed_model: str = "nomic-embed-text"
    llm_model: str = "phi3.5:mini"   # best small model for instruction following


@dataclass
class OpenAIConfig:
    api_key: str = ""
    embed_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"


@dataclass
class AnthropicConfig:
    api_key: str = ""
    llm_model: str = "claude-haiku-4-5-20251001"


@dataclass
class GroqConfig:
    api_key: str = ""
    llm_model: str = "llama-3.1-8b-instant"   # fast + free tier


@dataclass
class StorageConfig:
    type: str = "local"
    sqlite_path: str = "./data/capsules.db"
    chroma_path: str = "./data/chroma"
    uploads_path: str = "./data/uploads"


@dataclass
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    api_key: str = ""       # empty = no auth (local use)
    cors_origins: list = field(default_factory=lambda: ["*"])


@dataclass
class IntegrationConfig:
    # WhatsApp Personal (whatsapp-web.js)
    whatsapp_enabled: bool = False
    whatsapp_session_path: str = "./data/whatsapp_session"

    # WhatsApp Business API
    whatsapp_business_enabled: bool = False
    whatsapp_business_token: str = ""
    whatsapp_business_phone_id: str = ""
    whatsapp_business_verify_token: str = ""

    # Telegram
    telegram_enabled: bool = False
    telegram_api_id: str = ""
    telegram_api_hash: str = ""
    telegram_phone: str = ""
    telegram_session_path: str = "./data/telegram_session"

    # Email (IMAP)
    email_enabled: bool = False
    email_host: str = ""
    email_port: int = 993
    email_username: str = ""
    email_password: str = ""   # use app password, never main password
    email_use_ssl: bool = True
    email_folder: str = "INBOX"

    # Zoom
    zoom_enabled: bool = False
    zoom_recordings_path: str = ""   # local Zoom recordings folder

    # Slack
    slack_enabled: bool = False
    slack_bot_token: str = ""
    slack_channel_ids: list = field(default_factory=list)

    # Discord
    discord_enabled: bool = False
    discord_bot_token: str = ""
    discord_channel_ids: list = field(default_factory=list)

    # Watch folders (local filesystem)
    watch_folders: list = field(default_factory=list)
    watch_screenshots: bool = True    # auto-detect OS screenshot folder
    watch_downloads: bool = True      # auto-watch Downloads folder

    # Webhook receiver
    webhook_secret: str = ""          # for verifying Zapier/n8n/Make webhooks


@dataclass
class Config:
    provider: str = "ollama"          # ollama | openai | anthropic | groq
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    groq: GroqConfig = field(default_factory=GroqConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    api: APIConfig = field(default_factory=APIConfig)
    integrations: IntegrationConfig = field(default_factory=IntegrationConfig)
    debug: bool = False


def load_config(config_path: str = "config.yaml") -> Config:
    """
    Load config from YAML file, then override with environment variables.
    Priority: env vars > config.local.yaml > config.yaml > defaults
    """
    raw = {}

    # Load base config
    if Path(config_path).exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

    # Load local overrides (gitignored)
    local_path = config_path.replace(".yaml", ".local.yaml")
    if Path(local_path).exists():
        with open(local_path) as f:
            local = yaml.safe_load(f) or {}
            raw = _deep_merge(raw, local)

    config = Config()

    # Provider
    config.provider = os.getenv("MC_PROVIDER", raw.get("provider", config.provider))

    # Whisper
    w = raw.get("whisper", {})
    config.whisper.model = os.getenv("MC_WHISPER_MODEL", w.get("model", config.whisper.model))
    config.whisper.device = os.getenv("MC_WHISPER_DEVICE", w.get("device", config.whisper.device))
    config.whisper.language = os.getenv("MC_WHISPER_LANGUAGE", w.get("language", config.whisper.language))

    # Ollama
    o = raw.get("ollama", {})
    config.ollama.base_url = os.getenv("MC_OLLAMA_URL", o.get("base_url", config.ollama.base_url))
    config.ollama.llm_model = os.getenv("MC_OLLAMA_LLM", o.get("llm_model", config.ollama.llm_model))
    config.ollama.embed_model = os.getenv("MC_OLLAMA_EMBED", o.get("embed_model", config.ollama.embed_model))

    # OpenAI
    oa = raw.get("openai", {})
    config.openai.api_key = os.getenv("OPENAI_API_KEY", oa.get("api_key", ""))
    config.openai.llm_model = os.getenv("MC_OPENAI_LLM", oa.get("llm_model", config.openai.llm_model))

    # Anthropic
    an = raw.get("anthropic", {})
    config.anthropic.api_key = os.getenv("ANTHROPIC_API_KEY", an.get("api_key", ""))
    config.anthropic.llm_model = os.getenv("MC_ANTHROPIC_LLM", an.get("llm_model", config.anthropic.llm_model))

    # Groq
    gr = raw.get("groq", {})
    config.groq.api_key = os.getenv("GROQ_API_KEY", gr.get("api_key", ""))
    config.groq.llm_model = os.getenv("MC_GROQ_LLM", gr.get("llm_model", config.groq.llm_model))

    # Storage
    s = raw.get("storage", {})
    config.storage.type = os.getenv("MC_STORAGE_TYPE", s.get("type", config.storage.type))
    config.storage.sqlite_path = os.getenv("MC_SQLITE_PATH", s.get("sqlite_path", config.storage.sqlite_path))
    config.storage.chroma_path = os.getenv("MC_CHROMA_PATH", s.get("chroma_path", config.storage.chroma_path))
    config.storage.uploads_path = os.getenv("MC_UPLOADS_PATH", s.get("uploads_path", config.storage.uploads_path))

    # API
    a = raw.get("api", {})
    config.api.host = os.getenv("MC_API_HOST", a.get("host", config.api.host))
    config.api.port = int(os.getenv("MC_API_PORT", a.get("port", config.api.port)))
    config.api.api_key = os.getenv("MC_API_KEY", a.get("api_key", ""))

    # Integrations — load from raw config, env vars override sensitive fields
    i = raw.get("integrations", {})
    ig = config.integrations

    ig.whatsapp_enabled = _bool_env("MC_WHATSAPP_ENABLED", i.get("whatsapp_enabled", False))
    ig.whatsapp_business_enabled = _bool_env("MC_WA_BUSINESS_ENABLED", i.get("whatsapp_business_enabled", False))
    ig.whatsapp_business_token = os.getenv("MC_WA_BUSINESS_TOKEN", i.get("whatsapp_business_token", ""))
    ig.whatsapp_business_phone_id = os.getenv("MC_WA_PHONE_ID", i.get("whatsapp_business_phone_id", ""))
    ig.whatsapp_business_verify_token = os.getenv("MC_WA_VERIFY_TOKEN", i.get("whatsapp_business_verify_token", ""))

    ig.telegram_enabled = _bool_env("MC_TELEGRAM_ENABLED", i.get("telegram_enabled", False))
    ig.telegram_api_id = os.getenv("MC_TELEGRAM_API_ID", i.get("telegram_api_id", ""))
    ig.telegram_api_hash = os.getenv("MC_TELEGRAM_API_HASH", i.get("telegram_api_hash", ""))
    ig.telegram_phone = os.getenv("MC_TELEGRAM_PHONE", i.get("telegram_phone", ""))

    ig.email_enabled = _bool_env("MC_EMAIL_ENABLED", i.get("email_enabled", False))
    ig.email_host = os.getenv("MC_EMAIL_HOST", i.get("email_host", ""))
    ig.email_username = os.getenv("MC_EMAIL_USERNAME", i.get("email_username", ""))
    ig.email_password = os.getenv("MC_EMAIL_PASSWORD", i.get("email_password", ""))

    ig.zoom_enabled = _bool_env("MC_ZOOM_ENABLED", i.get("zoom_enabled", False))
    ig.zoom_recordings_path = os.getenv("MC_ZOOM_PATH", i.get("zoom_recordings_path", ""))

    ig.slack_enabled = _bool_env("MC_SLACK_ENABLED", i.get("slack_enabled", False))
    ig.slack_bot_token = os.getenv("MC_SLACK_BOT_TOKEN", i.get("slack_bot_token", ""))

    ig.discord_enabled = _bool_env("MC_DISCORD_ENABLED", i.get("discord_enabled", False))
    ig.discord_bot_token = os.getenv("MC_DISCORD_BOT_TOKEN", i.get("discord_bot_token", ""))

    ig.watch_folders = i.get("watch_folders", [])
    ig.watch_screenshots = _bool_env("MC_WATCH_SCREENSHOTS", i.get("watch_screenshots", True))
    ig.watch_downloads = _bool_env("MC_WATCH_DOWNLOADS", i.get("watch_downloads", True))
    ig.webhook_secret = os.getenv("MC_WEBHOOK_SECRET", i.get("webhook_secret", ""))

    config.debug = _bool_env("MC_DEBUG", raw.get("debug", False))

    return config


def _bool_env(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes")


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# Global config instance — import this everywhere
_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config
