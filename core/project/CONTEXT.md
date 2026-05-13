# CONTEXT.md — [Project name]

> Project-specific context. Complements `.agent/RULES.md`.
> Lives in `.agent/project/CONTEXT.md`.

---

## Identity

<!-- One or two lines: what it is, what it solves, primary stack. -->
TODO: describe the project here.

---

## Stack

- Primary language: TODO
- Tech tags: TODO
- Default environment: dev

---

## Project-specific rules

<!-- Rules that apply only to this project, beyond what's in RULES.md. -->

<!-- Example for an agent-runtime project:
- HITL action classifier lives in `src/executor.ts:classifyAction` (SSOT).
- Default model for chat sessions: Sonnet.
-->

---

## Role tier overrides

<!-- Override the default tier for specific roles in this project.
Example:
role_tier_overrides:
  qa: heavy        # this project needs heavy QA
  release: light   # release is mechanical here
-->

---

## Operational notes

<!-- API keys location, non-standard ports, startup commands, etc. -->
