"""
Configuration loader.
Reads config.yaml + config.local.yaml, with environment variables reserved for sensitive values.

Provider format follows convention: "provider/model"
Examples:
  llm.model: "ollama/phi3.5:latest"
  llm.model: "openai/gpt-4o-mini"
  llm.model: "anthropic/claude-haiku-4-5-20251001"
  llm.model: "groq/llama-3.1-8b-instant"
  llm.model: "gemini/gemini-2.0-flash"
  llm.model: "openai-compatible/my-model"  # any OpenAI-compatible endpoint
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Unified provider config using "provider/model" format"""
    model: str = "ollama/phi3.5:latest"
    api_key: str = ""
    base_url: str = ""      # override endpoint (self-hosted / openai-compatible)
    device: str = "auto"    # local providers: auto | cpu | gpu
    extra: dict = field(default_factory=dict)

    @property
    def provider_id(self) -> str:
        return self.model.split("/", 1)[0].strip().lower()

    @property
    def model_id(self) -> str:
        parts = self.model.split("/", 1)
        return parts[1].strip() if len(parts) > 1 else self.model


API_KEY_ENV: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


@dataclass
class StorageConfig:
    sqlite_path: str = "./data/capsules.db"
    chroma_path: str = "./data/chroma"
    uploads_path: str = "./data/uploads"


@dataclass
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    api_key: str = ""
    cors_origins: list = field(default_factory=lambda: ["*"])


@dataclass
class IntegrationConfig:
    whatsapp_enabled: bool = False

    whatsapp_business_enabled: bool = False
    whatsapp_business_token: str = ""
    whatsapp_business_phone_id: str = ""
    whatsapp_business_verify_token: str = ""

    telegram_enabled: bool = False
    telegram_api_id: str = ""
    telegram_api_hash: str = ""
    telegram_phone: str = ""
    telegram_session_path: str = "./data/telegram_session"

    email_enabled: bool = False
    email_host: str = ""
    email_port: int = 993
    email_username: str = ""
    email_password: str = ""
    email_use_ssl: bool = True
    email_folder: str = "INBOX"

    zoom_enabled: bool = False
    zoom_recordings_path: str = ""

    slack_enabled: bool = False
    slack_bot_token: str = ""
    slack_app_token: str = ""   # Socket Mode app-level token (xapp-...)
    slack_channel_ids: list = field(default_factory=list)

    discord_enabled: bool = False
    discord_bot_token: str = ""
    discord_channel_ids: list = field(default_factory=list)

    watch_folders: list = field(default_factory=list)
    watch_screenshots: bool = True
    watch_downloads: bool = True

    webhook_secret: str = ""


@dataclass
class Config:
    llm: ProviderConfig = field(default_factory=lambda: ProviderConfig(model="ollama/phi3.5:latest"))
    embed: ProviderConfig = field(default_factory=lambda: ProviderConfig(model="ollama/nomic-embed-text:latest"))
    transcribe: ProviderConfig = field(default_factory=lambda: ProviderConfig(model="whisper/small"))
    ocr: ProviderConfig = field(default_factory=lambda: ProviderConfig(model="easyocr/en"))
    storage: StorageConfig = field(default_factory=StorageConfig)
    api: APIConfig = field(default_factory=APIConfig)
    integrations: IntegrationConfig = field(default_factory=IntegrationConfig)
    debug: bool = False


