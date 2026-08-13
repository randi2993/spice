---
name: token-counter
version: 1.3.0
description: Count tokens of files or text to estimate cost and manage LLM context
shared_directive: To count tokens of a file, run `python .agent/skills/token-counter/scripts/count.py <file>`.
category: meta
applies_to: []
keywords: [tokens, context, cost-estimation]
scripts: [scripts/count.py]
depends_on: []
min_toolkit_version: 1.0.0
---

# token-counter

Counts tokens in two modes:

- **Measured** when `tiktoken` is installed, using `cl100k_base`.
- **Estimated** otherwise, from the text itself, with no dependencies.

Estimated output is always prefixed with `~` and labelled, so an estimate can
never be mistaken for a measurement.

## Usage

```bash
# Count tokens of a file
python .agent/skills/token-counter/scripts/count.py src/API/Controllers/WeaponsController.cs

# Count tokens of direct text
echo "text to count" | python .agent/skills/token-counter/scripts/count.py -

# Count multiple files — QUOTE the pattern
python .agent/skills/token-counter/scripts/count.py 'src/**/*.cs'
```

Quote the pattern. Unquoted, bash expands it first and `**` is NOT recursive
there unless `globstar` is on, while zsh and Python do recurse — the same
command then counts a different set of files on each platform. Quoted, Python
always expands it and the result is identical everywhere. The output states
how many files were counted so a mismatch is visible.

## Output

```
file:   src/API/Controllers/WeaponsController.cs
tokens: ~1,247  (estimated, no tiktoken installed)
chars:  4,912
lines:  118

-- 3 file(s), TOTAL: ~4,812 tokens (estimated, no tiktoken installed)
```

A pattern that matches nothing prints `no match: <pattern>` on stderr, and the
command exits non-zero if nothing matched at all — an empty run must not look
like a zero-token result.

## When to use

- Before pasting a large file into context: verify it doesn't exceed the limit.
- To estimate the cost of a long session.
- To decide whether to fragment a file before processing.

## Precision

Estimated mode is within roughly ±15%, measured against known `cl100k_base`
counts: exact on prose, +10% on code, and it under-counts very long single
words. It errs high on code, which is the safe direction — you would rather
believe a file is too big for the context window than discover it is.

That is enough for what this skill is for: deciding whether a file fits, or
whether to split it. Nothing here needs three significant figures.

`cl100k_base` is GPT-4's tokenizer. It is a reasonable proxy for Claude but not
its actual tokenizer, so measured mode is exact for GPT models and still an
approximation for Claude.

## Optional

```bash
pip install tiktoken   # switches to measured mode
```
