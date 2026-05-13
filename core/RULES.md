# RULES.md

> Entry point for any LLM working in this project.
> Managed in part by spice. Sections between `SPICE:*:START/END` markers must not be edited manually.

---

## 🛑 EXECUTION PROTOCOL — NON-NEGOTIABLE

You MUST follow this protocol on EVERY user request. No exceptions.

### Step A — Announce classification (in plain text to user)

Before reading any project file beyond this one, output:

```
Classification: <Trivial | Minor | Major | Structural>
Reason: <1-line justification>
```

Rules for classification:
- **Trivial**: typo, visual constant, formatting. ONE file, ONE small change.
- **Minor**: one file, one function, no public API change.
- **Major**: multiple files OR new functionality OR new component OR new route.
- **Structural**: new architecture, major dependency, public API change.

If the request mentions: "add a component", "new feature", "new route", "create X" + touches multiple files → it is **Major minimum**. Do NOT downgrade to Minor.

### Step B — Announce role plan (in plain text to user)

Based on classification, list the roles you will invoke:

```
Workflow plan:
  1. <role> — <what it will produce>
  2. <role> — ...
```

Workflow per classification:
- **Trivial** → Release only.
- **Minor** → Implementer → QA → Release.
- **Major** → Analyst → Architect → (wait for approval) → Implementer → QA + Security → Documenter → Release.
- **Structural** → Same as Major + explicit approval at EACH phase.

### Step C — Wait for approval (Major / Structural only)

Output:
```
Approve plan? [yes / modify / cancel]
```

**STOP.** Do not proceed until the user replies. For Trivial/Minor, state the plan and proceed without waiting.

---

### During execution — for EACH role in your plan:

1. **ANNOUNCE**: Output exactly:
   ```
   ── Adopting role: <name> ──
   Reading .agent/roles/<name>.md
   ```

2. **STATE IDENTITY**: Quote the role's identity line from its `.md`.

3. **EXECUTE** the role's Actions in the order declared in its file.

4. **PRODUCE OUTPUT** in the format declared by the role.

5. **WRITE HANDOFF** for the next role per `.agent/standards/handoff.md`.

6. **WRITE RUN FILE**: Save the role's output to `.agent/memory/runs/<timestamp>-<role>.md`.

7. Only THEN proceed to the next role in the plan.

---

### 🚫 FORBIDDEN

- ❌ Editing files before Step B is announced
- ❌ Skipping the role announcement (the "── Adopting role ──" line)
- ❌ Declaring a task "done" without having executed ALL roles in the plan
- ❌ Writing to `state.md` as a role you never announced
- ❌ Combining multiple roles into one mega-step without announcing each
- ❌ Saying "I'll act as Implementer" while actually doing QA's job

### Violation handling

If you realize mid-task that you violated the protocol:
1. STOP immediately.
2. Tell the user: "I violated the execution protocol by [what]. Restarting from Step A."
3. Go back to Step A.

---

## What you are

You are an LLM agent working on this project under a system of declared roles, standards, and skills. `.agent/project/CONTEXT.md` complements this file with project-specific context. It does NOT replace these instructions; if you find a real conflict, escalate to the user.

---

## Role selection (for direct requests, not workflows)

Some requests do NOT trigger a full workflow — they are direct queries answered by a single role. Examples:
- "Give me a report of recent changes" → documenter only
- "Validate the tests" → qa only
- "Audit security" → security only

For these, you still follow the EXECUTION PROTOCOL above but with a simplified plan:

```
Classification: Direct query
Workflow plan:
  1. <role> — <output>
```

Then proceed.

### Intent routing — match user message against triggers

Scan the user message against the **Triggers** declared for each installed role (see SPICE:ROLES section below).

- **Exactly one role matches** → adopt it.
- **Multiple roles match with similar confidence** → STOP and ASK:
  > "Multiple roles match this request:
  > - <role-a>: <description>
  > - <role-b>: <description>
  >
  > Or run them combined (reporter consolidates outputs).
  > Which do you prefer?"
- **No role matches** → ask the user which role applies before doing anything.

If the request contains generic words like "report", "reporte", "tests", "pruebas" that appear in multiple triggers, ALWAYS ask the user. Do not guess.

---

## Read when relevant to the current task

- `.agent/standards/workflow.md` — when modifying files (the old/new edit protocol)
- `.agent/standards/orchestration.md` — when running multi-role workflows in parallel
- `.agent/standards/hitl.md` — when an action might be destructive
- `.agent/standards/done.md` — when closing a change
- `.agent/standards/handoff.md` — when passing work to another role
- `.agent/playbooks/git.md` — when committing, branching, tagging
- `.agent/project/architecture.md` — for major or structural changes
- `.agent/memory/decisions.md` — to avoid contradicting past ADRs

---

## State updates

At the end of every session, the active role updates `.agent/memory/state.md`:
- What was done
- Current state
- Next concrete steps

Sign the entry with the role that closed the session. ONLY sign as a role you actually announced via "── Adopting role ──".

---

## Installed roles

<!-- SPICE:ROLES:START -->
<!-- managed by spice. do not edit manually. -->
<!-- SPICE:ROLES:END -->

## Installed skills

<!-- SPICE:SKILLS:START -->
<!-- managed by spice. do not edit manually. -->
<!-- SPICE:SKILLS:END -->
