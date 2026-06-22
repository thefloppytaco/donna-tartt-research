#!/usr/bin/env python3
"""
Validate ISBN-10 and ISBN-13 check digits.

Usage:
    python3 isbn_check.py 0679410325
    python3 isbn_check.py 9780679410324
    python3 isbn_check.py --batch path/to/list.txt   # one ISBN per line
"""
import sys
import re


def isbn10_valid(s: str) -> bool:
    s = re.sub(r"[^0-9Xx]", "", s)
    if len(s) != 10:
        return False
    total = 0
    for i, ch in enumerate(s):
        if ch in "Xx":
            v = 10
        else:
            v = int(ch)
        total += v * (10 - i)
    return total % 11 == 0


def isbn13_valid(s: str) -> bool:
    s = re.sub(r"[^0-9]", "", s)
    if len(s) != 13:
        return False
    total = 0
    for i, ch in enumerate(s):
        v = int(ch)
        total += v if i % 2 == 0 else v * 3
    return total % 10 == 0


def check(s: str) -> str:
    bare = re.sub(r"[^0-9Xx]", "", s)
    if len(bare) == 10:
        ok = isbn10_valid(bare)
        return f"ISBN-10 {bare}: {'VALID' if ok else 'INVALID'}"
    if len(bare) == 13:
        ok = isbn13_valid(bare)
        return f"ISBN-13 {bare}: {'VALID' if ok else 'INVALID'}"
    return f"Cannot determine ISBN type for {s!r} (length {len(bare)})"


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    if args[0] == "--batch":
        with open(args[1]) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    print(check(line))
    else:
        for a in args:
            print(check(a))


if __name__ == "__main__":
    main()
