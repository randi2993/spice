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
    cmd_onboard, cmd_run_agent, cmd_providers, cmd_search
)

MIN_PYTHON = (3, 10)
if sys.version_info < MIN_PYTHON:
    sys.exit(f"spice requires Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+. You have {sys.version}")


HELP_BANNER = """spice — agent toolkit
"He who controls the spice controls the universe." — Dune
"""

EPILOG = """
examples:
  spice init                           Initialize .agent/ + onboarding
  spice list                           List installed components
  spice list --available               List ALL components in toolkit
  spice search documenter              Search components by keyword
  spice add roles/documenter           Install the documenter role
  spice add skills/csharp-rest-api     Install a skill
  spice remove roles/refactor          Uninstall a component
  spice doctor                         Verify .agent/ integrity
  spice onboard                        Re-run interactive onboarding
  spice update                         Sync with latest toolkit version

  spice providers setup                Configure first LLM provider
  spice providers add anthropic        Add provider (interactive)
  spice providers list                 List configured providers
  spice providers remove anthropic     Remove provider

  spice run-agent --role qa --model sonnet --provider anthropic \\
                  --context "Validate the latest changes"
"""


def build_parser():
    parser = argparse.ArgumentParser(
        prog="spice",
        description=HELP_BANNER,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # init
    p_init = sub.add_parser("init", help="Initialize .agent/ in current project")
    p_init.add_argument("--force", action="store_true", help="Overwrite if .agent/ exists")
    p_init.add_argument("--no-onboard", action="store_true", help="Skip interactive onboarding")

    # add
    p_add = sub.add_parser("add", help="Install a component")
    p_add.add_argument("component", help="e.g. roles/qa, skills/csharp-rest-api")
    p_add.add_argument("--from", dest="from_path", help="Local path outside the toolkit")

    # remove
    p_remove = sub.add_parser("remove", help="Uninstall a component")
    p_remove.add_argument("component", help="e.g. roles/security")
    p_remove.add_argument("--yes", action="store_true", help="Skip confirmation")

    # list
    p_list = sub.add_parser("list", help="List components")
    p_list.add_argument("--available", action="store_true",
                        help="Show all components in the toolkit (installed and not)")
    p_list.add_argument("--all", action="store_true",
                        help="Same as --available")

    # search
    p_search = sub.add_parser("search", help="Search components by name or description")
    p_search.add_argument("query", help="Keyword to search")

    # update
    p_update = sub.add_parser("update", help="Sync with latest toolkit version")
    p_update.add_argument("--check", action="store_true", help="Show diff only, don't apply")
    p_update.add_argument("--allow-downgrade", action="store_true",
                          help="Apply components whose toolkit version is older than installed")

    # doctor
    sub.add_parser("doctor", help="Verify .agent/ integrity")

    # onboard
    sub.add_parser("onboard", help="Run interactive project onboarding")

    # run-agent
    p_run = sub.add_parser("run-agent", help="Execute a role with given model/provider")
    p_run.add_argument("--role",     required=True, help="Role to execute (e.g. qa)")
    p_run.add_argument("--model",    required=True, help="Model name (e.g. sonnet, gemini-pro)")
    p_run.add_argument("--provider", required=True, help="Provider name from providers.json")
    p_run_ctx = p_run.add_mutually_exclusive_group(required=True)
    p_run_ctx.add_argument("--context", help="Context/task description")
    p_run_ctx.add_argument("--context-file",
                           help="Read context from a file (shell-agnostic; use for long handoffs)")
    p_run.add_argument("--output",   help="Path to write output (default: .agent/memory/runs/<ts>-<role>.md)")

    # providers
    p_prov = sub.add_parser(
        "providers",
        help="Manage LLM provider configurations",
        description="Manage LLM provider configurations (~/.spice/providers.json)",
        epilog="examples:\n  spice providers setup\n  spice providers add anthropic\n  spice providers list",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    prov_sub = p_prov.add_subparsers(dest="prov_command", metavar="<subcommand>")
    prov_sub.add_parser("setup",  help="Interactive setup of first provider")
    p_prov_add = prov_sub.add_parser("add", help="Add a new provider (interactive)")
    p_prov_add.add_argument("name", help="Provider name (e.g. anthropic, google)")
    prov_sub.add_parser("list", help="List configured providers")
    p_prov_rm = prov_sub.add_parser("remove", help="Remove a provider")
    p_prov_rm.add_argument("name")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        print(HELP_BANNER)
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "init":      lambda: cmd_init(args),
        "add":       lambda: cmd_add(args),
        "remove":    lambda: cmd_remove(args),
        "list":      lambda: cmd_list(args),
        "search":    lambda: cmd_search(args),
        "update":    lambda: cmd_update(args),
        "doctor":    lambda: cmd_doctor(args),
        "onboard":   lambda: cmd_onboard(args),
        "run-agent": lambda: cmd_run_agent(args),
        "providers": lambda: cmd_providers(args),
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
