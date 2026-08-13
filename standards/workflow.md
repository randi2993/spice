---
name: workflow
version: 1.1.0
description: Edit protocol — old/new mandatory before modifying any file.
suggested: true
---

# workflow.md — Edit protocol

> Operational rules for modifying files. Different from `RULES.md` (which is high-level flow).
> The Implementer role applies this on every edit.

---

## Step 1 — Before editing any file

Show old/new and wait for approval:

```
## Change proposal: [file name]

**File:** `path/to/file.ts`

**OLD:**
```[language]
// current relevant code
```

**NEW:**
```[language]
// proposed code
```

**Reason:** [why this change]

Approve? [Y/n]
```

Do not edit until you receive confirmation.

---

## Step 2 — After editing

Identify what documentation becomes outdated by the change:
- Did any public API change? → update README / docs
- Did behavior documented in `architecture.md` change? → update
- Was an architectural decision made? → register in `memory/decisions.md`

Show old/new of affected docs and wait for approval before updating them.

---

## Step 3 — When closing the session

Update `memory/state.md` with:
- What was done
- Current state
- Concrete next steps

---

## Additional rules

- **Do not edit** files outside the approved plan scope without consulting.
- **No force push** ever (it's in `standards/hitl.md` as destructive).
- **No secrets in repo** — always from `.env` or env vars.
- If a file to edit wasn't in the plan: halt, notify, wait for confirmation that it's in scope.
