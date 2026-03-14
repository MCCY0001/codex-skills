#!/usr/bin/env python3
"""Backward-compatible wrapper around skill_repo.py export."""

from __future__ import annotations

import argparse
import sys

from skill_repo import main as skill_repo_main


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export source skills into an installer-friendly catalog."
    )
    parser.add_argument(
        "--source-root",
        help="Source root that contains canonical skill folders.",
    )
    parser.add_argument(
        "--dest-root",
        help="Deprecated. Use --catalog curated|experimental instead.",
    )
    parser.add_argument(
        "--skill-name",
        nargs="+",
        help="One or more skill names to export. Defaults to all source skills.",
    )
    parser.add_argument(
        "--delete-stale",
        action="store_true",
        help="Delete catalog entries that are not in the selected export set.",
    )
    return parser.parse_args(argv)


def infer_catalog(dest_root: str | None) -> str:
    if not dest_root:
        return "curated"
    normalized = dest_root.replace("\\", "/")
    if normalized.endswith("/.experimental") or normalized.endswith("/experimental"):
        return "experimental"
    return "curated"


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    forwarded = ["export", "--catalog", infer_catalog(args.dest_root)]
    if args.source_root:
        forwarded.extend(["--source-root", args.source_root])
    if args.delete_stale:
        forwarded.append("--delete-stale")
    if args.skill_name:
        forwarded.extend(args.skill_name)
    return skill_repo_main(forwarded)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
