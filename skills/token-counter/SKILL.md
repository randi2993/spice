---
name: token-counter
version: 1.0.0
description: Count tokens of files or text to estimate cost and manage LLM context
shared_directive: To count tokens of a file, run `python .agent/skills/token-counter/scripts/count.py <file>`.
category: meta
applies_to: [tokens, context, cost-estimation]
scripts: [scripts/count.py]
depends_on: []
min_toolkit_version: 1.0.0
---

# token-counter

Counts tokens using the `tiktoken` library (approximate same tokenization as GPT/Claude).

## Usage

```bash
# Count tokens of a file
python .agent/skills/token-counter/scripts/count.py src/API/Controllers/WeaponsController.cs

# Count tokens of direct text
echo "text to count" | python .agent/skills/token-counter/scripts/count.py -

# Count multiple files
python .agent/skills/token-counter/scripts/count.py src/**/*.cs
```

## Output

```
file:   src/API/Controllers/WeaponsController.cs
tokens: 1,247
model:  cl100k_base (approx. Claude/GPT-4)
```

## When to use

- Before pasting a large file into context: verify it doesn't exceed the limit.
- To estimate the cost of a long session.
- To decide whether to fragment a file before processing.

## Precision note

Exact tokenization varies between models. `cl100k_base` is a good approximation for Claude and GPT-4. Count may differ ±5% from real.

## Requires

```bash
pip install tiktoken
```
