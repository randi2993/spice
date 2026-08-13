---
name: claude
version: 1.0.0
description: Renders the active profile into Claude Code's settings.json.
target: Claude Code
renders: .claude/settings.json
depends_on: []
---

# Claude Code adapter

Translates `.agent/profile.json` into `.claude/settings.json`.

## Why this exists as a separate file

`.agent/RULES.md` addresses the **model**. It is advisory: the model can read
it, agree with it, and still do something else. Everything in this adapter
addresses the **program**, and is applied before the model gets a turn.

That is why the enforcing layer cannot be shared across tools the way `.agent/`
is. Gemini CLI cannot read Claude Code's settings, and vice versa. `.agent/` is
the specification; adapters are thin connectors that translate it. Delete this
adapter and no project knowledge is lost — only the enforcement for one tool.

## What it produces

- `.claude/settings.json` at the project root, merged with anything already
  there. Keys this adapter does not own are preserved untouched.
- `.agent/hooks/guard-paths.js`, copied from this adapter's own `hooks/`
  directory and registered as a `PreToolUse` hook.

The guard lives under this adapter rather than in a shared directory because
it speaks Claude Code's hook protocol: it reads `tool_input.file_path` from the
stdin payload and answers with `hookSpecificOutput.permissionDecision`. Another
tool's adapter ships its own guard, reusing the path-resolution approach but
speaking that tool's schema.

## Keys it owns

Anything under `base` or `when` in `mapping.json`. Everything else in an
existing `settings.json` is left alone.

## Requirements

`node` on PATH. Claude Code is a Node application, so this is normally already
true — but a bundled runtime that is not exposed on PATH would break the hook
silently. `spice doctor` checks it.
