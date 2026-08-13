"""
dep_resolver.py — Resolves component dependencies via frontmatter YAML.
Zero external dependencies (no PyYAML).
"""
import re
from pathlib import Path
from typing import Optional

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_LIST_ITEM_RE   = re.compile(r"^\s*-\s+(.+)$", re.MULTILINE)


DIR_MANIFESTS = ("SKILL.md", "ADAPTER.md")


def get_frontmatter(component_path: Path) -> dict:
    if component_path.is_dir():
        md = next((component_path / n for n in DIR_MANIFESTS
                   if (component_path / n).exists()), component_path / DIR_MANIFESTS[0])
    else:
        md = component_path
    if not md.exists():
        return {}
    text = md.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    return _parse_yaml_simple(m.group(1)) if m else {}


def get_depends_on(component_path: Path) -> list[str]:
    fm = get_frontmatter(component_path)
    raw = fm.get("depends_on", "")
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw]
    return [m.group(1).strip() for m in _LIST_ITEM_RE.finditer(raw)]


def resolve_install_order(
    toolkit_root: Path,
    component_type: str,
    name: str,
    _in_progress: Optional[list] = None,
    _resolved: Optional[set] = None,
) -> list[tuple[str, str]]:
    """Returns dependencies before dependents.

    Cycle detection uses `_in_progress` (the current branch only), while
    `_resolved` deduplicates. Using a single set for both reports a diamond
    (A->B, A->C, B->D, C->D) as a cycle, which it is not.
    """
    if _in_progress is None:
        _in_progress = []
    if _resolved is None:
        _resolved = set()

    key = f"{component_type}/{name}"
    if key in _in_progress:
        cycle = " -> ".join(_in_progress + [key])
        raise ValueError(f"Circular dependency detected: {cycle}")
    if key in _resolved:
        return []

    _in_progress.append(key)
    component_path = _resolve_path(toolkit_root, component_type, name)
    result = []
    for dep in get_depends_on(component_path):
        dep_type, dep_name = _split_key(dep)
        for item in resolve_install_order(toolkit_root, dep_type, dep_name,
                                          _in_progress, _resolved):
            if item not in result:
                result.append(item)
    _in_progress.pop()
    _resolved.add(key)

    result.append((component_type, name))
    return result


def find_component(toolkit_root: Path, name: str) -> Optional[tuple[str, str]]:
    for ctype in ("skills", "adapters", "roles", "playbooks", "standards"):
        if _resolve_path(toolkit_root, ctype, name).exists():
            return (ctype, name)
    return None


# ── helpers ─────────────────────────────────────────────────────────────────

def _resolve_path(toolkit_root: Path, component_type: str, name: str) -> Path:
    as_dir = toolkit_root / component_type / name
    if as_dir.is_dir():
        return as_dir
    as_file = toolkit_root / component_type / f"{name}.md"
    if as_file.exists():
        return as_file
    return as_dir  # caller handles not-found


def _split_key(key: str) -> tuple[str, str]:
    parts = key.strip().split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid dependency format: '{key}'. Use 'type/name'")
    return parts[0], parts[1]


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def _parse_inline_list(value: str) -> list[str]:
    """Parses `[a, b, c]` into a list. Commas inside quotes are not supported."""
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [_unquote(item.strip()) for item in inner.split(",") if item.strip()]


def _parse_yaml_simple(yaml_text: str) -> dict:
    """Minimal YAML parser: `key: value`, `key: [a, b]`, and lists with dashes."""
    result = {}
    current_key = None
    list_items = []
    for line in yaml_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key:
            list_items.append(_unquote(stripped[2:].strip()))
            continue
        if ":" in stripped:
            if current_key and list_items:
                result[current_key] = list_items
                list_items = []
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if val:
                if val.startswith("[") and val.endswith("]"):
                    result[key] = _parse_inline_list(val)
                else:
                    result[key] = _unquote(val)
                current_key = None
            else:
                current_key = key
                list_items = []
    if current_key and list_items:
        result[current_key] = list_items
    return result
