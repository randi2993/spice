---
name: orchestration
version: 1.2.0
description: Multi-role workflow orchestration with tier self-assessment.
suggested: true
---

# orchestration.md — Multi-role workflow orchestration

> Read this BEFORE running any workflow that requires more than one role.
> The orchestrator (the model in the current chat) follows this protocol.

---

## Self-assessment

Before orchestrating a multi-role workflow, assess your own reasoning capacity.

You are a **light-tier** model if you are designed for:
- Simple, fast tasks
- Cost-optimized responses
- Mechanical operations (translation, classification, short summaries)

You are a **standard-tier** model if you are designed for:
- Most coding tasks
- Reasonable reasoning depth
- Balance of cost and capability

You are a **heavy-tier** model if you are designed for:
- Complex reasoning
- Architectural decisions
- Tasks where mistakes are expensive

**If you are light-tier, do NOT orchestrate multi-role workflows.** Tell the user:

> "I'm a light-tier model. For multi-role workflows I need you to switch to a heavier model, or I can execute a single role at a time. What would you like to do?"

If the user insists (`force`, `proceed`), continue under their responsibility.

---

## Building the execution plan

When the workflow is Major or Structural, build an explicit execution plan and show it to the user BEFORE running anything.

For each role to invoke, determine its tier:
1. Look at the role's frontmatter `tier` (in `.agent/roles/<role>.md`).
2. Check `.agent/project/CONTEXT.md` for `role_tier_overrides` that may change it for this project.

Present the plan like this:

```
Execution plan:
  1. <role>     — tier: <tier>     [sequential]
  2. <role>     — tier: <tier>     [sequential]
  3. <role>     — tier: <tier>     [parallel with 4]
  4. <role>     — tier: <tier>     [parallel with 3]

Current model tier: <self-assessed tier>
Highest required tier: <max>

Options:
  [a] You switch the chat to a heavier model and I proceed
  [b] I delegate each step via `spice run-agent` (subprocess)
      -- only when the active profile allows shell; see below
  [c] I attempt all steps with the current model (may be insufficient for heavy roles)
  [d] Cancel

Your choice?
```

Wait for the user's choice. Do not assume.

---

## Executing via `spice run-agent`

**Check the profile first.** `spice run-agent` launches a subprocess, so it
needs `capabilities.shell`. Under a profile that denies the shell — `strict`
does — option [b] is unavailable: do not offer it, and say so if the user asks
for it. Run `spice profile show` if unsure.

When the user picks option [b], for each step in the plan:

```bash
spice run-agent \
  --role <role-name> \
  --model <model-for-the-target-tier> \
  --provider <provider-name> \
  --context "<handoff YAML from previous step>"
```

The provider and model come from the user's configured providers (`spice providers list`). If the user hasn't configured providers, ask them to run `spice providers setup` first.

For parallel steps, invoke `spice run-agent` for each in the background and wait for all to complete before proceeding.

---

## Context preparation

Do NOT pass the full chat history as `--context`. The target role only needs:

1. The handoff YAML from the previous role (per `standards/handoff.md`).
2. References to files it needs to read (paths, not contents).
3. The specific task or question for this step.

The target role reads files itself from `.agent/` and the project. Smaller context = better performance from any tier.

---

## Output collection

`spice run-agent` writes output to `.agent/memory/runs/<timestamp>-<role>.md` and prints the path to stdout. Read that file before proceeding to the next step.

---

## When to skip orchestration entirely

For Trivial or Minor changes, the orchestrator handles everything in-session. No need to invoke `spice run-agent` or build a multi-step plan. See change levels in `RULES.md`.
