"""
profile.py — The security profile and its rendering into tool adapters.

`.agent/profile.json` is the source of truth and is tool-agnostic: it declares
what is allowed in abstract terms (shell, network, subagents, path perimeter).
Adapters are renderers. Deleting every adapter loses no project knowledge, only
the enforcement for those tools.

Enforcement cannot be shared across tools: each CLI implements it in its own
engine, and none of them reads another's configuration. That asymmetry is the
whole reason adapters exist as a separate layer.
"""
import json
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
PROFILE_FILE = "profile.json"


# ── profile definitions ──────────────────────────────────────────────────────

def available() -> dict:
    path = TOOLKIT_ROOT / "profiles.json"
    if not path.exists():
        return {"default": "standard", "profiles": {}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build(name: str, tools: list[str] | None = None) -> dict:
    catalog = available()
    if name not in catalog.get("profiles", {}):
        raise ValueError(f"Unknown profile '{name}'. "
                         f"Available: {', '.join(sorted(catalog.get('profiles', {})))}")
    spec = catalog["profiles"][name]
    return {
        "profile": name,
        "tools": list(tools if tools is not None else default_tools()),
        "perimeter": dict(spec.get("perimeter", {})),
        "capabilities": dict(spec.get("capabilities", {})),
        "exceptions": [],
    }


# ── tool catalog ─────────────────────────────────────────────────────────────

def tools_catalog() -> dict:
    """Known LLM tools: entry point file and the adapter that enforces it."""
    path = TOOLKIT_ROOT / "tools.json"
    if not path.exists():
        return {"default": [], "tools": {}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def known_tools() -> dict:
    return tools_catalog().get("tools", {})


def default_tools() -> list[str]:
    return list(tools_catalog().get("default", []))


def selected_tools(agent_dir: Path) -> list[str]:
    """Tools this project targets. Falls back to the catalog default."""
    profile = load(agent_dir)
    if profile and "tools" in profile:
        return list(profile["tools"])
    return default_tools()


# ── project profile ──────────────────────────────────────────────────────────

def load(agent_dir: Path) -> dict | None:
    path = agent_dir / PROFILE_FILE
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(agent_dir: Path, profile: dict) -> None:
    with open(agent_dir / PROFILE_FILE, "w", encoding="utf-8", newline="") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_or_default(agent_dir: Path) -> dict:
    return load(agent_dir) or build(available().get("default", "standard"))


# ── rendering ────────────────────────────────────────────────────────────────

def render(profile: dict, mapping: dict) -> dict:
    """Applies the profile to an adapter mapping, producing the tool's config."""
    result = _deep_copy(mapping.get("base", {}))
    for condition, fragment in mapping.get("when", {}).items():
        if _matches(profile, condition):
            result = _merge(result, fragment)
    return result


def _matches(profile: dict, condition: str) -> bool:
    """Condition form: `dotted.path=value`, e.g. `capabilities.shell=false`."""
    dotted, _, expected = condition.partition("=")
    node = profile
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return _as_text(node) == expected.strip().lower()


def _as_text(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).lower()


def _merge(base, incoming):
    """Dicts merge recursively, string lists union, anything else replaces.

    Lists of objects replace rather than merge: a hook definition is a whole
    unit, and half-merging two of them produces a config nobody wrote.
    """
    if isinstance(base, dict) and isinstance(incoming, dict):
        merged = dict(base)
        for key, value in incoming.items():
            merged[key] = _merge(merged[key], value) if key in merged else _deep_copy(value)
        return merged
    if (isinstance(base, list) and isinstance(incoming, list)
            and all(isinstance(x, str) for x in base + incoming)):
        return base + [x for x in incoming if x not in base]
    return _deep_copy(incoming)


def _deep_copy(value):
    return json.loads(json.dumps(value))


# ── merging into a file the user may also own ────────────────────────────────

def owned_shape(mapping: dict) -> dict:
    """Key paths the adapter manages. Everything else in the target is preserved."""
    shape: dict = {}
    for fragment in [mapping.get("base", {})] + list(mapping.get("when", {}).values()):
        shape = _merge_shape(shape, fragment)
    return shape


def _merge_shape(shape: dict, fragment) -> dict:
    if not isinstance(fragment, dict):
        return shape
    for key, value in fragment.items():
        if isinstance(value, dict):
            shape[key] = _merge_shape(shape.get(key) or {}, value)
        else:
            shape.setdefault(key, True)
    return shape


def strip_owned(existing, shape):
    """Removes the adapter's key paths, keeping whatever the user added."""
    if not isinstance(existing, dict) or not isinstance(shape, dict):
        return existing
    kept = {}
    for key, value in existing.items():
        if key not in shape:
            kept[key] = value
            continue
        if isinstance(shape[key], dict):
            pruned = strip_owned(value, shape[key])
            if pruned:
                kept[key] = pruned
    return kept


def apply_to_file(target: Path, rendered: dict, shape: dict) -> None:
    existing = {}
    if target.exists():
        try:
            with open(target, encoding="utf-8") as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            raise ValueError(f"{target} is not valid JSON; refusing to overwrite it")
    merged = _merge(strip_owned(existing, shape), rendered)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")
