"""
dep_resolver.py — Resolves component dependencies via frontmatter YAML.
Zero external dependencies (no PyYAML).
"""
import re
from pathlib import Path
from typing import Optional

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_LIST_ITEM_RE   = re.compile(r"^\s*-\s+(.+)$", re.MULTILINE)


def get_frontmatter(component_path: Path) -> dict:
    if component_path.is_dir():
        md = component_path / "SKILL.md"
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
    visited: Optional[set] = None,
) -> list[tuple[str, str]]:
    if visited is None:
        visited = set()
    key = f"{component_type}/{name}"
    if key in visited:
        raise ValueError(f"Circular dependency detected: {key}")
    visited.add(key)

    component_path = _resolve_path(toolkit_root, component_type, name)
    result = []
    for dep in get_depends_on(component_path):
        dep_type, dep_name = _split_key(dep)
        for item in resolve_install_order(toolkit_root, dep_type, dep_name, visited):
            if item not in result:
                result.append(item)
    if (component_type, name) not in result:
        result.append((component_type, name))
    return result


def find_component(toolkit_root: Path, name: str) -> Optional[tuple[str, str]]:
    for ctype in ("skills", "roles", "playbooks", "standards"):
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


def _parse_yaml_simple(yaml_text: str) -> dict:
    """Minimal YAML parser: key: value and lists with dashes."""
    result = {}
    current_key = None
    list_items = []
    for line in yaml_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key:
            item = stripped[2:].strip()
            # Strip surrounding quotes
            if len(item) >= 2 and item[0] == item[-1] and item[0] in ('"', "'"):
                item = item[1:-1]
            list_items.append(item)
            continue
        if ":" in stripped:
            if current_key and list_items:
                result[current_key] = list_items
                list_items = []
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if val:
                # Strip surrounding quotes from scalar values too
                if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                    val = val[1:-1]
                result[key] = val
                current_key = None
            else:
                current_key = key
                list_items = []
    if current_key and list_items:
        result[current_key] = list_items
    return result
