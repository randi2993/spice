# decisions.md — Architecture Decision Records

> Important architectural decisions and why they were made.
> The Architect consults this before validating plans to avoid contradicting past decisions.

---

## ADR format

```
### ADR-NNN: [Title]
**Date:** YYYY-MM-DD
**Status:** active | superseded-by ADR-NNN
**Refs:** path/to/file.ts, .agent/roles/security.md
**Context:** Why the decision was needed.
**Decision:** What was decided.
**Consequences:** Implications, trade-offs.
```

**Refs** lists the files or components the decision depends on, comma
separated and without spaces inside each entry. `spice doctor` checks that
each one still exists and warns when it does not — that is how a decision
pointing at something deleted becomes visible instead of silently misleading
the next reader. Entries containing spaces are treated as prose and skipped.

**Never delete a stale ADR.** Mark it `superseded-by` and write the new one.
The reasoning stays valuable long after the decision is reversed.

---

<!-- Add ADRs below. -->
