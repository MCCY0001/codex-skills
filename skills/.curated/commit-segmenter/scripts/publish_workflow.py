#!/usr/bin/env python3
"""Publish a cleaned feature branch."""

from __future__ import annotations

import argparse
import subprocess
import sys

from segment_commits import git_args


DEFAULT_BASE_REF = "origin/main"


def git(*args: str) -> str:
    return git_args(*args)


def git_quiet(*args: str) -> bool:
    try:
        git(*args)
        return True
    except subprocess.CalledProcessError:
        return False


def current_branch_name() -> str:
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":
        raise RuntimeError("Detached HEAD is not supported. Switch to a branch before running publish.")
    return branch


def ensure_base_exists(base_ref: str) -> None:
    if not git_quiet("rev-parse", "--verify", base_ref):
        raise RuntimeError(f"Base ref '{base_ref}' is unavailable. Fetch it or pass --base <ref>.")


def ensure_local_main() -> None:
    if not git_quiet("show-ref", "--verify", "refs/heads/main"):
        raise RuntimeError("Local 'main' branch is missing. Create it before publishing.")


def can_fast_forward(ancestor: str, descendant: str) -> bool:
    return git_quiet("merge-base", "--is-ancestor", ancestor, descendant)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default=DEFAULT_BASE_REF,
        help="Base ref that local main must fast-forward to before publishing. Defaults to origin/main.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview fast-forward checks without switching branches or pushing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    main_before_merge: str | None = None

    try:
        if args.dry_run:
            print(f"Dry run: using existing local ref '{args.base}'.")
        else:
            git("fetch", "origin")

        ensure_base_exists(args.base)
        current_branch = current_branch_name()
        if current_branch == "main":
            raise RuntimeError("publish expects a cleaned feature branch, not 'main'.")

        ensure_local_main()
        main_before_merge = git("rev-parse", "main")
        print(f"Main before merge: {main_before_merge}")

        if not can_fast_forward("main", args.base):
            raise RuntimeError(f"Local 'main' cannot fast-forward to '{args.base}'.")
        if not can_fast_forward(args.base, current_branch):
            raise RuntimeError(f"Branch '{current_branch}' is not a fast-forward descendant of '{args.base}'.")

        if args.dry_run:
            print(f"Current branch: {current_branch}")
            print(f"Base ref: {args.base}")
            print("Dry run completed. Local 'main' can fast-forward to the base and then to the cleaned branch.")
            print("No branches were switched and nothing was pushed.")
            return 0

        git("switch", "main")
        git("merge", "--ff-only", args.base)
        git("merge", "--ff-only", current_branch)
        print("Merged cleaned history into local main with --ff-only.")

        git("push", "origin", "main")
        print("Pushed main.")
        print("Publish workflow completed on main.")
        return 0
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        message = exc.stdout.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stdout else str(exc)
        print(f"Publish workflow failed: {message}", file=sys.stderr)
        print("")
        print("Recovery:")
        if main_before_merge:
            print(f"- main before merge: {main_before_merge}")
            print(f"- restore main: git branch -f main {main_before_merge}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
