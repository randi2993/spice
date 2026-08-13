# learned.md — Discovered facts

> Facts the agent discovered and you confirmed.
> **Different from decisions.md**: observed facts, not chosen decisions.

---

Format — the `(Source: ...)` is required, not decorative:

```
- [YYYY-MM-DD] Fact discovered. (Source: path/to/file.ts)
```

`spice doctor` verifies every source path still exists and warns when one is
gone. Facts go stale as the code moves; this is what makes that visible
instead of leaving the agent to act on something that no longer exists.

Use a path with no spaces for anything checkable. A source containing spaces
is treated as a command or prose and is not verified.

<!-- The agent adds entries below. -->
