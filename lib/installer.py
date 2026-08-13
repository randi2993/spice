"""
installer.py — Command implementations.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import manifest as mf
import rules_editor as re_mod
import dep_resolver as dr
import providers as prov
import profile as prof

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR    = Path(".agent")

# Directories inside .agent/ owned by the user, never overwritten by a refresh.
USER_OWNED = ("memory", "project")

COMPONENT_TYPES = ("roles", "playbooks", "standards", "skills", "adapters")

# Component types stored as a directory rather than a single .md file.
DIR_COMPONENTS = ("skills", "adapters")


def _color(text: str, *codes: str) -> str:
    """ANSI colour, skipped when output is redirected."""
    if not sys.stdout.isatty():
        return text
    return "".join(codes) + text + "\033[0m"


RED  = "\033[31m"
BOLD = "\033[1m"

def _is_true(value) -> bool:
    """The minimal frontmatter parser yields strings, so `true` arrives as text."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "yes", "1")


def suggested_profile() -> list[tuple[str, str]]:
    """Components flagged `suggested: true` in their own frontmatter.

    This used to be a hardcoded Python list duplicating the flags in
    manifest.json, so adding a suggested component meant editing three places
    and nothing detected a disagreement between them.
    """
    profile = []
    for ctype in ("roles", "playbooks", "standards", "skills", "adapters"):
        for name, fm in _discover_components(ctype):
            if _is_true(fm.get("suggested")):
                profile.append((ctype, name))
    return profile


# ── init ────────────────────────────────────────────────────────────────────

def cmd_init(args):
    assume_yes = getattr(args, "yes", False)

    if AGENT_DIR.exists():
        if not args.force:
            print("[spice] .agent/ already exists in this directory.")
            print("        Use --force to refresh templates, or 'spice factory-reset'")
            print("        to delete everything and start over.")
            sys.exit(1)
        _refresh_existing()
        return

    print("[spice] Initializing .agent/ ...")
    _copy_core()
    _create_root_entrypoints()
    _init_manifest()

    # Install suggested profile
    if assume_yes:
        print("\n[spice] --yes: installing suggested minimal profile.")
        answer = "y"
    else:
        print("\n[spice] Install suggested minimal profile? [Y/n]: ", end="", flush=True)
        answer = input().strip().lower()
    if answer in ("", "y", "yes"):
        manifest = mf.load(AGENT_DIR)
        for ctype, name in suggested_profile():
            _install_single(ctype, name, manifest, quiet=False)
        mf.save(AGENT_DIR, manifest)
        print("\n[spice] Minimal profile installed.")
    else:
        print("[spice] Profile skipped. Use 'spice add <component>' when ready.")

    # Onboarding
    if assume_yes:
        print("\n[spice] --yes: skipping interactive onboarding.")
        print("        Run 'spice onboard' when you want to fill in project context.")
    elif not getattr(args, "no_onboard", False):
        print("\n[spice] Run interactive onboarding now? [Y/n]: ", end="", flush=True)
        answer = input().strip().lower()
        if answer in ("", "y", "yes"):
            _run_onboarding()

    print("\n[spice] Done. Open Claude Code (or your CLI of choice) in this project.")


def _refresh_existing():
    """`init --force`: refresh toolkit templates, keep everything the user owns.

    It used to delete .agent/ wholesale, taking ADRs, learned facts, project
    state and run history with it. Wiping is now 'spice factory-reset'.
    """
    print("[spice] Refreshing .agent/ templates ...")
    print(f"        Preserved: {', '.join(d + '/' for d in USER_OWNED)}, installed.json")

    manifest = mf.load(AGENT_DIR)
    _copy_core(preserve_user_data=True)
    _create_root_entrypoints()
    mf.save(AGENT_DIR, manifest)

    # RULES.md came back as a blank template, so its roster must be rebuilt
    # from the manifest or the two would silently disagree.
    restored = _reinject_roster(manifest)
    print(f"[spice] Templates refreshed. {restored} component(s) re-registered in RULES.md.")


def _copy_core(preserve_user_data: bool = False):
    core_src = TOOLKIT_ROOT / "core"
    if not AGENT_DIR.exists():
        shutil.copytree(core_src, AGENT_DIR)
        return
    if not preserve_user_data:
        shutil.rmtree(AGENT_DIR)
        shutil.copytree(core_src, AGENT_DIR)
        return
    for item in core_src.iterdir():
        dest = AGENT_DIR / item.name
        if item.name in USER_OWNED and dest.exists():
            continue
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


def _installed_phases() -> dict[str, list[str]]:
    """phase -> installed role names, read from the role files in the project."""
    phases: dict[str, list[str]] = {}
    roles_dir = AGENT_DIR / "roles"
    if not roles_dir.exists():
        return phases
    for role_file in sorted(roles_dir.glob("*.md")):
        phase = dr.get_frontmatter(role_file).get("phase")
        if not phase or phase == re_mod.ON_DEMAND:
            continue
        phases.setdefault(str(phase), []).append(role_file.stem)
    return phases


def _regenerate_workflows() -> None:
    """Rewrites the workflow block so it can only name installed roles."""
    rules_path = AGENT_DIR / "RULES.md"
    body = re_mod.render_workflows(_installed_phases())
    re_mod.set_block(rules_path, re_mod.WORKFLOWS_MARKER, body)


def _reinject_roster(manifest: dict) -> int:
    """Rebuilds the SPICE:ROLES / SPICE:SKILLS blocks from the manifest."""
    rules_path = AGENT_DIR / "RULES.md"
    count = 0
    for entry in manifest.get("components", {}).values():
        ctype, name = entry["type"], entry["name"]
        src = _toolkit_component_path(ctype, name)
        if not src.exists():
            continue
        fm = dr.get_frontmatter(src)
        if ctype == "roles":
            triggers = fm.get("triggers", [])
            if isinstance(triggers, str):
                triggers = [triggers]
            re_mod.inject_role(rules_path, name, entry["version"],
                               entry.get("tier") or "standard",
                               fm.get("description", ""), triggers)
            count += 1
        elif ctype == "skills":
            directive = fm.get("shared_directive", "")
            if directive:
                re_mod.inject_skill(rules_path, name, entry["version"], directive)
                count += 1
    _regenerate_workflows()
    return count


def _create_root_entrypoints():
    content = "Read `.agent/RULES.md` and follow all instructions before executing any task.\n"
    for fname in ("CLAUDE.md", "GEMINI.md"):
        p = Path(fname)
        existing = p.read_text(encoding="utf-8") if p.exists() else ""
        if existing.strip() == content.strip():
            continue  # already correct
        p.write_text(content, encoding="utf-8")
        action = "updated" if existing else "created"
        print(f"  {action}: {fname}")


def _init_manifest():
    mf.save(AGENT_DIR, mf.load(AGENT_DIR))


# ── add ─────────────────────────────────────────────────────────────────────

