---
name: done
version: 1.0.0
description: Definition of Done — checklist for closing a change.
---

# done.md — Definition of Done

> A change is "done" when it meets ALL applicable items in this list.
> The QA role verifies this point by point.

---

## Code

- [ ] Compiles without new errors or warnings
- [ ] Existing tests pass (without modifying tests just to make them pass)
- [ ] Edge cases of the change have test coverage
- [ ] No commented-out code or debug prints
- [ ] No hardcoded secrets (keys, passwords, tokens)
- [ ] `.env` is in `.gitignore`

## Quality

- [ ] No obvious duplication of existing code
- [ ] Public functions/methods documented (docstring, JSDoc, XML docs)
- [ ] Descriptive names — no cryptic abbreviations
- [ ] If applicable: `quality-scanner-*` skill reports no critical findings

## Architecture

- [ ] Respects layers defined in `architecture.md`
- [ ] No new dependencies without justification
- [ ] No breaking changes to existing public API contracts (or break is intentional and documented)

## System state

- [ ] `memory/state.md` updated with what was done and next steps
- [ ] If change affects `architecture.md`: updated
- [ ] If change is an architectural decision: registered in `memory/decisions.md`

## Release (staging/prod only)

- [ ] CHANGELOG updated
- [ ] Version bumped if applicable
- [ ] QA: PASS
- [ ] Security: PASS (prod only)
