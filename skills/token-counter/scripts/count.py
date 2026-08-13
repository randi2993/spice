#!/usr/bin/env python3
"""
count.py — Count tokens of files or stdin.
Uses cl100k_base (tiktoken) as approximation for Claude/GPT-4.

Requires: pip install tiktoken
"""
import sys
import argparse
from pathlib import Path

try:
    import tiktoken
except ImportError:
    print("Error: tiktoken not installed.")
    print("Install with: pip install tiktoken")
    sys.exit(1)

ENCODING = "cl100k_base"


def count_tokens(text: str) -> int:
    enc = tiktoken.get_encoding(ENCODING)
    return len(enc.encode(text))


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
    print(f"tokens: {format_number(tokens)}  (encoding: {ENCODING})")
    print(f"chars:  {format_number(chars)}")
    print(f"lines:  {format_number(lines)}")
    return tokens


def process_stdin() -> None:
    text = sys.stdin.read()
    tokens = count_tokens(text)
    print(f"tokens: {format_number(tokens)}  (encoding: {ENCODING})")


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

    if processed > 1:
        # The file count is not decoration. `**` is recursive in zsh and in
        # Python, but NOT in bash unless globstar is enabled, so the same
        # command can count a different set of files on each platform. Printing
        # what was actually counted makes that visible instead of silent.
        print(f"-- {format_number(processed)} file(s), "
              f"TOTAL: {format_number(total)} tokens")


if __name__ == "__main__":
    main()
