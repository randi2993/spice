#!/usr/bin/env python3
"""
count.py — Count tokens of files or stdin.

Two modes. With `tiktoken` installed it measures with cl100k_base; without it,
it estimates from the text itself and says so. Refusing to run without an
optional dependency made the whole skill unusable for anyone who had not
installed it, for questions a rough number answers perfectly well.

Optional: pip install tiktoken
"""
import re
import sys
import argparse
from pathlib import Path

try:
    import tiktoken
    ENCODING = "cl100k_base"
    MODE = f"measured, {ENCODING}"
    EXACT = True
except ImportError:
    tiktoken = None
    MODE = "estimated, no tiktoken installed"
    EXACT = False

# Word-ish runs and single symbols. Punctuation is almost always its own token,
# which is why code produces more tokens per character than prose does.
_PIECES = re.compile(r"\w+|[^\w\s]")


def count_tokens(text: str) -> int:
    if tiktoken is not None:
        return len(tiktoken.get_encoding(ENCODING).encode(text))
    return _estimate_tokens(text)


def _estimate_tokens(text: str) -> int:
    """Approximates BPE: a short word is one token, a long one splits, and each
    symbol counts on its own. Whitespace is absorbed into the adjacent token, so
    it is not counted separately.

    Expect roughly +/-15%. That is enough to decide whether a file fits in a
    context window or should be split, which is what this skill is for. Install
    tiktoken when the exact number matters.
    """
    return sum(max(1, round(len(piece) / 5)) for piece in _PIECES.findall(text))


def format_number(n: int) -> str:
    return f"{n:,}"


def process_file(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        return 0
    tokens = count_tokens(text)
    chars = len(text)
    lines = text.count("\n") + 1
    print(f"file:   {path}")
    print(f"tokens: {_prefix()}{format_number(tokens)}  ({MODE})")
    print(f"chars:  {format_number(chars)}")
    print(f"lines:  {format_number(lines)}")
    return tokens


def _prefix() -> str:
    """The tilde is the point: it must be impossible to mistake an estimate
    for a measurement."""
    return "" if EXACT else "~"


def process_stdin() -> None:
    text = sys.stdin.read()
    print(f"tokens: {_prefix()}{format_number(count_tokens(text))}  ({MODE})")


def main():
    parser = argparse.ArgumentParser(description="Count tokens of files or stdin.")
    parser.add_argument("files", nargs="*", help="Files to count. Use '-' for stdin.")
    args = parser.parse_args()

    if not args.files or args.files == ["-"]:
        process_stdin()
        return

    total = 0
    processed = 0
    for pattern in args.files:
        if pattern == "-":
            process_stdin()
            continue

        # Decide by existence, not by looking for a '*': in bash the shell has
        # already expanded the pattern, so the argument arrives as a plain
        # filename and there is no wildcard left to detect.
        target = Path(pattern)
        paths = [target] if target.is_file() else sorted(Path(".").glob(pattern))
        matched = [p for p in paths if p.is_file()]

        if not matched:
            print(f"no match: {pattern}", file=sys.stderr)
            continue

        for path in matched:
            if processed:
                print()
            total += process_file(path)
            processed += 1

    if args.files and args.files != ["-"] and processed == 0:
        # Nothing matched at all: fail loudly so a script cannot mistake an
        # empty run for a zero-token result.
        sys.exit(1)

    if processed > 1:
        # The file count is not decoration. `**` is recursive in zsh and in
        # Python, but NOT in bash unless globstar is enabled, so the same
        # command can count a different set of files on each platform. Printing
        # what was actually counted makes that visible instead of silent.
        print(f"-- {format_number(processed)} file(s), "
              f"TOTAL: {_prefix()}{format_number(total)} tokens ({MODE})")


if __name__ == "__main__":
    main()
