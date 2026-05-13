---
name: git
version: 1.0.0
description: Git conventions for commits, branches, PRs, and tags.
---

# git.md — Git Conventions

> Rules for commits, branches, PRs, and tags. The Release role applies them.

---

## Commits — Conventional Commits

Format: `<type>(<scope optional>): <imperative description>`

| Type | When |
|---|---|
| `feat` | New functionality |
| `fix` | Bug fix |
| `refactor` | Code change without behavior change |
| `test` | Add or fix tests |
| `docs` | Documentation only |
| `chore` | Build, deps, configs (no logic impact) |
| `perf` | Performance improvement |
| `ci` | CI/CD changes |

**Examples:**
```
feat(auth): add JWT refresh token endpoint
fix(users): prevent duplicate email on registration
docs: update API setup guide
chore: bump dotnet to 8.0.5
```

**Rules:**
- Description in English, imperative, no trailing period.
- No capital letter (`add`, not `Add`).
- Max 72 chars in first line.
- Optional body: explain "why", not "what".

---

## Branches

| Prefix | When |
|---|---|
| `feature/` | New functionality |
| `fix/` | Bug fix |
| `hotfix/` | Urgent prod fix |
| `refactor/` | Refactor without new functionality |
| `chore/` | Maintenance tasks |

**Naming:** kebab-case, descriptive. e.g. `feature/weapon-transfer-endpoint`

**Rules:**
- `main`: always stable, deployable.
- `develop`: integration. Merges to main for releases.
- No direct work on `main`.
- Delete branches after merge.

---

## PRs / Merge Requests

- Title in Conventional Commit format.
- Description: what changes, why, how to test.
- At least QA PASS before merging to develop/staging.
- QA + Security PASS before merging to main/prod.
- Don't merge with failing tests.
- Squash merge for features, merge commit for releases.

---

## Tags

- SemVer format: `v1.2.3`
- Only the Release role creates tags.
- Signed tags for official releases: `git tag -s v1.2.3`
- `MAJOR`: breaking public API change.
- `MINOR`: backward-compatible new functionality.
- `PATCH`: backward-compatible fix.

---

## Forbidden

- `git push --force` or `--force-with-lease` on shared branches (classified 🔴 Destructive in `standards/hitl.md`).
- Direct commits to `main`.
- Secrets in commits (even temporarily).
