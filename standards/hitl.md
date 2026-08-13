---
name: hitl
version: 1.1.0
description: Human-In-The-Loop action classification (destructive / safe / read-only).
suggested: true
---

# hitl.md — Human-In-The-Loop

> Actions that require human confirmation before execution.
> **First line of defense:** the client (Claude Code, etc.) controls which tools are enabled.
> **Second line:** these pattern rules.
> **Last resort:** the prompt itself.

---

## Action classification (assisted development)

### 🔴 Destructive — ALWAYS require approval
- `git push --force` or `git reset --hard`
- `git rebase` on shared branches
- Deleting files or folders
- Truncating or deleting DB data
- Production changes (deploys, prod migrations)
- Installing or removing project dependencies
- Modifying CI/CD configuration files

### 🟡 Safe — propose, wait for confirmation before executing
- Creating new branches
- Making commits (show message first)
- Modifying files outside the approved plan scope
- Changes to `architecture.md` or `RULES.md`
- Running migration scripts in staging

### 🟢 Read-only — execute without asking
- Reading files
- `git status`, `git log`, `git diff`
- Running tests
- Listing dependencies
- Static analysis (SonarQube, gitleaks)

---

## Escalation rule

If an action doesn't clearly fit any category:
1. Classify as 🔴 Destructive.
2. Describe the action and ask for confirmation.
3. Don't execute until you receive explicit approval.

---

## For projects with runtime agents (HITL-runtime)

If the project is an application that executes real actions (e.g. a bot controlling the system), the action classification lives in the project's code, not here. Reference the source:

```
# HITL-runtime
# Action classification lives in: [path/to/classifier.ts]
# This file doesn't enumerate actions — references the code as SSOT.
```

This avoids drift between the .md and the real code.
