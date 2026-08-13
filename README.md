# spice 🌶️

> *"He who controls the spice controls the universe."* — Frank Herbert, Dune

Agent toolkit for LLM-assisted projects. Installs a system of roles, playbooks,
standards, skills and a security perimeter into any project in 30 seconds.

---

## Installation

### Windows
```cmd
git clone https://github.com/your-user/spice.git
cd spice
install.bat
```

The installer copies files to `%USERPROFILE%\.spice\`, creates a `spice.bat`
launcher, and adds it to your `PATH`. **Open a new terminal** afterwards.

### macOS / Linux
```bash
git clone https://github.com/your-user/spice.git ~/.spice
echo "alias spice='python ~/.spice/bin/spice.py'" >> ~/.zshrc
source ~/.zshrc
```

**Requirements:** Python 3.10+. Git only for `spice self-update`. `node` only if
you install a tool adapter.

Provider configuration lives outside the install directory
(`%APPDATA%\spice\` or `$XDG_CONFIG_HOME/spice/`) so reinstalling never
destroys it. Run `spice path` to see every location.

---

## Quick start

```bash
spice init                      # creates .agent/, CLAUDE.md and GEMINI.md
spice suggest                   # detects your stack, offers matching skills
spice add adapters/claude       # enforces the security profile for Claude Code
spice doctor                    # verifies everything is wired
```

`spice init --yes` does the whole thing without prompting.

---

## Commands

| Command | What it does |
|---|---|
| `spice init [--force] [--no-onboard] [--yes]` | Initialize `.agent/`. `--force` refreshes templates and **keeps** `memory/` and `project/`. |
| `spice add <component> [--from <path>]` | Install a component and its dependencies. |
| `spice remove <component> [--yes]` | Uninstall a component. |
| `spice list [--available]` | List installed components, or everything in the toolkit. |
| `spice search <query>` | Search by name, description, keyword or tag. |
| `spice suggest [--yes]` | Detect the stack and offer matching skills. |
| `spice update [--check] [--refresh-core] [--allow-downgrade]` | Reconcile **this project** with the installed toolkit. |
| `spice self-update [--check]` | Upgrade the **toolkit itself**, machine-wide. |
| `spice doctor` | Verify `.agent/` integrity and the perimeter. |
| `spice path [--open]` | Show which toolkit copy is running and where its data lives. |
| `spice profile <show\|list\|set>` | Inspect or change the security profile. |
| `spice factory-reset [--yes]` | **Delete `.agent/` entirely.** Lists what will be lost first. |
| `spice onboard` | Interactive project onboarding (auto-detects stack). |
| `spice run-agent` | Execute a role with a specific model/provider via subprocess. |
| `spice providers <cmd>` | Manage LLM provider configurations. |

**Component format:** `type/name` (e.g. `roles/qa`, `adapters/claude`).
Without a prefix, `spice add qa` searches skills → adapters → roles → playbooks
→ standards.

### `--force` vs `factory-reset`

`init --force` refreshes toolkit templates and preserves everything you own:
ADRs, learned facts, project state, run history, the component manifest. It
then rebuilds the RULES.md roster so it cannot disagree with what is installed.

`factory-reset` is the destructive one. It enumerates exactly what will be lost
and requires typing `reset` to confirm.

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
├─ RULES.md           # Master entry point — sections between markers are managed
├─ profile.json       # Active security profile (tool-agnostic)
├─ installed.json     # Component manifest
├─ project/           # You write these
│  ├─ CONTEXT.md
│  └─ architecture.md
├─ roles/             # Installed roles
├─ playbooks/         # git, etc.
├─ standards/         # done, handoff, hitl, workflow, orchestration, perimeter
├─ adapters/          # Per-tool enforcement renderers
├─ hooks/             # Scripts adapters install (guard-paths.js)
├─ config/
│  ├─ conventions.md
│  └─ environment.md
├─ skills/            # Installed skills
└─ memory/
   ├─ state.md        # Current state
   ├─ decisions.md    # ADRs
   ├─ learned.md      # Discovered facts
   ├─ plans/          # Plans, when a tool writes them here
   └─ runs/           # Output of `spice run-agent`
```

