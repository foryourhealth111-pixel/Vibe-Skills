from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from ._io import load_json, utc_now, write_text
from ._repo import resolve_repo_root


def setting_value(settings: dict[str, Any] | None, name: str) -> str | None:
    if not isinstance(settings, dict):
        return None
    env = settings.get("env")
    if not isinstance(env, dict):
        return None
    value = env.get(name)
    if value is None:
        return None
    return str(value)


def placeholder_value(value: str | None) -> bool:
    if not value:
        return False
    trimmed = value.strip()
    return trimmed.startswith("<") and trimmed.endswith(">")


def setting_state(settings: dict[str, Any] | None, name: str) -> str:
    value = setting_value(settings, name)
    if value is None or not value.strip():
        return "missing"
    if placeholder_value(value):
        return "placeholder"
    return "configured"


def os_environ(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return None
    return str(value)


def resolved_setting_state(settings: dict[str, Any] | None, name: str) -> tuple[str, str]:
    env_value = os_environ(name)
    if env_value:
        if placeholder_value(env_value):
            return "placeholder", "env"
        return "configured", "env"

    setting_value_text = setting_value(settings, name)
    if setting_value_text is None or not setting_value_text.strip():
        return "missing", "missing"
    if placeholder_value(setting_value_text):
        return "placeholder", "settings"
    return "configured", "settings"


def command_present(name: str) -> bool:
    return shutil.which(name) is not None