def cmd_add(args):
    _require_agent_dir()
    if args.from_path:
        src = Path(args.from_path)
        if not src.exists():
            print(f"[spice] Path not found: {args.from_path}")
            sys.exit(1)
        ctype, name = _infer_type_from_path(src)
        manifest = mf.load(AGENT_DIR)
        _install_single(ctype, name, manifest, quiet=False, src_override=src)
        mf.save(AGENT_DIR, manifest)
        return

    ctype, name = _parse_component_key(args.component)
    try:
        order = dr.resolve_install_order(TOOLKIT_ROOT, ctype, name)
    except ValueError as e:
        print(f"[spice] Dependency error: {e}")
        sys.exit(1)
    manifest = mf.load(AGENT_DIR)
    for dep_type, dep_name in order:
        _install_single(dep_type, dep_name, manifest, quiet=False)
        # Saved after each component: a missing dependency aborts the loop, and
        # everything copied before it used to be left on disk unrecorded.
        mf.save(AGENT_DIR, manifest)


def _install_single(ctype: str, name: str, manifest: dict, quiet: bool = True,
                    src_override: Path | None = None):
    src = src_override or _toolkit_component_path(ctype, name)
    if not src.exists():
        print(f"[spice] Component not found in toolkit: {ctype}/{name}")
        sys.exit(1)

    fm = dr.get_frontmatter(src)
    version = fm.get("version", "0.0.0")
    tier    = fm.get("tier")  # only for roles

    # Declared in every skill's frontmatter and documented in the README, but
    # never actually checked, so it promised a compatibility gate that did not
    # exist.
    required = fm.get("min_toolkit_version")
    if required and _version_tuple(mf.toolkit_version()) < _version_tuple(str(required)):
        print(f"[spice] {ctype}/{name} needs toolkit v{required}, "
              f"this one is v{mf.toolkit_version()}.")
        print(f"        Run 'spice update' to upgrade the toolkit first.")
        sys.exit(1)

    if mf.is_installed(manifest, ctype, name):
        installed_ver = mf.get_version(manifest, ctype, name)
        if installed_ver == version:
            if not quiet:
                print(f"  · {ctype}/{name} v{version} already installed, skipping.")
            return

    # Copy files
    dest = _agent_component_dest(ctype, name)
    if src.is_dir():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    # Inject into RULES.md
    rules_path = AGENT_DIR / "RULES.md"
    if ctype == "skills":
        directive = fm.get("shared_directive", "")
        if directive:
            re_mod.inject_skill(rules_path, name, version, directive)
            if not quiet:
                print(f"    -> directive injected into RULES.md")
    elif ctype == "roles":
        description = fm.get("description", "")
        tier_str = tier or "standard"
        triggers = fm.get("triggers", [])
        if isinstance(triggers, str):
            triggers = [triggers]
        re_mod.inject_role(rules_path, name, version, tier_str, description, triggers)
        _regenerate_workflows()
        if not quiet:
            trig_info = f", {len(triggers)} triggers" if triggers else ""
            print(f"    -> role registered in RULES.md (tier: {tier_str}{trig_info})")

    elif ctype == "adapters":
        _install_adapter_hooks(name)
        applied = _render_adapter(name)
        if applied and not quiet:
            print(f"    -> rendered {applied}")

    deps = dr.get_depends_on(src)
    mf.record(manifest, ctype, name, version, deps, tier=tier)

    if not quiet:
        print(f"  + {ctype}/{name} v{version}")


# ── remove ───────────────────────────────────────────────────────────────────

def cmd_remove(args):
    _require_agent_dir()
    ctype, name = _parse_component_key(args.component)
    manifest = mf.load(AGENT_DIR)

    if not mf.is_installed(manifest, ctype, name):
        print(f"[spice] {ctype}/{name} is not installed.")
        sys.exit(1)

    dependents = mf.dependents_of(manifest, ctype, name)
    if dependents:
        print(f"[spice] Warning: these components depend on {ctype}/{name}:")
        for d in dependents:
            print(f"          - {d}")
        print("Continue anyway? [y/N]: ", end="", flush=True)
        if input().strip().lower() not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    if not args.yes:
        print(f"Remove {ctype}/{name}? [y/N]: ", end="", flush=True)
        if input().strip().lower() not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    dest = _agent_component_dest(ctype, name)
    if dest.is_dir():
        shutil.rmtree(dest)
    elif dest.exists():
        dest.unlink()

    rules_path = AGENT_DIR / "RULES.md"
    if rules_path.exists():
        if ctype == "skills":
            re_mod.remove_skill(rules_path, name)
        elif ctype == "roles":
            re_mod.remove_role(rules_path, name)
            # Workflows are derived from the roster, so uninstalling a role
            # removes it from the flows instead of leaving a dangling name.
            _regenerate_workflows()

    mf.remove_record(manifest, ctype, name)
    mf.save(AGENT_DIR, manifest)
    print(f"[spice] Removed {ctype}/{name}.")


# ── profile & adapters ───────────────────────────────────────────────────────

def cmd_profile(args):
    _require_agent_dir()
    sub = getattr(args, "profile_command", None) or "show"

    if sub == "list":
        catalog = prof.available()
        active = (prof.load(AGENT_DIR) or {}).get("profile")
        print("[spice] Available profiles:\n")
        for name, spec in catalog.get("profiles", {}).items():
            marker = "*" if name == active else " "
            print(f"  {marker} {name:<10} {spec.get('description', '')}")
        print("\n  * = active in this project")
        return

    if sub == "set":
        try:
            profile = prof.build(args.name)
        except ValueError as e:
            print(f"[spice] {e}")
            sys.exit(1)
        previous = prof.load(AGENT_DIR)
        if previous:
            profile["exceptions"] = previous.get("exceptions", [])
        prof.save(AGENT_DIR, profile)
        print(f"[spice] Profile set to '{args.name}'.")
        rendered = _render_all_adapters()
        if rendered:
            for target in rendered:
                print(f"  -> re-rendered {target}")
        else:
            print("  ! No adapters installed, so nothing enforces this profile.")
            print("    Install one with 'spice add adapters/claude'.")
        return

    # show
    profile = prof.load(AGENT_DIR)
    if not profile:
        default = prof.available().get("default", "standard")
        print(f"[spice] No profile set. Commands behave as '{default}' would "
              f"describe, but nothing enforces it.")
        print(f"        Set one with 'spice profile set <name>'.")
        return
    print(f"  profile:     {profile.get('profile')}")
    print(f"  perimeter:   {_format_flags(profile.get('perimeter', {}))}")
    print(f"  capabilities:{_format_flags(profile.get('capabilities', {}))}")
    for exception in profile.get("exceptions", []):
        print(f"  exception:   {exception}")

    print("\n  coverage:")
    for line in _coverage_lines():
        print(f"    {line}")


# Root entry point -> the adapter that enforces the profile for that tool.
ENTRY_POINTS = {"CLAUDE.md": "claude", "GEMINI.md": "gemini"}


