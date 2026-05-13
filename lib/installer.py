"""
installer.py — Command implementations.
"""
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import manifest as mf
import rules_editor as re_mod
import dep_resolver as dr
import providers as prov

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR    = Path(".agent")

SUGGESTED_PROFILE = [
    ("roles",     "implementer"),
    ("roles",     "qa"),
    ("roles",     "release"),
    ("playbooks", "git"),
    ("standards", "done"),
    ("standards", "handoff"),
    ("standards", "hitl"),
    ("standards", "orchestration"),
    ("standards", "workflow"),
]


# ── init ────────────────────────────────────────────────────────────────────

def cmd_init(args):
    if AGENT_DIR.exists() and not args.force:
        print("[spice] .agent/ already exists in this directory.")
        print("        Use --force to overwrite.")
        sys.exit(1)

    print("[spice] Initializing .agent/ ...")
    _copy_core()
    _create_root_entrypoints()
    _init_manifest()

    # Install suggested profile
    print("\n[spice] Install suggested minimal profile? [Y/n]: ", end="", flush=True)
    answer = input().strip().lower()
    if answer in ("", "y", "yes"):
        manifest = mf.load(AGENT_DIR)
        for ctype, name in SUGGESTED_PROFILE:
            _install_single(ctype, name, manifest, quiet=False)
        mf.save(AGENT_DIR, manifest)
        print("\n[spice] Minimal profile installed.")
    else:
        print("[spice] Profile skipped. Use 'spice add <component>' when ready.")

    # Onboarding
    if not getattr(args, "no_onboard", False):
        print("\n[spice] Run interactive onboarding now? [Y/n]: ", end="", flush=True)
        answer = input().strip().lower()
        if answer in ("", "y", "yes"):
            _run_onboarding()

    print("\n[spice] Done. Open Claude Code (or your CLI of choice) in this project.")


def _copy_core():
    core_src = TOOLKIT_ROOT / "core"
    if AGENT_DIR.exists():
        shutil.rmtree(AGENT_DIR)
    shutil.copytree(core_src, AGENT_DIR)


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
                print(f"    → directive injected into RULES.md")
    elif ctype == "roles":
        description = fm.get("description", "")
        tier_str = tier or "standard"
        triggers = fm.get("triggers", [])
        if isinstance(triggers, str):
            triggers = [triggers]
        re_mod.inject_role(rules_path, name, version, tier_str, description, triggers)
        if not quiet:
            trig_info = f", {len(triggers)} triggers" if triggers else ""
            print(f"    → role registered in RULES.md (tier: {tier_str}{trig_info})")

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

    mf.remove_record(manifest, ctype, name)
    mf.save(AGENT_DIR, manifest)
    print(f"[spice] Removed {ctype}/{name}.")


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
    for ctype in ("roles", "playbooks", "standards", "skills"):
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

    for ctype in ("roles", "playbooks", "standards", "skills"):
        components = _discover_components(ctype)
        if not components:
            continue
        print(f"  {ctype.upper()}")
        for name, fm in components:
            marker = "[✓]" if f"{ctype}/{name}" in installed_keys else "[ ]"
            version = fm.get("version", "?")
            tier = fm.get("tier")
            tier_str = f"  (tier: {tier})" if tier else ""
            desc = fm.get("description", "")
            desc_str = f" — {desc}" if desc else ""
            print(f"    {marker} {name:<22} v{version}{tier_str}{desc_str}")
        print()

    print("Install with: spice add <type>/<name>   (e.g. spice add roles/documenter)")


def cmd_search(args):
    query = args.query.lower()
    print(f"[spice] Searching for '{query}'...\n")

    installed_keys = set()
    if AGENT_DIR.exists():
        manifest = mf.load(AGENT_DIR)
        installed_keys = set(manifest.get("components", {}).keys())

    found = False
    for ctype in ("roles", "playbooks", "standards", "skills"):
        components = _discover_components(ctype)
        matches = []
        for name, fm in components:
            desc = (fm.get("description") or "").lower()
            if query in name.lower() or query in desc:
                matches.append((name, fm))
        if not matches:
            continue
        found = True
        print(f"  {ctype.upper()}")
        for name, fm in matches:
            marker = "[✓]" if f"{ctype}/{name}" in installed_keys else "[ ]"
            version = fm.get("version", "?")
            tier = fm.get("tier")
            tier_str = f"  (tier: {tier})" if tier else ""
            desc = fm.get("description", "")
            desc_str = f" — {desc}" if desc else ""
            print(f"    {marker} {name:<22} v{version}{tier_str}{desc_str}")
        print()

    if not found:
        print("  No components found matching that query.")


