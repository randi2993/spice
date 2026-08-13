"""
providers.py — Manages the global LLM provider config.

The file used to live in ~/.spice/, which is the directory the installer wipes
on every reinstall, so reinstalling silently destroyed the user's providers.
Config now lives outside the install directory, and is migrated on first use.
"""
import json
import os
import shutil
import sys
from pathlib import Path


def _config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        return Path(base) / "spice" if base else Path.home() / "AppData" / "Roaming" / "spice"
    return Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / "spice"


PROVIDERS_FILE = _config_dir() / "providers.json"
LEGACY_PROVIDERS_FILE = Path.home() / ".spice" / "providers.json"


def _migrate_legacy() -> None:
    """Moves a pre-existing config out of the install directory, once."""
    if PROVIDERS_FILE.exists() or not LEGACY_PROVIDERS_FILE.exists():
        return
    PROVIDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LEGACY_PROVIDERS_FILE, PROVIDERS_FILE)
    print(f"[spice] providers.json migrated to {PROVIDERS_FILE}")
    print(f"        (the old path lives inside the directory the installer deletes)")


def load() -> dict:
    _migrate_legacy()
    if not PROVIDERS_FILE.exists():
        return {"providers": {}, "default": None}
    with open(PROVIDERS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save(data: dict) -> None:
    PROVIDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROVIDERS_FILE, "w", encoding="utf-8", newline="") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def add_provider(name: str, cli: str, model_flag: str, system_flag: str) -> None:
    data = load()
    data["providers"][name] = {
        "cli": cli,
        "model_flag": model_flag,
        "system_flag": system_flag,
    }
    if data.get("default") is None:
        data["default"] = name
    save(data)


def remove_provider(name: str) -> bool:
    data = load()
    if name not in data.get("providers", {}):
        return False
    del data["providers"][name]
    if data.get("default") == name:
        remaining = list(data["providers"].keys())
        data["default"] = remaining[0] if remaining else None
    save(data)
    return True


def get_provider(name: str) -> dict | None:
    data = load()
    return data.get("providers", {}).get(name)


def list_providers() -> list[str]:
    return list(load().get("providers", {}).keys())


def get_default() -> str | None:
    return load().get("default")