def _coverage_lines() -> list[str]:
    """Which tools are actually protected, and which only read the rules.

    Every entry point delivers the full declarative layer — RULES.md, the
    roles, standards/perimeter.md. Only a tool with an adapter also gets
    enforcement. Stating that per tool keeps the gap visible instead of
    leaving it to be inferred from a list of installed adapters.
    """
    installed = set(_installed_adapters())
    lines = []
    for entry, adapter in sorted(ENTRY_POINTS.items()):
        if not Path(entry).exists():
            continue
        if adapter in installed:
            lines.append(f"{entry:<12} enforced by adapters/{adapter}")
        else:
            available = (TOOLKIT_ROOT / "adapters" / adapter).exists()
            hint = (f"install adapters/{adapter}" if available
                    else "no adapter exists yet for this tool")
            lines.append(f"{entry:<12} rules only, nothing enforces them  ({hint})")
    for adapter in sorted(installed):
        if adapter not in ENTRY_POINTS.values():
            lines.append(f"{'(' + adapter + ')':<12} adapter installed with no known entry point")
    return lines or ["no root entry points found"]


def _format_flags(flags: dict) -> str:
    if not flags:
        return " (none)"
    return " " + ", ".join(f"{k}={'yes' if v else 'no'}" if isinstance(v, bool)
                           else f"{k}={v}" for k, v in flags.items())


def _installed_adapters() -> list[str]:
    base = AGENT_DIR / "adapters"
    if not base.exists():
        return []
    return [d.name for d in base.iterdir() if (d / "mapping.json").exists()]


def _install_adapter_hooks(name: str) -> None:
    """Copies an adapter's hook scripts into .agent/hooks/.

    They live under the adapter, not in a shared directory: guard-paths.js
    speaks Claude Code's hook protocol — its stdin payload and its deny
    response are that tool's schema. A directory called `_shared` holding a
    tool-specific script is a trap for whoever writes the next adapter.
    """
    src = TOOLKIT_ROOT / "adapters" / name / "hooks"
    if not src.exists():
        return
    dest = AGENT_DIR / "hooks"
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.is_file():
            shutil.copy2(item, dest / item.name)


def _render_adapter(name: str) -> str | None:
    mapping_path = AGENT_DIR / "adapters" / name / "mapping.json"
    if not mapping_path.exists():
        return None
    with open(mapping_path, encoding="utf-8") as f:
        mapping = json.load(f)
    profile = prof.load_or_default(AGENT_DIR)
    target = Path(mapping["target"])
    try:
        prof.apply_to_file(target, prof.render(profile, mapping),
                           prof.owned_shape(mapping))
    except ValueError as e:
        print(f"[spice] {e}")
        return None
    return mapping["target"]


def _render_all_adapters() -> list[str]:
    return [t for t in (_render_adapter(n) for n in _installed_adapters()) if t]


# ── factory-reset ────────────────────────────────────────────────────────────

def cmd_factory_reset(args):
    """Deletes .agent/ entirely. This is what `init --force` used to do silently."""
    _require_agent_dir()

    print()
    print(_color("  ╔════════════════════════════════════════════════════════╗", RED, BOLD))
    print(_color("  ║                     FACTORY RESET                      ║", RED, BOLD))
    print(_color("  ╚════════════════════════════════════════════════════════╝", RED, BOLD))
    print()
    print(_color("  This DELETES .agent/ and everything inside it.", RED))
    print("  The following will be permanently lost:")
    print()
    for line in _reset_inventory():
        print(f"    - {line}")
    print()
    print("  If you only want fresh templates, cancel and run 'spice init --force'")
    print("  instead — it keeps memory/ and project/.")
    print()

    if not getattr(args, "yes", False):
        print(_color("  Type 'reset' to confirm: ", RED, BOLD), end="", flush=True)
        if input().strip().lower() != "reset":
            print("[spice] Aborted. Nothing was deleted.")
            sys.exit(0)

    shutil.rmtree(AGENT_DIR)
    print(f"[spice] .agent/ deleted. Run 'spice init' to start over.")


def _reset_inventory() -> list[str]:
    """What the user actually loses, with enough detail to think twice."""
    items = []
    mem = AGENT_DIR / "memory"
    if mem.exists():
        for f in sorted(mem.glob("*.md")):
            items.append(f"memory/{f.name}  ({_content_lines(f)} non-empty lines)")
        runs = mem / "runs"
        if runs.exists():
            items.append(f"memory/runs/  ({len(list(runs.glob('*')))} file(s))")
    ctx = AGENT_DIR / "project" / "CONTEXT.md"
    if ctx.exists():
        items.append(f"project/CONTEXT.md  ({_content_lines(ctx)} non-empty lines)")
    arch = AGENT_DIR / "project" / "architecture.md"
    if arch.exists():
        items.append(f"project/architecture.md  ({_content_lines(arch)} non-empty lines)")
    n = len(mf.load(AGENT_DIR).get("components", {}))
    items.append(f"{n} installed component(s)")
    return items


