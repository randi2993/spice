"""
providers.py — Manages ~/.spice/providers.json (global LLM provider config).
"""
import json
import os
from pathlib import Path

PROVIDERS_FILE = Path.home() / ".spice" / "providers.json"


def load() -> dict:
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
