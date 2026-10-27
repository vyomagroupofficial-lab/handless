"""Configuration manager for Vyoma Handless.

Loads and saves non-sensitive application settings (hotkeys, preferences, UI flags)
from and to a local TOML configuration file. Sensitive credentials (e.g. Gemini API key)
are handled separately via Windows Credential Manager.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import pydantic
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".vyoma-handless" / "config.toml"


class HotkeysConfig(BaseModel):
    push_to_talk: str = "<ctrl>+<space>"
    emergency_stop: str = "<ctrl>+<shift>+q"
    toggle_bar: str = "<ctrl>+<alt>+h"


class VoiceConfig(BaseModel):
    mode: str = Field(default="push_to_talk", description="push_to_talk or continuous")
    vad_aggressiveness: int = Field(default=2, ge=0, le=3)
    vosk_model_path: str = Field(default="models/vosk-model-small-en-us-0.15")
    sample_rate: int = 16000
    device_index: int = -1  # -1 = system default


class AIConfig(BaseModel):
    preferred_tier: str = Field(
        default="hybrid", description="local_only, hybrid, or cloud_only"
    )
    gemini_model: str = "gemini-2.5-flash"
    local_llm_endpoint: str = "http://localhost:11434/api/generate"  # Ollama default
    local_llm_model: str = "qwen2.5-coder:3b"
    enable_vision_fallback: bool = True


class UIConfig(BaseModel):
    theme: str = "cream"
    stay_on_top: bool = True
    start_in_tray: bool = False
    window_opacity: float = 0.98


class SafetyConfig(BaseModel):
    confirm_destructive_actions: bool = True
    emergency_stop_enabled: bool = True


class AppConfig(BaseModel):
    hotkeys: HotkeysConfig = Field(default_factory=HotkeysConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)


def get_default_config_file() -> Path:
    config_dir = Path.home() / ".vyoma-handless"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.toml"


def load_config(path: Path | None = None) -> AppConfig:
    config_file = path or get_default_config_file()
    if not config_file.exists():
        cfg = AppConfig()
        save_config(cfg, config_file)
        return cfg

    try:
        with open(config_file, "rb") as f:
            data = tomllib.load(f)
        return AppConfig.model_validate(data)
    except Exception as exc:
        logger.warning("Error reading config from %s: %s. Using defaults.", config_file, exc)
        return AppConfig()


def save_config(config: AppConfig, path: Path | None = None) -> bool:
    config_file = path or get_default_config_file()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = config.model_dump()
        lines = []
        for section, values in data.items():
            lines.append(f"[{section}]")
            for k, v in values.items():
                if isinstance(v, bool):
                    val_str = "true" if v else "false"
                elif isinstance(v, (int, float)):
                    val_str = str(v)
                else:
                    val_str = f'"{v}"'
                lines.append(f"{k} = {val_str}")
            lines.append("")
        with open(config_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return True
    except Exception as exc:
        logger.error("Failed to write config to %s: %s", config_file, exc)
        return False