def _content_lines(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return sum(1 for line in text.splitlines()
               if line.strip() and not line.strip().startswith(("#", "<!--", ">")))


# ── path ─────────────────────────────────────────────────────────────────────

def cmd_path(args):
    """Shows which spice is running and where its data lives."""
    launcher = _launcher_path()
    providers_file = prov.PROVIDERS_FILE

    print(f"  toolkit:    {TOOLKIT_ROOT}")
    print(f"  launcher:   {launcher if launcher else '(not found)'}")
    print(f"  providers:  {providers_file}"
          f"{'' if providers_file.exists() else '   (not created yet)'}")
    if AGENT_DIR.exists():
        print(f"  project:    {AGENT_DIR.resolve()}")
    else:
        print(f"  project:    (no .agent/ in {Path.cwd()})")

    if getattr(args, "open", False):
        _open_in_file_manager(TOOLKIT_ROOT)


def _launcher_path() -> Path | None:
    candidates = ["spice.bat", "spice.py"] if sys.platform == "win32" else ["spice.py"]
    for name in candidates:
        candidate = TOOLKIT_ROOT / "bin" / name
        if candidate.exists():
            return candidate
    return None


def _open_in_file_manager(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
        print(f"[spice] Opened {path}")
    except Exception as e:
        print(f"[spice] Could not open {path}: {e}")


# ── list ─────────────────────────────────────────────────────────────────────

def cmd_list(args):
    if getattr(args, "available", False) or getattr(args, "all", False):
        _list_available()
    else:
        _list_installed()


def _list_installed():
    _require_agent_dir()
    manifest = mf.load(AGENT_DIR)
    components = manifest.get("components", {})
    if not components:
        print("[spice] No components installed. Use 'spice add <component>'.")
        print("        See available with: spice list --available")
        return

    by_type: dict[str, list] = {}
    for key, entry in sorted(components.items()):
        by_type.setdefault(entry["type"], []).append(entry)

    print(f"[spice] Toolkit v{manifest.get('toolkit_version', '?')}  (installed components)\n")
    for ctype in COMPONENT_TYPES:
        if ctype not in by_type:
            continue
        print(f"  {ctype.upper()}")
        for entry in by_type[ctype]:
            tier = entry.get("tier")
            tier_str = f"  (tier: {tier})" if tier else ""
            deps = entry.get("depends_on", [])
            dep_str = f"  [deps: {', '.join(deps)}]" if deps else ""
            print(f"    {entry['name']:<28} v{entry['version']}{tier_str}{dep_str}")
        print()


def _list_available():
    """Show all components in the toolkit, marking which are installed."""
    installed_keys = set()
    if AGENT_DIR.exists():
        manifest = mf.load(AGENT_DIR)
        installed_keys = set(manifest.get("components", {}).keys())

    print("[spice] Available components in toolkit:")
    print("        [✓] = installed in current project\n")

    for ctype in COMPONENT_TYPES:
        components = _discover_components(ctype)
        if not components:
            continue
        print(f"  {ctype.upper()}")
        for name, fm in components:
            marker = "[✓]" if f"{ctype}/{name}" in installed_keys else "[ ]"
            version = fm.get("version", "?")
            labels = [v for v in (fm.get("tier"), fm.get("phase"), fm.get("category")) if v]
            label_str = f"  ({', '.join(labels)})" if labels else ""
            desc = fm.get("description", "")
            desc_str = f" — {desc}" if desc else ""
            print(f"    {marker} {name:<22} v{version}{label_str}{desc_str}")
        print()

    print("Install with: spice add <type>/<name>   (e.g. spice add roles/documenter)")
    print("Match your stack:  spice suggest")


def cmd_search(args):
    query = args.query.lower()
    print(f"[spice] Searching for '{query}'...\n")

    installed_keys = set()
    if AGENT_DIR.exists():
        manifest = mf.load(AGENT_DIR)
        installed_keys = set(manifest.get("components", {}).keys())

    found = False
    for ctype in COMPONENT_TYPES:
        components = _discover_components(ctype)
        matches = []
        for name, fm in components:
            haystack = [name.lower(), (fm.get("description") or "").lower()]
            for field in ("keywords", "applies_to", "category"):
                value = fm.get(field) or []
                haystack.extend(v.lower() for v in
                                ([value] if isinstance(value, str) else value))
            if any(query in part for part in haystack):
                matches.append((name, fm))
        if not matches:
            continue
        found = True
        print(f"  {ctype.upper()}")
        for name, fm in matches:
            marker = "[✓]" if f"{ctype}/{name}" in installed_keys else "[ ]"
            version = fm.get("version", "?")
            labels = [v for v in (fm.get("tier"), fm.get("phase"), fm.get("category")) if v]
            label_str = f"  ({', '.join(labels)})" if labels else ""
            desc = fm.get("description", "")
            desc_str = f" — {desc}" if desc else ""
            print(f"    {marker} {name:<22} v{version}{label_str}{desc_str}")
        print()

    if not found:
        print("  No components found matching that query.")


def _discover_components(ctype: str) -> list[tuple[str, dict]]:
    """List all components of a given type in the toolkit with their frontmatter."""
    base = TOOLKIT_ROOT / ctype
    if not base.exists():
        return []
    result = []
    if ctype in DIR_COMPONENTS:
        manifest_name = "SKILL.md" if ctype == "skills" else "ADAPTER.md"
        for d in sorted(base.iterdir()):
            if d.is_dir() and (d / manifest_name).exists():
                result.append((d.name, dr.get_frontmatter(d / manifest_name)))
    else:
        # roles, playbooks, standards are .md files
        for f in sorted(base.glob("*.md")):
            fm = dr.get_frontmatter(f)
            result.append((f.stem, fm))
    return result


# ── suggest ──────────────────────────────────────────────────────────────────

def cmd_suggest(args):
    _require_agent_dir()
    tags = detect_tags()
    if not tags:
        print("[spice] No stack detected in this directory.")
        print("        Nothing to suggest. Browse with 'spice list --available'.")
        return

    print(f"[spice] Detected: {', '.join(sorted(tags))}\n")
    matches = _matching_skills(tags)
    if not matches:
        print("  No skill in the toolkit targets this stack yet.")
        print("  See 'spice list --available' for what exists.")
        return

    for name, fm, matched in matches:
        print(f"  skills/{name}  (matches: {', '.join(sorted(matched))})")
        if fm.get("description"):
            print(f"    {fm['description']}")

    print()
    manifest = mf.load(AGENT_DIR)
    for name, _, _ in matches:
        if getattr(args, "yes", False):
            answer = "y"
            print(f"[spice] --yes: installing skills/{name}")
        else:
            print(f"Install skills/{name}? [y/N]: ", end="", flush=True)
            answer = input().strip().lower()
        if answer in ("y", "yes"):
            _install_single("skills", name, manifest, quiet=False)
            mf.save(AGENT_DIR, manifest)


def _matching_skills(tags: set[str]) -> list[tuple[str, dict, set[str]]]:
    """Uninstalled skills whose applies_to intersects the detected tags."""
    installed = set(mf.load(AGENT_DIR).get("components", {}))
    matches = []
    for name, fm in _discover_components("skills"):
        if f"skills/{name}" in installed:
            continue
        applies = fm.get("applies_to") or []
        if isinstance(applies, str):
            applies = [applies]
        overlap = {a.strip().lower() for a in applies} & tags
        if overlap:
            matches.append((name, fm, overlap))
    return matches


# ── update ───────────────────────────────────────────────────────────────────

def cmd_update(args):
    """Reconciles this project with the installed toolkit. Never touches the
    toolkit itself — that is `spice self-update`."""
    _require_agent_dir()
    print(f"[spice] Reconciling with toolkit v{mf.toolkit_version()} at {TOOLKIT_ROOT}")

    drift = _core_drift()
    if drift:
        print("[spice] Core templates differ from the toolkit:")
        for name in drift:
            print(f"  ~ {name}")
        if getattr(args, "refresh_core", False) and not args.check:
            _refresh_existing()
        else:
            print("        Run 'spice update --refresh-core' to apply them")
            print("        (memory/ and project/ are preserved).")

    if args.check:
        print("[spice] --check mode: no changes applied.")
        return

    manifest = mf.load(AGENT_DIR)
    components = list(manifest.get("components", {}).values())
    updated = 0
    skipped: list[str] = []
    for entry in components:
        ctype, name = entry["type"], entry["name"]
        src = _toolkit_component_path(ctype, name)
        if not src.exists():
            continue
        new_ver = dr.get_frontmatter(src).get("version", "0.0.0")
        if new_ver == entry["version"]:
            continue
        if _version_tuple(new_ver) < _version_tuple(entry["version"]):
            if not getattr(args, "allow_downgrade", False):
                skipped.append(f"{ctype}/{name}: v{entry['version']} → v{new_ver}")
                continue
            print(f"  {ctype}/{name}: v{entry['version']} → v{new_ver}  (DOWNGRADE)")
        else:
            print(f"  {ctype}/{name}: v{entry['version']} → v{new_ver}")
        _install_single(ctype, name, manifest, quiet=True)
        updated += 1

    manifest["toolkit_version"] = mf.toolkit_version()
    mf.save(AGENT_DIR, manifest)

    if skipped:
        print("[spice] Skipped (toolkit has an older version than installed):")
        for line in skipped:
            print(f"  ! {line}")
        print("        Use --allow-downgrade to apply them anyway.")
    print(f"[spice] {updated} component(s) updated." if updated else "[spice] Up to date.")


SOURCE_MARKER = "install-source.txt"


def cmd_self_update(args):
    """Upgrades the toolkit itself. `spice update` only touches the project.

    They used to be one command: `spice update`, run inside a project, did a
    git pull on the shared toolkit and so changed every other project on the
    machine. It also could not work at all on a normal install — install.bat
    uses xcopy, which skips hidden entries, so the installed copy has no .git
    and the pull failed outright.
    """
    source = _toolkit_source()
    if source is None:
        print("[spice] Cannot locate the toolkit source checkout.")
        print(f"        The installed copy at {TOOLKIT_ROOT} is not a git repository")
        print(f"        and no {SOURCE_MARKER} recorded where it came from.")
        print("        Update manually: git pull in your spice clone, then run the installer.")
        sys.exit(1)

    before = mf.toolkit_version()
    print(f"[spice] Toolkit source: {source}")

    if getattr(args, "check", False):
        _git_report(source)
        return

    try:
        result = subprocess.run(["git", "pull", "--ff-only"], cwd=source,
                                capture_output=True, text=True)
    except FileNotFoundError:
        print("[spice] git not found in PATH.")
        sys.exit(1)
    if result.returncode != 0:
        print("[spice] git pull failed:")
        print(f"        {result.stderr.strip()}")
        sys.exit(1)
    print(f"        {result.stdout.strip()}")

    if source == TOOLKIT_ROOT:
        after = mf.toolkit_version()
        print(f"[spice] Toolkit v{before} -> v{after}." if before != after
              else f"[spice] Already at v{after}.")
        print("        Run 'spice update' in each project to apply it.")
        return

    # Installed copy is separate from the source, so the pull alone changes
    # nothing until the installer runs again.
    installer = "install.bat" if sys.platform == "win32" else "install.sh"
    print(f"[spice] Source updated. The installed copy at {TOOLKIT_ROOT} is unchanged.")
    print(f"        Reinstall to apply it:  cd {source} && {installer}")
    print(f"        Then run 'spice update' in each project.")


def _toolkit_source() -> Path | None:
    """Where the toolkit is developed: this copy if cloned, else what the
    installer recorded."""
    if (TOOLKIT_ROOT / ".git").exists():
        return TOOLKIT_ROOT
    marker = TOOLKIT_ROOT / SOURCE_MARKER
    if marker.exists():
        candidate = Path(marker.read_text(encoding="utf-8").strip())
        if (candidate / ".git").exists():
            return candidate
    return None


def _git_report(source: Path) -> None:
    try:
        subprocess.run(["git", "fetch"], cwd=source, capture_output=True, text=True)
        result = subprocess.run(["git", "log", "--oneline", "HEAD..@{u}"],
                                cwd=source, capture_output=True, text=True)
    except FileNotFoundError:
        print("[spice] git not found in PATH.")
        return
    pending = result.stdout.strip()
    print(f"[spice] {len(pending.splitlines())} commit(s) available:" if pending
          else "[spice] Toolkit is up to date.")
    if pending:
        for line in pending.splitlines():
            print(f"          {line}")


def _core_drift() -> list[str]:
    """core/ files that differ from the toolkit template.

    `update` only ever reinstalled manifest components, so RULES.md and the
    config templates never reached projects already initialised. User-owned
    directories are excluded — their contents are supposed to differ.
    """
    core_src = TOOLKIT_ROOT / "core"
    if not core_src.exists():
        return []
    drifted = []
    for item in sorted(core_src.rglob("*")):
        if item.is_dir():
            continue
        rel = item.relative_to(core_src)
        if rel.parts and rel.parts[0] in USER_OWNED:
            continue
        dest = AGENT_DIR / rel
        if not dest.exists():
            drifted.append(f"{rel.as_posix()}  (missing)")
            continue
        if _normalised(item) != _normalised(dest, strip_markers=rel.name == "RULES.md"):
            drifted.append(rel.as_posix())
    return drifted


def _normalised(path: Path, strip_markers: bool = False) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if strip_markers:
        text = re_mod.strip_managed(text)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def _version_tuple(version: str) -> tuple[int, int, int]:
    """Loose semver parse for comparison. Non-numeric chunks count as 0."""
    parts = []
    for chunk in str(version).split(".")[:3]:
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)  # type: ignore[return-value]


# ── doctor ───────────────────────────────────────────────────────────────────

def cmd_doctor(args):
    _require_agent_dir()
    errors: list[str] = []
    warnings: list[str] = []

    manifest = mf.load(AGENT_DIR)
    components = manifest.get("components", {})
    rules_path = AGENT_DIR / "RULES.md"

    # 1. Files and directories that ship with core/ and always exist.
    for fname in ("RULES.md", "installed.json",
                  "project/CONTEXT.md", "project/architecture.md"):
        if not (AGENT_DIR / fname).exists():
            errors.append(f"Missing core file: .agent/{fname}")
    for sub in ("config", "memory", "project"):
        if not (AGENT_DIR / sub).exists():
            errors.append(f"Missing directory: .agent/{sub}/")

    # 2. Component directories are required only when components of that type
    #    are installed. A docs project with a single role and no git playbook
    #    is a valid install, and used to be reported as three errors.
    for ctype in sorted({e["type"] for e in components.values()}):
        if not (AGENT_DIR / ctype).exists():
            errors.append(f"Missing .agent/{ctype}/ but the manifest records "
                          f"components of that type")

    # 3. RULES.md markers
    if rules_path.exists():
        _, marker_errors = re_mod.validate_markers(rules_path)
        errors.extend(f"RULES.md: {e}" for e in marker_errors)

    # 4. Manifest -> disk
    for key, entry in components.items():
        ctype, name = entry["type"], entry["name"]
        dest = _agent_component_dest(ctype, name)
        if not dest.exists():
            errors.append(f"In manifest but not on disk: {key}")
            continue
        fm = dr.get_frontmatter(dest)
        disk_ver = fm.get("version", "0.0.0")
        if disk_ver != entry["version"]:
            warnings.append(f"Version mismatch for {key}: "
                            f"manifest={entry['version']}, disk={disk_ver}")
        if ctype == "roles":
            if "tier" not in fm:
                warnings.append(f"Role {name} has no 'tier' in frontmatter")
            elif fm["tier"] not in ("light", "standard", "heavy"):
                errors.append(f"Role {name}: invalid tier '{fm['tier']}'. "
                              f"Must be light|standard|heavy")

    # 5. Disk -> manifest. An aborted install could leave files behind with no
    #    record; only the opposite direction was ever checked.
    for key in sorted(_components_on_disk() - set(components)):
        warnings.append(f"On disk but not in manifest: {key}  "
                        f"(reinstall it, or delete the file)")

    # 6. Manifest -> RULES.md roster. These drift silently: reinstalling the
    #    same version returns early, before the RULES.md injection.
    if rules_path.exists():
        listed_roles = re_mod.listed_entries(rules_path, re_mod.ROLES_MARKER)
        expected_roles = {e["name"] for e in components.values() if e["type"] == "roles"}
        for name in sorted(expected_roles - listed_roles):
            errors.append(f"Role '{name}' is installed but missing from the "
                          f"RULES.md roster")
        for name in sorted(listed_roles - expected_roles):
            errors.append(f"Role '{name}' is listed in RULES.md but not installed")

    # 7. Dangling references in memory. Reported, never removed: an outdated
    #    pointer is worth less than the reasoning it sits next to.
    warnings.extend(_memory_reference_warnings())

    # 8. Execution protocol coverage
    if not any(e["type"] == "roles" for e in components.values()):
        warnings.append("No roles installed — the RULES.md execution protocol "
                        "requires adopting roles it cannot find")
    else:
        phase_roles = _installed_phases()
        for role_file in sorted((AGENT_DIR / "roles").glob("*.md")):
            phase = dr.get_frontmatter(role_file).get("phase")
            if not phase:
                warnings.append(f"Role {role_file.stem} has no 'phase' in "
                                f"frontmatter and cannot appear in any workflow")
            elif phase not in re_mod.KNOWN_PHASES:
                errors.append(f"Role {role_file.stem}: unknown phase '{phase}'. "
                              f"Must be one of {', '.join(sorted(re_mod.KNOWN_PHASES))}")
        for level in re_mod.uncovered_classifications(phase_roles):
            warnings.append(f"Classification '{level}' has no installed role to "
                            f"serve it")

    if rules_path.exists():
        content = rules_path.read_text(encoding="utf-8", errors="replace")
        if "SPICE:WORKFLOWS:START" not in content:
            warnings.append("RULES.md predates generated workflows — run "
                            "'spice update --refresh-core'")

    # 9. Perimeter. A guard that is declared but not actually wired is worse
    #    than none: it produces confidence without protection.
    adapters = _installed_adapters()
    profile = prof.load(AGENT_DIR)
    if profile and not adapters:
        warnings.append(f"Profile '{profile.get('profile')}' is declared but no "
                        f"adapter is installed, so nothing enforces it")
    if adapters and not profile:
        warnings.append("Adapters installed but no profile set — they rendered "
                        "the default. Run 'spice profile set <name>'")
    for name in adapters:
        errors.extend(_adapter_errors(name))

    # An entry point with no adapter is not an error — the tool still gets the
    # full declarative layer. But it must be visible, or a project looks
    # uniformly protected when only one of its tools actually is.
    if profile:
        for entry, adapter in sorted(ENTRY_POINTS.items()):
            if Path(entry).exists() and adapter not in adapters:
                warnings.append(f"{entry} exists but adapters/{adapter} is not "
                                f"installed — that tool reads the rules with "
                                f"nothing enforcing them")

    # 10. Root entry points
    for fname in ("CLAUDE.md", "GEMINI.md"):
        if not Path(fname).exists():
            warnings.append(f"Missing root entry point: {fname}")

    if not errors and not warnings:
        print("[spice] All checks passed.")
        return
    if errors:
        print("[spice] ERRORS:")
        for e in errors:
            print(f"  x {e}")
    if warnings:
        print("[spice] WARNINGS:")
        for w in warnings:
            print(f"  ! {w}")
    if errors:
        sys.exit(1)


def _adapter_errors(name: str) -> list[str]:
    """Checks the adapter is actually wired, not merely present."""
    out = []
    mapping_path = AGENT_DIR / "adapters" / name / "mapping.json"
    if not mapping_path.exists():
        return [f"Adapter {name} has no mapping.json"]
    with open(mapping_path, encoding="utf-8") as f:
        mapping = json.load(f)

    target = Path(mapping["target"])
    if not target.exists():
        return [f"Adapter {name} declares {mapping['target']} but the file is "
                f"missing — run 'spice profile set <name>' to render it"]

    try:
        with open(target, encoding="utf-8") as f:
            actual = json.load(f)
    except json.JSONDecodeError:
        return [f"{mapping['target']} is not valid JSON"]

    expected = prof.render(prof.load_or_default(AGENT_DIR), mapping)
    for key in expected:
        if key not in actual:
            out.append(f"{mapping['target']} is missing '{key}', which the "
                       f"active profile requires — re-run 'spice profile set'")

    required = mapping.get("requires_command")
    if required and not shutil.which(required):
        out.append(f"Adapter {name} needs '{required}' on PATH; the perimeter "
                   f"hook cannot run without it")

    hook = AGENT_DIR / "hooks" / "guard-paths.js"
    if not hook.exists():
        out.append("Perimeter hook .agent/hooks/guard-paths.js is missing")
    return out


def _components_on_disk() -> set[str]:
    found = set()
    for ctype in COMPONENT_TYPES:
        base = AGENT_DIR / ctype
        if not base.exists():
            continue
        if ctype in DIR_COMPONENTS:
            found |= {f"{ctype}/{d.name}" for d in base.iterdir() if d.is_dir()}
        else:
            found |= {f"{ctype}/{f.stem}" for f in base.glob("*.md")}
    return found


_REFS_RE   = re.compile(r"\*\*Refs:\*\*\s*(.+)", re.IGNORECASE)
_SOURCE_RE = re.compile(r"\(Source:\s*([^)]+)\)", re.IGNORECASE)


def _memory_reference_warnings() -> list[str]:
    """Checks that what memory points at still exists.

    Only structured references are checkable — `**Refs:**` in decisions.md and
    `(Source: ...)` in learned.md. Anything containing a space is treated as
    prose or a command and skipped.
    """
    out = []
    for filename, pattern in (("decisions.md", _REFS_RE), ("learned.md", _SOURCE_RE)):
        path = AGENT_DIR / "memory" / filename
        if not path.exists():
            continue
        in_fence = in_comment = False
        for lineno, line in enumerate(path.read_text(encoding="utf-8",
                                                     errors="replace").splitlines(), 1):
            stripped = line.strip()
            # The templates document the reference format inside fenced blocks
            # and HTML comments; those examples are not real entries.
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if "<!--" in stripped:
                in_comment = "-->" not in stripped
                continue
            if in_comment:
                in_comment = "-->" not in stripped
                continue
            if in_fence:
                continue
            match = pattern.search(line)
            if not match:
                continue
            for ref in (r.strip() for r in match.group(1).split(",")):
                if not ref or " " in ref:
                    continue
                if not _reference_exists(ref):
                    out.append(f"memory/{filename}:{lineno} points at '{ref}', "
                               f"which no longer exists")
    return out


def _reference_exists(ref: str) -> bool:
    if Path(ref).exists() or (AGENT_DIR / ref).exists():
        return True
    ctype, _, name = ref.partition("/")
    if name and ctype in COMPONENT_TYPES:
        return _agent_component_dest(ctype, name).exists()
    return False


# ── onboard ──────────────────────────────────────────────────────────────────

def cmd_onboard(args):
    _require_agent_dir()
    _run_onboarding()


def _run_onboarding():
    print("\n[spice] Interactive onboarding\n")
    print("Press Enter to skip any field.\n")

    # Auto-detect stack from project files
    detected_lang, detected_stack = _detect_stack()
    if detected_lang or detected_stack:
        print(f"[spice] Auto-detected: language={detected_lang or '?'}, stack={detected_stack or '?'}\n")

    name        = _ask("Project name")
    description = _ask("One-line description")
    language    = _ask("Primary language (e.g. csharp, typescript, python)", default=detected_lang)
    stack       = _ask("Stack tags (comma-separated, e.g. dotnet8, angular19, sqlserver)", default=detected_stack)
    env         = _ask("Default environment [dev/staging/prod]", default="dev")

    context_path = AGENT_DIR / "project" / "CONTEXT.md"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    content = _build_context_md(name, description, language, stack, env)
    context_path.write_text(content, encoding="utf-8")
    print(f"\n[spice] project/CONTEXT.md populated.")

    matches = _matching_skills(detect_tags())
    if matches:
        print(f"\n[spice] Skills matching this stack:")
        for skill, fm, matched in matches:
            print(f"  skills/{skill}  (matches: {', '.join(sorted(matched))})")
        print("        Install them with 'spice suggest'.")


# Every tag `_detect_stack` can emit. A skill's `applies_to` must draw from this
# vocabulary or it can never match; free words belong in `keywords` instead.
DETECTABLE_TAGS = frozenset({
    "csharp", "dotnet",
    "typescript", "javascript",
    "angular", "react", "vue", "nextjs", "nuxt", "svelte", "astro",
    "express", "nestjs",
    "python", "django", "fastapi", "flask",
    "rust", "go",
    "dart", "flutter",
    "java", "kotlin", "maven", "gradle",
    "php", "laravel", "symfony",
    "ruby", "rails",
    "swift",
})


def _detect_stack() -> tuple[str, str]:
    languages, stack_tags = _detect_lists()
    return ",".join(languages), ",".join(stack_tags)


def detect_tags() -> set[str]:
    languages, stack_tags = _detect_lists()
    return {t.lower() for t in languages + stack_tags}


def _versioned(tags: list[str], name: str, raw_version: str) -> None:
    """Records both `angular` and `angular19`.

    A skill targeting Angular in general and one targeting a specific major
    both need something to match; emitting only the versioned form meant
    `applies_to: [angular]` never matched anything.
    """
    tags.append(name)
    major = (raw_version or "").lstrip("^~>=< ").split(".")[0]
    if major.isdigit():
        tags.append(f"{name}{major}")


def _detect_lists() -> tuple[list[str], list[str]]:
    """Detect languages and stack tags from files in the current directory."""
    cwd = Path(".")
    languages: list[str] = []
    stack_tags: list[str] = []

    # C# / .NET
    if list(cwd.glob("*.csproj")) or list(cwd.glob("*.sln")) or list(cwd.glob("**/*.csproj")):
        languages.append("csharp")
        stack_tags.append("dotnet")

    # Node / TS / JS
    pkg_json = cwd / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

            if "typescript" in deps or (cwd / "tsconfig.json").exists():
                languages.append("typescript")
            else:
                languages.append("javascript")

            if "@angular/core" in deps:
                _versioned(stack_tags, "angular", deps["@angular/core"])
            if "react" in deps:
                _versioned(stack_tags, "react", deps["react"])
            if "vue" in deps:
                _versioned(stack_tags, "vue", deps["vue"])
            if "next" in deps:
                _versioned(stack_tags, "nextjs", deps["next"])
            if "nuxt" in deps:
                _versioned(stack_tags, "nuxt", deps["nuxt"])
            if "svelte" in deps:
                _versioned(stack_tags, "svelte", deps["svelte"])
            if "astro" in deps:
                _versioned(stack_tags, "astro", deps["astro"])
            if "express" in deps:
                stack_tags.append("express")
            if "@nestjs/core" in deps:
                stack_tags.append("nestjs")
        except (json.JSONDecodeError, OSError):
            pass

    # Python
    if any((cwd / f).exists() for f in ("pyproject.toml", "requirements.txt", "setup.py")):
        languages.append("python")
        req = cwd / "requirements.txt"
        if req.exists():
            content = req.read_text(encoding="utf-8", errors="ignore").lower()
            for framework in ("django", "fastapi", "flask"):
                if framework in content:
                    stack_tags.append(framework)

    if (cwd / "Cargo.toml").exists():
        languages.append("rust")
    if (cwd / "go.mod").exists():
        languages.append("go")

    # Flutter / Dart
    if (cwd / "pubspec.yaml").exists():
        languages.append("dart")
        stack_tags.append("flutter")

    # JVM
    if (cwd / "pom.xml").exists():
        languages.append("java")
        stack_tags.append("maven")
    if (cwd / "build.gradle").exists() or (cwd / "build.gradle.kts").exists():
        if "java" not in languages:
            languages.append("java")
        stack_tags.append("gradle")
    if (cwd / "build.gradle.kts").exists() or list(cwd.glob("**/*.kt")):
        languages.append("kotlin")

    # PHP
    composer = cwd / "composer.json"
    if composer.exists():
        languages.append("php")
        try:
            deps = json.loads(composer.read_text(encoding="utf-8")).get("require", {})
            if any(k.startswith("laravel/") for k in deps):
                stack_tags.append("laravel")
            if any(k.startswith("symfony/") for k in deps):
                stack_tags.append("symfony")
        except (json.JSONDecodeError, OSError):
            pass

    # Ruby
    gemfile = cwd / "Gemfile"
    if gemfile.exists():
        languages.append("ruby")
        if "rails" in gemfile.read_text(encoding="utf-8", errors="ignore").lower():
            stack_tags.append("rails")

    # Swift
    if (cwd / "Package.swift").exists() or list(cwd.glob("*.xcodeproj")):
        languages.append("swift")

    return languages, stack_tags


def _ask(question: str, default: str = "") -> str:
    if default:
        print(f"  {question}")
        print(f"    [Enter for default: {default}]: ", end="", flush=True)
    else:
        print(f"  {question}: ", end="", flush=True)
    answer = input().strip()
    return answer or default


def _build_context_md(name, description, language, stack, env) -> str:
    return f"""# CONTEXT.md — {name or "Unnamed project"}

> Project-specific context. Complements `.agent/RULES.md`.
> Lives in `.agent/project/CONTEXT.md`.

---

## Identity

{description or "TODO: one-line description"}

## Stack

- Primary language: {language or "TODO"}
- Tech tags: {stack or "TODO"}
- Default environment: {env}

## Project-specific rules

<!-- Add rules that apply only to this project. -->

## Role tier overrides

<!-- Override the default tier for specific roles in this project.
Example:
role_tier_overrides:
  qa: heavy
  release: light
-->

## Operational notes

<!-- API keys, non-standard ports, startup commands, etc. -->
"""


# ── run-agent ────────────────────────────────────────────────────────────────

def cmd_run_agent(args):
    _require_agent_dir()

    # Load provider config
    provider = prov.get_provider(args.provider)
    if not provider:
        print(f"[spice] Provider '{args.provider}' not configured.")
        print(f"        Run 'spice providers list' to see configured providers,")
        print(f"        or 'spice providers add {args.provider}' to add it.")
        sys.exit(1)

    # Load role
    role_path = AGENT_DIR / "roles" / f"{args.role}.md"
    if not role_path.exists():
        print(f"[spice] Role not found: {role_path}")
        print(f"        Available roles: {[r['name'] for r in mf.installed_roles(mf.load(AGENT_DIR))]}")
        sys.exit(1)

    role_content = role_path.read_text(encoding="utf-8")

    # Context: inline or from file. --context-file avoids shell-specific
    # command substitution and keeps long handoffs off the command line.
    if getattr(args, "context_file", None):
        ctx_path = Path(args.context_file)
        if not ctx_path.exists():
            print(f"[spice] Context file not found: {ctx_path}")
            sys.exit(1)
        context = ctx_path.read_text(encoding="utf-8")
    else:
        context = args.context

    # Resolve output path
    output_path = Path(args.output) if args.output else _default_run_output(args.role)

    # Build command. The one-shot flag goes first: most CLIs treat it as a mode
    # switch rather than an option of the prompt.
    cmd = [provider["cli"]]
    oneshot = provider.get("oneshot_flag", "").strip()
    if oneshot:
        cmd.append(oneshot)
    cmd += [
        provider["model_flag"], args.model,
        provider["system_flag"], role_content,
        context
    ]

    print(f"[spice] Running role '{args.role}' with {args.provider}/{args.model}...")
    print(f"        Output: {output_path}")
    if not oneshot:
        print(f"        ! No oneshot_flag configured for '{args.provider}'. If"
              f" {provider['cli']} opens an")
        print(f"          interactive session instead of printing, this will time out.")

    timeout = getattr(args, "timeout", None) or 300
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                encoding="utf-8", timeout=timeout)
    except FileNotFoundError:
        print(f"[spice] CLI '{provider['cli']}' not found in PATH.")
        print(f"        Make sure it is installed.")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        # An interactive session with its stdout captured never returns, so
        # without a timeout this hangs silently and forever.
        print(f"[spice] No response after {timeout}s. Killed.")
        print(f"        The usual cause is a missing one-shot flag: the CLI opened")
        print(f"        an interactive session and is waiting for input.")
        print(f"        Set it with 'spice providers add {args.provider}'"
              f" (Claude Code uses -p).")
        sys.exit(1)

    # Write only on success — a failed run used to leave an empty or partial
    # file in runs/, which `reporter` would then consolidate as if it were real.
    if result.returncode != 0:
        print(f"[spice] Agent run failed (exit {result.returncode}):")
        print(result.stderr.strip())
        print("[spice] No output file written.")
        sys.exit(result.returncode)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.stdout, encoding="utf-8")

    print(f"[spice] Done. Read output: {output_path}")
    # Print path to stdout for orchestrator to capture
    print(str(output_path))