def _discover_components(ctype: str) -> list[tuple[str, dict]]:
    """List all components of a given type in the toolkit with their frontmatter."""
    base = TOOLKIT_ROOT / ctype
    if not base.exists():
        return []
    result = []
    if ctype == "skills":
        # Skills are folders with SKILL.md
        for d in sorted(base.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                fm = dr.get_frontmatter(d / "SKILL.md")
                result.append((d.name, fm))
    else:
        # roles, playbooks, standards are .md files
        for f in sorted(base.glob("*.md")):
            fm = dr.get_frontmatter(f)
            result.append((f.stem, fm))
    return result


# ── update ───────────────────────────────────────────────────────────────────

def cmd_update(args):
    _require_agent_dir()
    print(f"[spice] Updating toolkit from {TOOLKIT_ROOT} ...")
    result = subprocess.run(["git", "pull", "--ff-only"], cwd=TOOLKIT_ROOT,
                            capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[spice] git pull failed:\n{result.stderr}")
        sys.exit(1)
    print(result.stdout.strip())

    if args.check:
        print("[spice] --check mode: no changes applied.")
        return

    manifest = mf.load(AGENT_DIR)
    components = list(manifest.get("components", {}).values())
    updated = 0
    for entry in components:
        ctype, name = entry["type"], entry["name"]
        src = _toolkit_component_path(ctype, name)
        if not src.exists():
            continue
        new_ver = dr.get_frontmatter(src).get("version", "0.0.0")
        if new_ver != entry["version"]:
            print(f"  {ctype}/{name}: v{entry['version']} → v{new_ver}")
            _install_single(ctype, name, manifest, quiet=True)
            updated += 1
    mf.save(AGENT_DIR, manifest)
    print(f"[spice] {updated} component(s) updated." if updated else "[spice] Up to date.")


# ── doctor ───────────────────────────────────────────────────────────────────

def cmd_doctor(args):
    _require_agent_dir()
    errors = []
    warnings = []

    # 1. Core files
    required = [
        "RULES.md",
        "installed.json",
        "project/CONTEXT.md",
        "project/architecture.md",
    ]
    for fname in required:
        if not (AGENT_DIR / fname).exists():
            errors.append(f"Missing core file: .agent/{fname}")

    required_dirs = ["config", "memory", "roles", "playbooks", "standards", "project"]
    for sub in required_dirs:
        if not (AGENT_DIR / sub).exists():
            errors.append(f"Missing directory: .agent/{sub}/")

    # 2. RULES.md markers
    rules_path = AGENT_DIR / "RULES.md"
    if rules_path.exists():
        ok, errs = re_mod.validate_markers(rules_path)
        for e in errs:
            errors.append(f"RULES.md: {e}")

    # 3. Manifest vs disk
    manifest = mf.load(AGENT_DIR)
    for key, entry in manifest.get("components", {}).items():
        ctype, name = entry["type"], entry["name"]
        dest = _agent_component_dest(ctype, name)
        if not dest.exists():
            errors.append(f"Component in manifest but not on disk: {key}")
            continue
        # Version match check
        fm = dr.get_frontmatter(dest)
        disk_ver = fm.get("version", "0.0.0")
        if disk_ver != entry["version"]:
            warnings.append(f"Version mismatch for {key}: manifest={entry['version']}, disk={disk_ver}")
        # Role tier check
        if ctype == "roles":
            if "tier" not in fm:
                warnings.append(f"Role {name} has no 'tier' in frontmatter")
            elif fm["tier"] not in ("light", "standard", "heavy"):
                errors.append(f"Role {name}: invalid tier '{fm['tier']}'. Must be light|standard|heavy")

    # 4. Root entry points
    for fname in ("CLAUDE.md", "GEMINI.md"):
        if not Path(fname).exists():
            warnings.append(f"Missing root entry point: {fname}")

    # Report
    if not errors and not warnings:
        print("[spice] All checks passed.")
        return
    if errors:
        print("[spice] ERRORS:")
        for e in errors:
            print(f"  ✗ {e}")
    if warnings:
        print("[spice] WARNINGS:")
        for w in warnings:
            print(f"  ! {w}")
    if errors:
        sys.exit(1)


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


def _detect_stack() -> tuple[str, str]:
    """Detect language and stack from project files in current directory."""
    cwd = Path(".")
    languages = []
    stack_tags = []

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

            # Detect TS vs JS
            if "typescript" in deps or (cwd / "tsconfig.json").exists():
                languages.append("typescript")
            else:
                languages.append("javascript")

            # Detect frameworks
            if "@angular/core" in deps:
                ver = deps.get("@angular/core", "").lstrip("^~").split(".")[0]
                stack_tags.append(f"angular{ver}" if ver.isdigit() else "angular")
            if "react" in deps:
                stack_tags.append("react")
            if "vue" in deps:
                stack_tags.append("vue")
            if "next" in deps:
                stack_tags.append("nextjs")
            if "express" in deps:
                stack_tags.append("express")
            if "@nestjs/core" in deps:
                stack_tags.append("nestjs")
        except Exception:
            pass

    # Python
    if (cwd / "pyproject.toml").exists() or (cwd / "requirements.txt").exists() or (cwd / "setup.py").exists():
        languages.append("python")
        # Try detecting framework
        req = cwd / "requirements.txt"
        if req.exists():
            content = req.read_text(encoding="utf-8", errors="ignore").lower()
            if "django" in content:
                stack_tags.append("django")
            if "fastapi" in content:
                stack_tags.append("fastapi")
            if "flask" in content:
                stack_tags.append("flask")

    # Rust
    if (cwd / "Cargo.toml").exists():
        languages.append("rust")

    # Go
    if (cwd / "go.mod").exists():
        languages.append("go")

    # Flutter / Dart
    if (cwd / "pubspec.yaml").exists():
        languages.append("dart")
        stack_tags.append("flutter")

    # Java
    if (cwd / "pom.xml").exists():
        languages.append("java")
        stack_tags.append("maven")
    if (cwd / "build.gradle").exists() or (cwd / "build.gradle.kts").exists():
        if "java" not in languages:
            languages.append("java")
        stack_tags.append("gradle")

    # DB hints
    if any(cwd.glob("**/*.sql")) or "sqlserver" in str(cwd.glob("**/appsettings*.json")).lower():
        # heuristic — only add if clearly present
        pass

    return ",".join(languages), ",".join(stack_tags)


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

    # Resolve output path
    output_path = Path(args.output) if args.output else _default_run_output(args.role)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build command
    cmd = [
        provider["cli"],
        provider["model_flag"], args.model,
        provider["system_flag"], role_content,
        args.context
    ]

    print(f"[spice] Running role '{args.role}' with {args.provider}/{args.model}...")
    print(f"        Output: {output_path}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        print(f"[spice] CLI '{provider['cli']}' not found in PATH.")
        print(f"        Make sure it is installed.")
        sys.exit(1)

    output_path.write_text(result.stdout, encoding="utf-8")

    if result.returncode != 0:
        print(f"[spice] Agent run failed (exit {result.returncode}):")
        print(result.stderr)
        sys.exit(result.returncode)

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

    if not cli:
        print("[spice] CLI command required. Aborted.")
        return

    prov.add_provider(name, cli, model_flag, system_flag)
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
        print(f"    cli:         {cfg['cli']}")
        print(f"    model_flag:  {cfg['model_flag']}")
        print(f"    system_flag: {cfg['system_flag']}")
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
    if ctype == "skills":
        return AGENT_DIR / ctype / name
    return AGENT_DIR / ctype / f"{name}.md"


def _infer_type_from_path(src: Path) -> tuple[str, str]:
    name = src.stem if src.is_file() else src.name
    parent = src.parent.name
    if parent in ("roles", "playbooks", "standards", "skills"):
        return parent, name
    if (src / "SKILL.md").exists():
        return "skills", name
    print(f"[spice] Could not infer type from '{src}'. Use 'type/name'.")
    sys.exit(1)
