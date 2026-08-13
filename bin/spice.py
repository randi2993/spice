#!/usr/bin/env python3
"""
spice — agent toolkit CLI
"He who controls the spice controls the universe." — Dune
"""
import sys
import argparse
from pathlib import Path

# Add lib/ to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

from installer import (
    cmd_init, cmd_add, cmd_remove, cmd_list, cmd_update, cmd_doctor,
    cmd_onboard, cmd_run_agent, cmd_providers, cmd_search, cmd_path,
    cmd_factory_reset, cmd_profile, cmd_suggest, cmd_self_update
)

MIN_PYTHON = (3, 10)
if sys.version_info < MIN_PYTHON:
    sys.exit(f"spice requires Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+. You have {sys.version}")

# The CLI prints arrows, em dashes and box characters. On a Windows console
# using a legacy code page — and on ANY platform when stdout is redirected to
# a pipe or a file — those raise UnicodeEncodeError and abort the command
# mid-run. `spice init` died at the profile step for exactly this reason.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # pragma: no cover - very old consoles
        pass


HELP_BANNER = """spice — agent toolkit
"He who controls the spice controls the universe." — Dune
"""

EPILOG = """
examples:
  spice init --yes                     Initialize without any prompts
  spice add roles/documenter           Install a component (type/name)
  spice update --check                 See what would change, apply nothing

  spice run-agent --role qa --model sonnet --provider anthropic \\
                  --context-file handoff.yaml
"""


