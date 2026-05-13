# spice 🌶️

> *"He who controls the spice controls the universe."* — Frank Herbert, Dune

Agent toolkit for LLM-assisted projects. Installs a system of roles, playbooks, standards, and skills into any project in 30 seconds.

---

## Installation

### Windows
```cmd
git clone https://github.com/your-user/spice.git
cd spice
install.bat
```

The installer copies files to `%USERPROFILE%\.spice\`, creates a `spice.bat` launcher, and adds it to your `PATH`. **Open a new terminal** after installation.

### macOS / Linux
```bash
git clone https://github.com/your-user/spice.git ~/.spice
echo "alias spice='python ~/.spice/bin/spice.py'" >> ~/.zshrc
source ~/.zshrc
```

**Requirements:** Python 3.10+, Git.

---

## Quick start

```bash
# 1. In your project directory:
spice init
# → Creates .agent/ with core files, CLAUDE.md and GEMINI.md at the project root.
# → Offers a suggested minimal profile and interactive onboarding.
# → Auto-detects your stack (C#, Angular, Python, Go, Rust, etc.)

# 2. (Optional) Configure your LLM provider for run-agent:
spice providers setup
# → Sets up CLI command, model flag, and system prompt flag for your provider.

# 3. Install components as needed:
spice add skills/csharp-rest-api

# 4. Open your CLI of choice (Claude Code, Gemini CLI, etc.)
```

---

## Commands

| Command | What it does |
|---|---|
| `spice init [--force] [--no-onboard]` | Initialize `.agent/` with core files + `CLAUDE.md`/`GEMINI.md` at project root. Offers minimal profile + onboarding. |
| `spice add <component> [--from <path>]` | Install a component and its dependencies. `--from` installs from a local path outside the toolkit. |
| `spice remove <component> [--yes]` | Uninstall a component. |
| `spice list [--available]` | List installed components. `--available` (or `--all`) shows all components in the toolkit. |
| `spice search <query>` | Search components by name or description. |
| `spice update [--check]` | Sync with latest toolkit version. |
| `spice doctor` | Verify `.agent/` integrity. |
| `spice onboard` | Run interactive project onboarding (auto-detects stack). |
| `spice run-agent` | Execute a role with a specific model/provider via subprocess. |
| `spice providers <cmd>` | Manage LLM provider configurations (`setup`, `add`, `list`, `remove`). |

**Component format:** `type/name` (e.g. `roles/qa`, `skills/csharp-rest-api`)
**Without prefix:** `spice add qa` searches skills → roles → playbooks → standards.

---

## What `spice init` creates

At the **project root**:
```
CLAUDE.md             # Entry point for Claude Code → reads .agent/RULES.md
GEMINI.md             # Entry point for Gemini CLI → reads .agent/RULES.md
```

Inside `.agent/`:
```
.agent/
├─ RULES.md           # Master entry point — managed by spice (sections between markers)
├─ project/           # Project-specific files — you write these
│  ├─ CONTEXT.md
│  └─ architecture.md
├─ installed.json     # Component manifest
├─ roles/             # Installed roles
├─ playbooks/         # git, etc.
├─ standards/         # done, handoff, hitl, workflow, orchestration
├─ config/
│  ├─ conventions.md
│  └─ environment.md
├─ skills/            # Installed skills
└─ memory/
   ├─ state.md        # Current state — agent updates it
   ├─ decisions.md    # ADRs
   ├─ learned.md      # Discovered facts
   └─ runs/           # Output of `spice run-agent` (created on first use)
