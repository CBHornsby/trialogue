"""
Settings storage. JSON file in ~/.debate-tool/config.json.
Versioned so we can migrate later.
"""
import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".debate-tool"
CONFIG_FILE = CONFIG_DIR / "config.json"
CONFIG_VERSION = 1

@dataclass
class Settings:
    version: int = CONFIG_VERSION
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    proposer_provider: str = "claude"
    proposer_model: str = "claude-opus-4-7"
    critic_provider: str = "openai"
    critic_model: str = "gpt-5.5"
    judge_provider: str = "gemini"
    judge_model: str = "gemini-3.1-pro-preview"

    def api_key_for(self, provider: str) -> str:
        return {
            "claude": self.anthropic_api_key,
            "openai": self.openai_api_key,
            "gemini": self.google_api_key,
        }.get(provider, "")

def load_settings() -> Settings:
    if not CONFIG_FILE.exists():
        return Settings()
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        # Future: migrate based on version field
        # Drop unknown fields gracefully
        valid_fields = Settings.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return Settings(**filtered)
    except (json.JSONDecodeError, TypeError):
        return Settings()

def save_settings(settings: Settings) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Restrict file permissions on Unix (best effort)
    with open(CONFIG_FILE, "w") as f:
        json.dump(asdict(settings), f, indent=2)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass  # Windows or permission issue - settings still saved