Component directories appear only once something of that type is installed. A
documentation project with one role and no git playbook is a valid install, and
`doctor` treats it as one.

---

## The security perimeter

Two layers, and both are needed.

`.agent/` addresses the **model**: it is advisory, and a model can read a rule,
agree with it, and still do something else. An adapter addresses the
**program**: permission rules and hooks are evaluated before the model gets a
turn.

`.agent/profile.json` is the source of truth and is tool-agnostic. Adapters are
renderers — delete every adapter and no project knowledge is lost, only
enforcement. Enforcement cannot be shared across tools because each CLI
implements it in its own engine and none reads another's configuration.

### Profiles

| Profile | Shell | Network | Subagents | Reads confined |
|---|---|---|---|---|
| `strict` | ✗ | ✗ | ✗ | ✓ |
| `standard` | ✓ | ✗ | ✓ | ✓ |
| `open` | ✓ | ✓ | ✓ | writes only |

```bash
spice profile list
spice profile set strict     # re-renders every installed adapter
spice profile show           # what is active, and what actually enforces it
```

Writes never leave the project in any profile. Reading and writing files does
not require `capabilities.shell` — those are separate tools, so disabling the
shell removes command execution without affecting normal editing.

### Adapters

`adapters/claude` renders `.claude/settings.json` and installs
`.agent/hooks/guard-paths.js`, a `PreToolUse` guard that denies any path
resolving outside the project. It is written in Node because the tools that run
it are Node applications: one committed file behaves identically on Windows,
macOS and Linux, so a repository cloned on another OS stays protected with no
per-machine setup.

Existing keys in `settings.json` are preserved — an adapter only owns the paths
declared in its `mapping.json`.

### What no profile can contain

Session transcripts are written outside the project by the tool itself and no
project configuration relocates them. Tools with no adapter get the declarative
layer only. Configuration living outside the project, such as global provider
files, is out of reach. `spice doctor` reports whether an adapter is installed
and actually wired — a profile with no adapter is a statement of intent, not a
control.

---

## Roles, phases and generated workflows

Roles declare a `phase`. The workflow list in `RULES.md` is generated from the
roles actually installed, so it can never name one that is not there.

| Phase | Role | Tier | Suggested |
|---|---|---|---|
| `analysis` | `analyst` | heavy | ✗ |
| `design` | `architect` | heavy | ✗ |
| `build` | `implementer` | standard | ✓ |
| `verify` | `qa` | standard | ✓ |
| `security` | `security` | standard | ✗ |
| `document` | `documenter` | light | ✗ |
| `release` | `release` | light | ✓ |
| `on-demand` | `refactor`, `reporter` | — | ✗ |

With the suggested profile a Major change renders as
`(wait for approval) → implementer → qa → release`. Install `analyst` and
`architect` and it becomes
`analyst → architect → (wait for approval) → implementer → qa → release`.

The approval gate belongs to the classification, not to the roles: it is there
whether or not an analyst is installed.

---

## Skills and stack matching

`spice suggest` detects the stack and offers skills that target it.

- **`applies_to`** must draw from the detectable tag vocabulary, or it can never
  match anything.
- **`keywords`** holds free words, used by `spice search`.
- **`category`** is `stack | meta | quality`.
- **`min_toolkit_version`** is enforced at install time.

Detection emits both the generic and the versioned form (`angular` and
`angular19`), so a skill can target a framework broadly or one major version.

**Detectable tags:** `csharp` `dotnet` `typescript` `javascript` `angular`
`react` `vue` `nextjs` `nuxt` `svelte` `astro` `express` `nestjs` `python`
`django` `fastapi` `flask` `rust` `go` `dart` `flutter` `java` `kotlin` `maven`
`gradle` `php` `laravel` `symfony` `ruby` `rails` `swift`

