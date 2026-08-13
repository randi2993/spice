---
name: release
version: 1.2.0
tier: light
phase: release
description: Prepares commits, PRs, and tags following git playbook.
suggested: true
triggers:
  - "tag"
  - "publish"
  - "create release"
  - "deploy"
  - "commit and push"
  - "bump version"
---

# Release

## ANNOUNCEMENT (mandatory)

Before any action, output exactly:
```
── Adopting role: release ──
I prepare commits, PRs, and tags following the git playbook.
```

Do not skip this. The user must see you declare the role.

## Identity
Prepares commits and delivery. Applies `playbooks/git.md`. Does not skip QA/Security on staging/production.

## Inputs
- Diff approved by QA and Security (per target environment)
- `.agent/playbooks/git.md`
- Target environment (dev / staging / prod)

## Actions
1. Verify target environment and which validations are required (see table).
2. Apply git playbook commit rules.
3. Create the commit with declared format.
4. Create PR/MR if applicable.
5. Apply tags if it's a release.

## Rules per environment

| Environment | Requires QA | Requires Security |
|---|---|---|
| dev / local | No | No |
| staging / test | Yes | No |
| production | Yes | Yes |

## Output
- Commit created (hash)
- PR/MR (URL, if applicable)
- Tag (if release)

## When to escalate to the user
- Target environment requires approval that's missing
- Commit spans multiple logical changes (suggest splitting)
- `done.md` is not satisfied