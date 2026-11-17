"""Loads the user's search settings.

Precedence: `config.example.yml` (tracked, documented defaults) < `presets/<preset>.yml` (the
profession: role keywords, skills, title filters) < `config.yml` (git-ignored, any subset of keys).
Set JOB_HUNTER_CONFIG to point at another user file, or JOB_HUNTER_PRESET to switch the preset.
"""
import copy
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLE_FILE = REPO_ROOT / "config.example.yml"
USER_FILE = REPO_ROOT / "config.yml"
PRESETS_DIR = REPO_ROOT / "presets"

_override: Optional[Dict[str, Any]] = None


def _read(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must be a YAML mapping")
    return data


def _merge(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (extra or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def available_presets() -> list:
    return sorted(p.stem for p in PRESETS_DIR.glob("*.yml"))


def compose(user: Optional[Dict[str, Any]] = None, preset: Optional[str] = None) -> Dict[str, Any]:
    """defaults < preset < user. `preset` (e.g. from --preset) beats the one named in the files."""
    defaults = _read(EXAMPLE_FILE)
    user = user or {}
    name = preset or user.get("preset") or defaults.get("preset")
    data = _merge(defaults, {})
    if name:
        path = PRESETS_DIR / f"{name}.yml"
        if not path.exists():
            raise ValueError(f"Unknown preset '{name}'. Available: {', '.join(available_presets())}")
        data = _merge(data, _read(path))
    data = _merge(data, user)
    data["preset"] = name
    return data


@lru_cache(maxsize=8)
def _load(path_str: str, preset: str) -> Dict[str, Any]:
    return compose(_read(Path(path_str)) if path_str else {}, preset or None)


def get() -> Dict[str, Any]:
    """The active settings (defaults + preset + config.yml, or a test override)."""
    if _override is not None:
        return _override
    path = os.getenv("JOB_HUNTER_CONFIG") or (str(USER_FILE) if USER_FILE.exists() else "")
    return _load(path, os.getenv("JOB_HUNTER_PRESET", ""))


def section(name: str) -> Dict[str, Any]:
    return get().get(name) or {}


def use(settings: Optional[Dict[str, Any]]) -> None:
    """Tests: pin the settings (pass None to go back to the files)."""
    global _override
    _override = settings
    _load.cache_clear()


def example(preset: Optional[str] = None) -> Dict[str, Any]:
    """Defaults + preset only, ignoring the user's config.yml (deterministic for tests)."""
    return compose({}, preset)


def words_regex(words: Iterable[str], flags=re.I) -> Optional["re.Pattern[str]"]:
    """\\b-bounded alternation of literal phrases; None when the list is empty."""
    items = sorted({str(w).strip() for w in words or [] if str(w).strip()}, key=len, reverse=True)
    if not items:
        return None
    return re.compile(r"(?<![\w])(" + "|".join(re.escape(w) for w in items) + r")(?![\w])", flags)
