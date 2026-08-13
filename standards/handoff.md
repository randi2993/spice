---
name: handoff
version: 1.1.0
description: Role-to-role delivery formats (YAML handoffs).
---

# handoff.md — Role-to-role delivery formats

> Delivery protocol between roles. Without a fixed format, each role delivers however it wants and the next gets confused.
> Allows switching models (Claude → Gemini) without losing context.

---

## Analyst → Architect

```yaml
handoff:
  from: analyst
  to: architect
  change_level: trivial | minor | major | structural
  summary: "One-line description"
  scope:
    files_to_modify:
      - path/to/file.ts
    files_to_read:
      - path/to/related.ts
  risks:
    - "Identified risk"
  tests_required:
    - "Scenario to cover"
  open_questions:
    - "Unresolved question (if any)"
  suggested_tier: light | standard | heavy
```

---

## Architect → Implementer

```yaml
handoff:
  from: architect
  to: implementer
  architecture_validation: PASS | FAIL
  validation_notes: "Architect notes (if FAIL: what to change)"
  approved_plan:
    files_to_modify:
      - file: path/to/file.ts
        reason: "Why it's touched"
        changes: "What to change"
    constraints:
      - "Constraint that cannot be broken"
  tests_required:
    - "Required test scenario"
```

---

## Implementer → QA

```yaml
handoff:
  from: implementer
  to: qa
  summary: "What was implemented"
  files_changed:
    - path/to/changed_file.ts
  tests_added:
    - path/to/test_file.spec.ts
  known_gaps:
    - "Uncovered case (if any)"
  notes: "Additional context for QA"
```

---

## QA → Release

```yaml
handoff:
  from: qa
  to: release
  status: PASS | FAIL | WARN
  tests_run:
    - "test name"
  gaps_found:
    - "Gap found (if WARN)"
  security_review_required: true | false
  notes: "Context for Release"
```

---

## Use with `spice run-agent`

Write the handoff to a file and pass it with `--context-file`:

```
spice run-agent --role qa --model sonnet --provider anthropic --context-file handoff.yaml
```

Use `--context-file`, not `--context "$(cat handoff.yaml)"`. Command substitution
is bash-only — it does not work in cmd.exe or PowerShell — and inlining a long
handoff can exceed the command-line length limit on Windows.

For a short, one-line task, `--context "..."` is still fine.

The target agent reads the YAML, treats it as its inputs, and produces its own handoff to the next role.
