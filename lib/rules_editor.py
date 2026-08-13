"""
rules_editor.py — Manages SPICE:ROLES and SPICE:SKILLS markers in RULES.md.
"""
import re
from pathlib import Path

# Marker labels
ROLES_MARKER  = "ROLES"
SKILLS_MARKER = "SKILLS"

MANAGED_NOTE = "<!-- managed by spice. do not edit manually. -->"


def _start(label: str) -> str: return f"<!-- SPICE:{label}:START -->"
def _end(label: str)   -> str: return f"<!-- SPICE:{label}:END -->"


def inject_skill(rules_path: Path, name: str, version: str, directive: str) -> bool:
    line = f"- **{name}** (v{version}): {directive}"
    return _inject_line(rules_path, SKILLS_MARKER, line, key=f"**{name}**")


def inject_role(rules_path: Path, name: str, version: str, tier: str,
                description: str, triggers: list[str] | None = None) -> bool:
    triggers = triggers or []
    if triggers:
        triggers_str = ", ".join(f'"{t}"' for t in triggers)
        line = f"- **{name}** (v{version}, tier: {tier}): {description}\n  Triggers: {triggers_str}"
    else:
        line = f"- **{name}** (v{version}, tier: {tier}): {description}"
    return _inject_line(rules_path, ROLES_MARKER, line, key=f"**{name}**")


def remove_skill(rules_path: Path, name: str) -> bool:
    return _remove_line(rules_path, SKILLS_MARKER, key=f"**{name}**")


def remove_role(rules_path: Path, name: str) -> bool:
    return _remove_line(rules_path, ROLES_MARKER, key=f"**{name}**")


_ENTRY_RE = re.compile(r"^- \*\*([^*]+)\*\*", re.MULTILINE)


def listed_entries(rules_path: Path, label: str) -> set[str]:
    """Names currently registered inside a managed block.

    Lets `doctor` compare what RULES.md advertises against what the manifest
    records — they can drift, and nothing used to notice.
    """
    if not rules_path.exists():
        return set()
    section = _section(rules_path.read_text(encoding="utf-8"), label)
    return {m.group(1).strip() for m in _ENTRY_RE.finditer(section)}


def strip_managed(content: str) -> str:
    """Content with managed block bodies emptied, so prose can be diffed."""
    for label in (ROLES_MARKER, SKILLS_MARKER):
        s, e = _start(label), _end(label)
        if s in content and e in content and content.index(s) < content.index(e):
            head = content[:content.index(s) + len(s)]
            tail = content[content.index(e):]
            content = head + "\n" + tail
    return content


def validate_markers(rules_path: Path) -> tuple[bool, list[str]]:
    """Verifies all required markers exist and are well-formed."""
    if not rules_path.exists():
        return False, [f"{rules_path} does not exist"]
    content = rules_path.read_text(encoding="utf-8")
    errors = []
    for label in (ROLES_MARKER, SKILLS_MARKER):
        s, e = _start(label), _end(label)
        if s not in content:
            errors.append(f"Missing marker: {s}")
        if e not in content:
            errors.append(f"Missing marker: {e}")
        if s in content and e in content and content.index(s) > content.index(e):
            errors.append(f"Markers out of order: {label}")
    return (len(errors) == 0), errors


# ── helpers ─────────────────────────────────────────────────────────────────

def _inject_line(rules_path: Path, label: str, line: str, key: str) -> bool:
    content = rules_path.read_text(encoding="utf-8")
    if key in _section(content, label):
        # Replace existing entry with updated one (handles multi-line entries)
        content = _replace_entry_with_key(content, label, key, line)
    else:
        content = _ensure_markers(content, label)
        content = content.replace(_end(label), f"{line}\n{_end(label)}")
    rules_path.write_text(content, encoding="utf-8")
    return True


def _remove_line(rules_path: Path, label: str, key: str) -> bool:
    content = rules_path.read_text(encoding="utf-8")
    section = _section(content, label)
    if key not in section:
        return False
    # Find the entry by key and remove it (entry may be 1 or 2 lines)
    new_content = _remove_entry_with_key(content, label, key)
    rules_path.write_text(new_content, encoding="utf-8")
    return True


def _section(content: str, label: str) -> str:
    s, e = _start(label), _end(label)
    if s not in content or e not in content:
        return ""
    return content[content.index(s):content.index(e)]


def _replace_entry_with_key(content: str, label: str, key: str, new_entry: str) -> str:
    """Replace an entry that starts with a line containing `key`.
    The entry may span multiple lines (continuation lines indented with 2+ spaces)."""
    s, e = _start(label), _end(label)
    start_pos = content.index(s)
    end_pos   = content.index(e)
    before = content[:start_pos + len(s) + 1]  # include newline
    section = content[start_pos + len(s) + 1:end_pos]
    after = content[end_pos:]

    lines = section.splitlines(keepends=True)
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if key in line and line.lstrip().startswith("-"):
            # Replace this entry — skip continuation lines (indented)
            new_lines.append(new_entry + "\n")
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i].startswith("\t")):
                i += 1
            continue
        new_lines.append(line)
        i += 1
    return before + "".join(new_lines) + after


def _remove_entry_with_key(content: str, label: str, key: str) -> str:
    """Remove an entry by key, including continuation lines."""
    s, e = _start(label), _end(label)
    start_pos = content.index(s)
    end_pos   = content.index(e)
    before = content[:start_pos + len(s) + 1]
    section = content[start_pos + len(s) + 1:end_pos]
    after = content[end_pos:]

    lines = section.splitlines(keepends=True)
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if key in line and line.lstrip().startswith("-"):
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i].startswith("\t")):
                i += 1
            continue
        new_lines.append(line)
        i += 1
    return before + "".join(new_lines) + after


def _line_inside_section(content: str, line: str, label: str) -> bool:
    s, e = _start(label), _end(label)
    if s not in content or e not in content:
        return False
    start_pos = content.index(s)
    end_pos   = content.index(e)
    line_pos  = content.find(line)
    return start_pos < line_pos < end_pos


def _ensure_markers(content: str, label: str) -> str:
    s, e = _start(label), _end(label)
    if s in content and e in content:
        return content
    block = f"\n\n{s}\n{MANAGED_NOTE}\n{e}\n"
    return content.rstrip() + block + "\n"