```

---

## Available components

### Roles

| Name | Tier | Suggested | Description |
|---|---|---|---|
| `analyst` | heavy | ✗ | First contact with the request; classifies change and produces initial plan. |
| `architect` | heavy | ✗ | Validates plans against architecture.md; does not write code. |
| `implementer` | standard | ✓ | Executes the approved plan; halts and consults on anything outside scope. |
| `qa` | standard | ✓ | Validates quality and Definition of Done; does not write new code. |
| `release` | light | ✓ | Prepares commits, PRs, and tags following git playbook. |
| `security` | standard | ✗ | Reviews security risks in the diff; does not write new code. |
| `documenter` | light | ✗ | Keeps documentation up to date with only what changed. |
| `refactor` | standard | ✗ | Detects technical debt and proposes cleanup; only on explicit demand. |
| `reporter` | light | ✗ | Consolidates outputs from multiple roles into a single executive report. |

### Playbooks

| Name | Suggested | Description |
|---|---|---|
| `git` | ✓ | Git conventions for commits, branches, PRs, and tags. |

### Standards

| Name | Suggested | Description |
|---|---|---|
| `done` | ✓ | Definition of Done — checklist for closing a change. |
| `handoff` | ✓ | Role-to-role delivery formats (YAML handoffs). |
| `hitl` | ✓ | Human-In-The-Loop action classification (destructive / safe / read-only). |
| `orchestration` | ✓ | Multi-role workflow orchestration with tier self-assessment. |
| `workflow` | ✓ | Edit protocol — old/new mandatory before modifying any file. |

### Skills

| Name | Suggested | Description |
|---|---|---|
| `token-counter` | ✗ | Count tokens of files or text to estimate cost and manage LLM context. |
| `csharp-rest-api` | ✗ | Best practices for C# .NET 8 REST APIs — Clean Architecture, JWT, EF Core. |

> **Suggested** components are offered during `spice init` as a minimal profile.
> Install any component with `spice add <type>/<name>` (e.g. `spice add roles/analyst`).

---

## Multi-role workflows with `spice run-agent`

When a workflow requires multiple roles in parallel, or a model switch the current CLI doesn't support, the orchestrator (the model in your current chat) invokes:

```bash
spice run-agent \
  --role qa \
  --model sonnet \
  --provider anthropic \
  --context "<handoff YAML from previous step>" \
  --output .agent/memory/runs/20260513-qa.md
```

Output is written to the file, path printed to stdout for the orchestrator to read.

Configure providers once per machine with `spice providers setup`.

---

## Tiers, not models

Roles declare `tier: light | standard | heavy` in their frontmatter. They never mention concrete model names. The orchestrator self-assesses and decides which concrete model to use per tier, based on what's available in the current environment.

This means roles survive provider changes, model renames, and new model releases without edits.

---

## Adding a new component

1. Create the file in the corresponding toolkit directory (`roles/`, `skills/`, etc.).
2. Include YAML frontmatter with the required fields per type:

**Roles:**
```yaml
name: my-role
version: 1.0.0
tier: light | standard | heavy
description: One-line description.
triggers:
  - "keyword that activates this role"
```

**Skills** (folder with `SKILL.md`):
```yaml
name: my-skill
version: 1.0.0
description: What the skill does.
shared_directive: Instruction injected into RULES.md when installed.
category: stack | meta | quality
applies_to: [tag1, tag2]
scripts: [scripts/my-script.py]
depends_on: []
min_toolkit_version: 1.0.0
```

**Playbooks / Standards:**
```yaml
name: my-standard
version: 1.0.0
description: What it defines.
```

3. Run `spice update` in existing projects to propagate it.

---

## Philosophy

- **SSOT strict**: each file has one purpose and one author.
- **Explicit loading**: skills are loaded declaratively, not auto-triggered.
- **No external dependencies**: the CLI uses only Python stdlib.
- **Minimal tokens**: the model loads only what's needed for the current task.
- **HITL by default**: destructive actions require human approval.
- **Auto-detection**: `onboard` auto-detects your stack (C#/.NET, Angular, React, Vue, Next.js, Express, NestJS, Python/Django/FastAPI/Flask, Rust, Go, Flutter/Dart, Java/Maven/Gradle) to pre-fill project context.
- **CLI-agnostic**: works with any LLM CLI (Claude Code, Gemini CLI, etc.) via root entry points (`CLAUDE.md`, `GEMINI.md`).
