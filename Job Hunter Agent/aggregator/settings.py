"""Loads the user's search settings.

`config.example.yml` (tracked) holds every key with documented defaults; `config.yml` (git-ignored)
overrides any subset of them. Set JOB_HUNTER_CONFIG to point at another file.
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


@lru_cache(maxsize=4)
def _load(path_str: str) -> Dict[str, Any]:
    defaults = _read(EXAMPLE_FILE)
    return _merge(defaults, _read(Path(path_str))) if path_str else defaults


def get() -> Dict[str, Any]:
    """The active settings (defaults merged with config.yml, or a test override)."""
    if _override is not None:
        return _override
    path = os.getenv("JOB_HUNTER_CONFIG") or (str(USER_FILE) if USER_FILE.exists() else "")
    return _load(path)


def section(name: str) -> Dict[str, Any]:
    return get().get(name) or {}


def use(settings: Optional[Dict[str, Any]]) -> None:
    """Tests: pin the settings (pass None to go back to the files)."""
    global _override
    _override = settings
    _load.cache_clear()


def example() -> Dict[str, Any]:
    """The documented defaults only, ignoring the user's config.yml (deterministic for tests)."""
    return _read(EXAMPLE_FILE)


def words_regex(words: Iterable[str], flags=re.I) -> Optional["re.Pattern[str]"]:
    """\\b-bounded alternation of literal phrases; None when the list is empty."""
    items = sorted({str(w).strip() for w in words or [] if str(w).strip()}, key=len, reverse=True)
    if not items:
        return None
    return re.compile(r"(?<![\w])(" + "|".join(re.escape(w) for w in items) + r")(?![\w])", flags)
