"""manifest.py — Read/write .agent/installed.json"""
import json
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_FILE = "installed.json"
TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
_UNKNOWN_VERSION = "0.0.0"


def toolkit_version() -> str:
    """Reads the real toolkit version from manifest.json.

    Previously a hardcoded constant, which meant installed.json recorded a
    version that stopped matching the toolkit as soon as it advanced.
    """
    try:
        with open(TOOLKIT_ROOT / "manifest.json", encoding="utf-8") as f:
            return json.load(f).get("version", _UNKNOWN_VERSION)
    except (OSError, json.JSONDecodeError):
        return _UNKNOWN_VERSION


def _manifest_path(agent_dir: Path) -> Path:
    return agent_dir / MANIFEST_FILE


def load(agent_dir: Path) -> dict:
    path = _manifest_path(agent_dir)
    if not path.exists():
        return _empty()
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(agent_dir: Path, manifest: dict) -> None:
    path = _manifest_path(agent_dir)
    with open(path, "w", encoding="utf-8", newline="") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _empty() -> dict:
    return {
        "toolkit_version": toolkit_version(),
        "installed_at": _now(),
        "components": {}
    }


def record(manifest: dict, component_type: str, name: str, version: str,
           deps: list[str], tier: str | None = None) -> None:
    key = f"{component_type}/{name}"
    entry = {
        "type": component_type,
        "name": name,
        "version": version,
        "installed_at": _now(),
        "depends_on": deps,
    }
    if tier is not None:
        entry["tier"] = tier
    manifest.setdefault("components", {})[key] = entry


def remove_record(manifest: dict, component_type: str, name: str) -> None:
    key = f"{component_type}/{name}"
    manifest.get("components", {}).pop(key, None)


def is_installed(manifest: dict, component_type: str, name: str) -> bool:
    return f"{component_type}/{name}" in manifest.get("components", {})


def get_version(manifest: dict, component_type: str, name: str) -> str | None:
    entry = manifest.get("components", {}).get(f"{component_type}/{name}")
    return entry["version"] if entry else None


def dependents_of(manifest: dict, component_type: str, name: str) -> list[str]:
    target = f"{component_type}/{name}"
    return [k for k, e in manifest.get("components", {}).items()
            if target in e.get("depends_on", [])]


def installed_roles(manifest: dict) -> list[dict]:
    """Returns list of installed role entries."""
    return [e for e in manifest.get("components", {}).values()
            if e["type"] == "roles"]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