def load_config(config_path: str = "config.yaml") -> Config:
    """
    Load config from YAML files and apply environment variables for secrets only.
    Precedence (highest to lowest):
    1) Environment variables (secrets only)
    2) config.local.yaml
    3) config.yaml
    4) dataclass defaults
    """
    raw = {}

    if Path(config_path).exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

    local_path = config_path.replace(".yaml", ".local.yaml")
    if Path(local_path).exists():
        with open(local_path) as f:
            local = yaml.safe_load(f) or {}
            raw = _deep_merge(raw, local)

    config = Config()

    # --- LLM ---
    llm_raw = raw.get("llm") or {}
    if isinstance(llm_raw, str):
        # shorthand: llm: "ollama/phi3.5:latest"
        config.llm.model = llm_raw
    else:
        config.llm.model = llm_raw.get("model", config.llm.model)
        config.llm.base_url = llm_raw.get("base_url", "")
        config.llm.device = llm_raw.get("device", "auto")
        config.llm.extra = {k: v for k, v in llm_raw.items()
                            if k not in ("model", "api_key", "base_url", "device")}

    config.llm.api_key = _resolve_api_key(config.llm.provider_id, llm_raw)

    # --- Embed ---
    embed_raw = raw.get("embed") or {}
    if isinstance(embed_raw, str):
        config.embed.model = embed_raw
    elif embed_raw:
        config.embed.model = embed_raw.get("model", config.embed.model)
        config.embed.base_url = embed_raw.get("base_url", "")
        config.embed.device = embed_raw.get("device", "auto")
        config.embed.extra = {k: v for k, v in embed_raw.items()
                              if k not in ("model", "api_key", "base_url", "device")}
        config.embed.api_key = _resolve_api_key(config.embed.provider_id, embed_raw)
    else:
        # Default embed follows LLM provider where possible, else Ollama
        _set_default_embed(config)

    # --- Transcribe ---
    tr_raw = raw.get("transcribe") or {}
    if isinstance(tr_raw, str):
        config.transcribe.model = tr_raw
    else:
        config.transcribe.model = tr_raw.get("model", config.transcribe.model)
        config.transcribe.base_url = tr_raw.get("base_url", "")
        config.transcribe.device = tr_raw.get("device", "auto")
        config.transcribe.extra = {k: v for k, v in tr_raw.items()
                                   if k not in ("model", "api_key", "base_url", "device")}
        config.transcribe.api_key = _resolve_api_key(config.transcribe.provider_id, tr_raw)

    # --- OCR ---
    ocr_raw = raw.get("ocr") or {}
    if isinstance(ocr_raw, str):
        config.ocr.model = ocr_raw
    elif ocr_raw:
        config.ocr.model = ocr_raw.get("model", config.ocr.model)
        config.ocr.base_url = ocr_raw.get("base_url", "")
        config.ocr.extra = {k: v for k, v in ocr_raw.items()
                            if k not in ("model", "api_key", "base_url", "device")}
        config.ocr.api_key = _resolve_api_key(config.ocr.provider_id, ocr_raw)

    # --- Storage ---
    s = raw.get("storage") or {}
    config.storage.sqlite_path = s.get("sqlite_path", config.storage.sqlite_path)
    config.storage.chroma_path = s.get("chroma_path", config.storage.chroma_path)
    config.storage.uploads_path = s.get("uploads_path", config.storage.uploads_path)

    # --- API ---
    a = raw.get("api") or {}
    config.api.host = a.get("host", config.api.host)
    config.api.port = int(a.get("port", config.api.port))
    config.api.api_key = os.getenv("MC_API_KEY", a.get("api_key", ""))

    # --- Integrations ---
    i = raw.get("integrations") or {}
    ig = config.integrations

    ig.whatsapp_enabled = i.get("whatsapp_enabled", False)
    ig.whatsapp_business_enabled = i.get("whatsapp_business_enabled", False)
    ig.whatsapp_business_token = os.getenv("MC_WA_BUSINESS_TOKEN", i.get("whatsapp_business_token", ""))
    ig.whatsapp_business_phone_id = os.getenv("MC_WA_BUSINESS_PHONE_ID", i.get("whatsapp_business_phone_id", ""))
    ig.whatsapp_business_verify_token = os.getenv("MC_WA_BUSINESS_VERIFY_TOKEN", i.get("whatsapp_business_verify_token", ""))

    ig.telegram_enabled = i.get("telegram_enabled", False)
    ig.telegram_api_id = os.getenv("MC_TELEGRAM_API_ID", i.get("telegram_api_id", ""))
    ig.telegram_api_hash = os.getenv("MC_TELEGRAM_API_HASH", i.get("telegram_api_hash", ""))
    ig.telegram_phone = os.getenv("MC_TELEGRAM_PHONE", i.get("telegram_phone", ""))

    ig.email_enabled = i.get("email_enabled", False)
    ig.email_host = os.getenv("MC_EMAIL_HOST", i.get("email_host", ""))
    ig.email_port = int(os.getenv("MC_EMAIL_PORT", i.get("email_port", 993)))
    ig.email_username = os.getenv("MC_EMAIL_USERNAME", i.get("email_username", ""))
    ig.email_password = os.getenv("MC_EMAIL_PASSWORD", i.get("email_password", ""))

    ig.zoom_enabled = i.get("zoom_enabled", False)
    ig.zoom_recordings_path = i.get("zoom_recordings_path", "")

    ig.slack_enabled = i.get("slack_enabled", False)
    ig.slack_bot_token = os.getenv("MC_SLACK_BOT_TOKEN", i.get("slack_bot_token", ""))
    ig.slack_app_token = os.getenv("MC_SLACK_APP_TOKEN", i.get("slack_app_token", ""))

    ig.discord_enabled = i.get("discord_enabled", False)
    ig.discord_bot_token = os.getenv("MC_DISCORD_BOT_TOKEN", i.get("discord_bot_token", ""))

    ig.watch_folders = i.get("watch_folders", [])
    _ws = os.getenv("MC_WATCH_SCREENSHOTS")
    ig.watch_screenshots = (_ws.lower() not in ("false", "0", "no")) if _ws else i.get("watch_screenshots", True)
    _wd = os.getenv("MC_WATCH_DOWNLOADS")
    ig.watch_downloads = (_wd.lower() not in ("false", "0", "no")) if _wd else i.get("watch_downloads", True)
    ig.webhook_secret = os.getenv("MC_WEBHOOK_SECRET", i.get("webhook_secret", ""))

    config.debug = raw.get("debug") or False

    return config


def _resolve_api_key(provider_id: str, raw: dict) -> str:
    """Reads api_key from env var (if known provider) or config block."""
    env_var = API_KEY_ENV.get(provider_id)
    if env_var:
        return os.getenv(env_var, raw.get("api_key", ""))
    return raw.get("api_key", "")


def _set_default_embed(config: Config) -> None:
    """When no embed config given, pick a sensible default based on LLM provider."""
    provider = config.llm.provider_id
    if provider == "openai":
        config.embed.model = "openai/text-embedding-3-small"
        config.embed.api_key = config.llm.api_key
    elif provider == "gemini":
        config.embed.model = "gemini/text-embedding-004"
        config.embed.api_key = config.llm.api_key
    else:
        # anthropic, groq, ollama, or anything else → use Ollama for embeddings
        config.embed.model = "ollama/nomic-embed-text:latest"
        config.embed.base_url = (
            "http://localhost:11434/v1"
            if not config.llm.base_url or config.llm.provider_id != "ollama"
            else config.llm.base_url
        )
        config.embed.api_key = "ollama"


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config