def _cmd(sub, name, summary, **kwargs):
    """Registers a subcommand. `summary` feeds both the listing and its own -h."""
    return sub.add_parser(name, help=summary, description=summary, **kwargs)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="spice",
        description=HELP_BANNER,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # init
    p_init = _cmd(sub, "init", "Initialize .agent/ in current project")
    p_init.add_argument("--force", action="store_true",
                        help="Refresh templates, keeping memory/ and project/")
    p_init.add_argument("--no-onboard", action="store_true", help="Skip interactive onboarding")
    p_init.add_argument("--yes", "-y", action="store_true",
                        help="Accept the suggested profile and skip all prompts")

    # add
    p_add = _cmd(sub, "add", "Install a component")
    p_add.add_argument("component", help="e.g. roles/qa, skills/csharp-rest-api")
    p_add.add_argument("--from", dest="from_path", help="Local path outside the toolkit")

    # remove
    p_remove = _cmd(sub, "remove", "Uninstall a component")
    p_remove.add_argument("component", help="e.g. roles/security")
    p_remove.add_argument("--yes", action="store_true", help="Skip confirmation")

    # list
    p_list = _cmd(sub, "list", "List components")
    p_list.add_argument("--available", action="store_true",
                        help="Show all components in the toolkit (installed and not)")
    p_list.add_argument("--all", action="store_true",
                        help="Same as --available")

    # search
    p_search = _cmd(sub, "search", "Search components by name, description or keyword")
    p_search.add_argument("query", help="Keyword to search")

    # suggest
    p_suggest = _cmd(sub, "suggest", "Detect the stack and offer matching skills")
    p_suggest.add_argument("--yes", "-y", action="store_true",
                           help="Install every match without asking")

    # update
    p_update = _cmd(sub, "update", "Reconcile this project with the installed toolkit")
    p_update.add_argument("--check", action="store_true", help="Show diff only, don't apply")
    p_update.add_argument("--allow-downgrade", action="store_true",
                          help="Apply components whose toolkit version is older than installed")
    p_update.add_argument("--refresh-core", action="store_true",
                          help="Also refresh core templates (keeps memory/ and project/)")

    # self-update
    p_self = _cmd(sub, "self-update", "Upgrade the toolkit itself (machine-wide)")
    p_self.add_argument("--check", action="store_true",
                        help="Show what would be pulled, apply nothing")

    # doctor
    _cmd(sub, "doctor", "Verify .agent/ integrity")

    # path
    p_path = _cmd(sub, "path", "Show where spice and its data live")
    p_path.add_argument("--open", action="store_true",
                        help="Open the toolkit directory in the file manager")

    # profile
    p_profile = _cmd(sub, "profile", "Show or change the security profile")
    profile_sub = p_profile.add_subparsers(dest="profile_command", metavar="<subcommand>")
    profile_sub.add_parser("show", help="Show the active profile and what enforces it")
    profile_sub.add_parser("list", help="List available profiles")
    p_profile_set = profile_sub.add_parser("set", help="Change profile and re-render adapters")
    p_profile_set.add_argument("name", help="Profile name (e.g. strict, standard, open)")

    # factory-reset
    p_reset = _cmd(sub, "factory-reset", "Delete .agent/ entirely and start over")
    p_reset.add_argument("--yes", action="store_true", help="Skip the typed confirmation")

    # onboard
    _cmd(sub, "onboard", "Run interactive project onboarding")

    # run-agent
    p_run = _cmd(sub, "run-agent", "Execute a role with given model/provider")
    p_run.add_argument("--role",     required=True, help="Role to execute (e.g. qa)")
    p_run.add_argument("--model",    required=True, help="Model name (e.g. sonnet, gemini-pro)")
    p_run.add_argument("--provider", required=True, help="Provider name from providers.json")
    p_run_ctx = p_run.add_mutually_exclusive_group(required=True)
    p_run_ctx.add_argument("--context", help="Context/task description")
    p_run_ctx.add_argument("--context-file",
                           help="Read context from a file (shell-agnostic; use for long handoffs)")
    p_run.add_argument("--output",   help="Path to write output (default: .agent/memory/runs/<ts>-<role>.md)")

    # providers
    p_prov = _cmd(
        sub, "providers", "Manage LLM provider configurations",
        epilog="examples:\n  spice providers setup\n  spice providers add anthropic\n  spice providers list\n\nConfig location: run 'spice path'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    prov_sub = p_prov.add_subparsers(dest="prov_command", metavar="<subcommand>")
    prov_sub.add_parser("setup",  help="Interactive setup of first provider")
    p_prov_add = prov_sub.add_parser("add", help="Add a new provider (interactive)")
    p_prov_add.add_argument("name", help="Provider name (e.g. anthropic, google)")
    prov_sub.add_parser("list", help="List configured providers")
    p_prov_rm = prov_sub.add_parser("remove", help="Remove a provider")
    p_prov_rm.add_argument("name")

    # The command listing is rendered from the parser itself, so a new flag is
    # visible in `spice -h` the moment it is declared. The hand-written epilog
    # used to be the only place flags appeared, and it had drifted: --force,
    # --no-onboard, --from, --yes, --check and --output were undiscoverable.
    parser.format_help = lambda: _render_help(parser, sub)  # type: ignore[method-assign]
    return parser


def _optional_flags(subparser) -> list[str]:
    """Longest form of each non-required flag, minus --help."""
    flags = []
    for action in subparser._actions:
        if not action.option_strings or action.required:
            continue
        if "-h" in action.option_strings:
            continue
        flags.append(max(action.option_strings, key=len))
    return flags


def _render_help(parser, sub) -> str:
    rows = [(name, (p.description or "").strip(), _optional_flags(p))
            for name, p in sub.choices.items()]
    name_w = max(len(n) for n, _, _ in rows) + 2
    desc_w = max(len(d) for _, d, _ in rows) + 2

    lines = [parser.format_usage().rstrip(), "", HELP_BANNER.rstrip(), "", "commands:"]
    for name, desc, flags in rows:
        suffix = " ".join(f"[{f}]" for f in flags)
        lines.append(f"  {name.ljust(name_w)}{desc.ljust(desc_w) if suffix else desc}{suffix}".rstrip())

    lines += ["", "options:"]
    for action in parser._actions:
        if action.option_strings:
            lines.append(f"  {', '.join(action.option_strings).ljust(name_w)}{action.help or ''}")

    lines += ["", "Run 'spice <command> -h' for the full options of a command.",
              EPILOG.rstrip(), ""]
    return "\n".join(lines)


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "init":          lambda: cmd_init(args),
        "add":           lambda: cmd_add(args),
        "remove":        lambda: cmd_remove(args),
        "list":          lambda: cmd_list(args),
        "search":        lambda: cmd_search(args),
        "suggest":       lambda: cmd_suggest(args),
        "update":        lambda: cmd_update(args),
        "self-update":   lambda: cmd_self_update(args),
        "doctor":        lambda: cmd_doctor(args),
        "path":          lambda: cmd_path(args),
        "profile":       lambda: cmd_profile(args),
        "factory-reset": lambda: cmd_factory_reset(args),
        "onboard":       lambda: cmd_onboard(args),
        "run-agent":     lambda: cmd_run_agent(args),
        "providers":     lambda: cmd_providers(args),
    }

    try:
        dispatch[args.command]()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
    except Exception as e:
        print(f"[spice] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