---

## Available components

### Playbooks
| Name | Suggested | Description |
|---|---|---|
| `git` | ✓ | Git conventions for commits, branches, PRs, and tags. |

### Standards
| Name | Suggested | Description |
|---|---|---|
| `done` | ✓ | Definition of Done — checklist for closing a change. |
| `handoff` | ✓ | Role-to-role delivery formats (YAML handoffs). |
| `hitl` | ✓ | Human-In-The-Loop action classification. |
| `orchestration` | ✓ | Multi-role workflow orchestration with tier self-assessment. |
| `perimeter` | ✓ | What the agent may read, write and execute. |
| `workflow` | ✓ | Edit protocol — old/new mandatory before modifying any file. |

### Adapters
| Name | Renders | Description |
|---|---|---|
| `claude` | `.claude/settings.json` | Enforces the profile for Claude Code. |

### Skills
| Name | Category | Description |
|---|---|---|
| `token-counter` | meta | Count tokens to estimate cost and manage context. Estimates without dependencies; measures if `tiktoken` is installed. |
| `csharp-rest-api` | stack | C# .NET 8 REST APIs — Clean Architecture, JWT, EF Core. |

---

## Multi-role workflows with `spice run-agent`

When a workflow needs a model the current CLI is not running, the orchestrator
invokes:

```bash
spice run-agent --role qa --model sonnet --provider anthropic \
                --context-file handoff.yaml
```

Use `--context-file`, not `--context "$(cat handoff.yaml)"`: command
substitution is bash-only and inlining a long handoff can exceed the
command-line length limit on Windows.

Output is written to `.agent/memory/runs/<timestamp>-<role>.md` and the path
printed to stdout — but only on success, so a failed run leaves no partial file
for `reporter` to consolidate.

Note this requires `capabilities.shell`, so it is unavailable under the
`strict` profile.

---

## Tiers, not models

Roles declare `tier: light | standard | heavy` and never mention concrete model
names. The orchestrator self-assesses and picks a model per tier from what is
available. Roles survive provider changes, model renames and new releases
without edits.

---

## Adding a new component

1. Create the file in the corresponding toolkit directory.
2. Include YAML frontmatter with the required fields:

**Roles:**
```yaml
name: my-role
version: 1.0.0
tier: light | standard | heavy
phase: analysis | design | build | verify | security | document | release | on-demand
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
applies_to: [csharp, dotnet]      # detectable tags only
keywords: [free, words, for, search]
scripts: [scripts/my-script.py]
depends_on: []
min_toolkit_version: 1.0.0
```

**Adapters** (folder with `ADAPTER.md` and `mapping.json`):
```yaml
name: my-tool
version: 1.0.0
description: Renders the active profile into my-tool's configuration.
target: My Tool
renders: .mytool/config.json
```

**Playbooks / Standards:**
```yaml
name: my-standard
version: 1.0.0
description: What it defines.
```

3. Add `suggested: true` if it belongs in the minimal profile — the flag lives
   in the component's own frontmatter and nowhere else.
4. Bump the version so `spice update` propagates the change.
5. Run `spice update --refresh-core` in existing projects if you changed `core/`.

Inline lists (`[a, b]`) and dashed lists are both parsed.

---

## Philosophy

- **SSOT strict**: each file has one purpose and one author.
- **Enforcement outside the prompt**: rules the model cannot argue with live in
  adapters, not in Markdown.
- **Explicit loading**: skills are loaded declaratively, not auto-triggered.
- **No external dependencies**: the CLI uses only the Python standard library,
  and a skill degrades rather than refusing to run when an optional one is
  missing.
- **Minimal tokens**: the model loads only what the current task needs.
- **HITL by default**: destructive actions require human approval — including
  spice's own.
- **Report, do not improvise**: an agent that hits a contradiction says so
  instead of resolving it quietly.
- **CLI-agnostic**: `.agent/` works with any LLM CLI through root entry points;
  adapters add enforcement per tool.
