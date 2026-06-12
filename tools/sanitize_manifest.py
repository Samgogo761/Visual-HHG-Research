#!/usr/bin/env python3
"""Sanitize a manifest JSON by replacing private absolute paths with placeholders.

Use this on any manifest_*.json (including the legacy manifest_hhgxr_v0.json)
before committing it to a public repository. The script is conservative: it
inspects every string value in the JSON tree, recognizes a small set of
"this looks like a private absolute path" patterns, and replaces them with
named placeholders.

Examples of replacements:

    C:\\Users\\26507\\Documents\\...\\lgcov_k40_nb104\\Jt.dat
        -> <LOCAL_SBE_RUN_DIR>/Jt.dat

    /home/jiashen/data/sbe/run01/HHG.dat
        -> <LOCAL_SBE_RUN_DIR>/HHG.dat

    \\\\server\\share\\wannier\\CrI3_band.dat
        -> <LOCAL_WANNIER_DIR>/CrI3_band.dat

Heuristics (in order):

1. A path ending in ``CrI3_band.dat`` or under a path containing ``wannier``
   is mapped under ``<LOCAL_WANNIER_DIR>``.
2. Any other absolute path that contains a recognized SBE/run keyword
   (``lgcov``, ``lg_cov``, ``sbe``, ``new_sbe``, ``output_lg_cov``) is
   mapped under ``<LOCAL_SBE_RUN_DIR>``.
3. Any other absolute Windows/Unix/UNC path is mapped under
   ``<LOCAL_PATH>`` and a warning is printed.

The script never modifies a file in place by default. Use ``--in-place``
explicitly to overwrite the input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

RUN_PLACEHOLDER = "<LOCAL_SBE_RUN_DIR>"
WANNIER_PLACEHOLDER = "<LOCAL_WANNIER_DIR>"
GENERIC_PLACEHOLDER = "<LOCAL_PATH>"

WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")
UNC_PATH = re.compile(r"^\\\\[^\\]+\\[^\\]+")
UNIX_ABS = re.compile(r"^/(?:home|root|mnt|media|Users|data|scratch|work|share|var|opt)/")

WANNIER_HINTS = ("cri3_band", "wannier", "cri3_tb", "cri3_hr")
RUN_HINTS = ("lgcov", "lg_cov", "sbe", "new_sbe", "output_lg_cov", "0p5cycle")


def looks_like_abs_path(s: str) -> bool:
    if not isinstance(s, str) or not s:
        return False
    if WINDOWS_DRIVE.match(s) or UNC_PATH.match(s):
        return True
    if UNIX_ABS.match(s):
        return True
    return False


def classify(path: str) -> tuple[str, str]:
    """Return (placeholder, tail) for a recognized private path."""
    norm = path.replace("\\", "/")
    lower = norm.lower()
    tail = norm.rsplit("/", 1)[-1]

    if any(h in lower for h in WANNIER_HINTS):
        return WANNIER_PLACEHOLDER, tail
    if any(h in lower for h in RUN_HINTS):
        idx = max(lower.rfind(h) for h in RUN_HINTS)
        sub = norm[idx:]
        rest = sub.split("/", 1)[1] if "/" in sub else tail
        return RUN_PLACEHOLDER, rest
    return GENERIC_PLACEHOLDER, tail


def sanitize_string(s: str, warnings: list[str]) -> str:
    if not looks_like_abs_path(s):
        return s
    placeholder, tail = classify(s)
    if placeholder == GENERIC_PLACEHOLDER:
        warnings.append(f"unclassified absolute path: {s!r}")
    return f"{placeholder}/{tail}"


def sanitize_tree(node: Any, warnings: list[str]) -> Any:
    if isinstance(node, dict):
        return {k: sanitize_tree(v, warnings) for k, v in node.items()}
    if isinstance(node, list):
        return [sanitize_tree(v, warnings) for v in node]
    if isinstance(node, str):
        return sanitize_string(node, warnings)
    return node


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--in", dest="inp", required=True, type=Path,
                   help="Input manifest JSON file.")
    p.add_argument("--out", dest="out", type=Path, default=None,
                   help="Output path. Defaults to <input>.sanitized.json.")
    p.add_argument("--in-place", action="store_true",
                   help="Overwrite the input file. Mutually exclusive with --out.")
    p.add_argument("--check-only", action="store_true",
                   help="Exit non-zero if absolute paths are detected; do not write.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.in_place and args.out:
        print("error: --in-place and --out are mutually exclusive", file=sys.stderr)
        return 2

    src = json.loads(args.inp.read_text())
    warnings: list[str] = []
    cleaned = sanitize_tree(src, warnings)
    changed = cleaned != src

    if args.check_only:
        if changed:
            print(f"[fail] {args.inp} contains absolute paths", file=sys.stderr)
            for w in warnings:
                print(f"  - {w}", file=sys.stderr)
            return 1
        print(f"[ok] {args.inp} has no absolute paths")
        return 0

    out_path = args.inp if args.in_place else (args.out or args.inp.with_suffix(".sanitized.json"))
    out_path.write_text(json.dumps(cleaned, indent=2))

    print(f"[ok] wrote sanitized manifest -> {out_path}")
    if not changed:
        print("[ok] no absolute paths detected; output is identical to input")
    for w in warnings:
        print(f"[warn] {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