def _default_run_output(role: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return AGENT_DIR / "memory" / "runs" / f"{ts}-{role}.md"


# ── providers ────────────────────────────────────────────────────────────────

def cmd_providers(args):
    sub = getattr(args, "prov_command", None)
    if sub == "setup":
        _providers_setup()
    elif sub == "add":
        _providers_add(args.name)
    elif sub == "list":
        _providers_list()
    elif sub == "remove":
        _providers_remove(args.name)
    else:
        print("Usage: spice providers [setup|add <name>|list|remove <name>]")


def _providers_setup():
    print("\n[spice] Provider setup\n")
    print("Configure your first LLM provider (the CLI tool you use).\n")
    name = _ask("Provider name (e.g. anthropic, google, deepseek)")
    if not name:
        print("[spice] Aborted.")
        return
    _providers_add(name)


def _providers_add(name: str):
    print(f"\n[spice] Adding provider: {name}\n")
    cli         = _ask("CLI command (e.g. claude, gemini)")
    model_flag  = _ask("Model flag (e.g. --model, -m)", default="--model")
    system_flag = _ask("System prompt flag (e.g. --append-system-prompt, --system)",
                       default="--append-system-prompt")
    print("  One-shot flag: makes the CLI print an answer and exit instead of")
    print("  opening an interactive session. Without it run-agent times out.")
    oneshot     = _ask("One-shot flag (e.g. -p for Claude Code)", default="-p")

    if not cli:
        print("[spice] CLI command required. Aborted.")
        return

    prov.add_provider(name, cli, model_flag, system_flag, oneshot)
    print(f"\n[spice] Provider '{name}' added.")
    print(f"        Config: {prov.PROVIDERS_FILE}")


def _providers_list():
    data = prov.load()
    providers = data.get("providers", {})
    if not providers:
        print("[spice] No providers configured.")
        print("        Run 'spice providers setup' to configure your first one.")
        return
    default = data.get("default")
    print(f"[spice] Configured providers ({prov.PROVIDERS_FILE}):\n")
    for name, cfg in providers.items():
        marker = " (default)" if name == default else ""
        print(f"  {name}{marker}")
        print(f"    cli:          {cfg['cli']}")
        print(f"    model_flag:   {cfg['model_flag']}")
        print(f"    system_flag:  {cfg['system_flag']}")
        oneshot = cfg.get("oneshot_flag", "")
        print(f"    oneshot_flag: {oneshot if oneshot else '(none — run-agent may hang)'}")
        print()


def _providers_remove(name: str):
    if not prov.remove_provider(name):
        print(f"[spice] Provider '{name}' not found.")
        sys.exit(1)
    print(f"[spice] Provider '{name}' removed.")


# ── helpers ──────────────────────────────────────────────────────────────────

def _require_agent_dir():
    if not AGENT_DIR.exists():
        print("[spice] .agent/ not found in current directory.")
        print("        Run 'spice init' first.")
        sys.exit(1)


def _parse_component_key(component: str) -> tuple[str, str]:
    if "/" in component:
        parts = component.split("/", 1)
        return parts[0], parts[1]
    result = dr.find_component(TOOLKIT_ROOT, component)
    if result is None:
        print(f"[spice] Component not found: '{component}'")
        print("        Specify type: roles/<name>, skills/<name>, etc.")
        sys.exit(1)
    return result


def _toolkit_component_path(ctype: str, name: str) -> Path:
    as_dir = TOOLKIT_ROOT / ctype / name
    if as_dir.exists():
        return as_dir
    as_file = TOOLKIT_ROOT / ctype / f"{name}.md"
    if as_file.exists():
        return as_file
    return as_dir


def _agent_component_dest(ctype: str, name: str) -> Path:
    if ctype in DIR_COMPONENTS:
        return AGENT_DIR / ctype / name
    return AGENT_DIR / ctype / f"{name}.md"


def _infer_type_from_path(src: Path) -> tuple[str, str]:
    name = src.stem if src.is_file() else src.name
    parent = src.parent.name
    if parent in COMPONENT_TYPES:
        return parent, name
    if (src / "SKILL.md").exists():
        return "skills", name
    if (src / "ADAPTER.md").exists():
        return "adapters", name
    print(f"[spice] Could not infer type from '{src}'. Use 'type/name'.")
    sys.exit(1)
