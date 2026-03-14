#!/usr/bin/env python3
"""Clean the current feature branch into Conventional Commits."""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from dataclasses import dataclass

from segment_commits import apply_groups_to_current_branch, build_plan, git_args, print_plan


DEFAULT_BASE_REF = "origin/main"


@dataclass
class FinishContext:
    branch: str
    safety_ref: str
    scratch_branch: str
    stash_revision: str | None = None


def timestamp_suffix() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def sanitize_ref_component(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._/-]+", "-", value.strip())
    sanitized = re.sub(r"/+", "/", sanitized)
    sanitized = sanitized.strip("/.")
    sanitized = sanitized.replace("..", "-")
    return sanitized or "work"


def git(*args: str) -> str:
    return git_args(*args)


def git_quiet(*args: str) -> bool:
    try:
        git(*args)
        return True
    except subprocess.CalledProcessError:
        return False


def working_tree_is_dirty() -> bool:
    return bool(git("status", "--porcelain").strip())


def current_branch_name() -> str:
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":
        raise RuntimeError("Detached HEAD is not supported. Switch to a feature branch before running finish.")
    return branch


def ensure_feature_branch() -> str:
    branch = current_branch_name()
    if branch == "main":
        raise RuntimeError("Refusing to run finish on 'main'. Switch to a feature branch first.")
    return branch


def ensure_base_exists(base_ref: str) -> None:
    if not git_quiet("rev-parse", "--verify", base_ref):
        raise RuntimeError(f"Base ref '{base_ref}' is unavailable. Fetch it or pass --base <ref>.")


def count_commits(base_ref: str, head: str = "HEAD") -> int:
    return int(git("rev-list", "--count", f"{base_ref}..{head}"))


def create_finish_context(branch: str) -> FinishContext:
    original_head = git("rev-parse", "HEAD")
    branch_path = sanitize_ref_component(branch)
    stamp = timestamp_suffix()
    safety_ref = f"refs/codex-safety/{branch_path}/head-{stamp}"
    scratch_branch = f"codex/finish/{branch_path}/{stamp}"
    git("update-ref", safety_ref, original_head)
    git("branch", scratch_branch, original_head)
    return FinishContext(branch=branch, safety_ref=safety_ref, scratch_branch=scratch_branch)


def create_dirty_snapshot(context: FinishContext) -> str:
    stash_name = f"codex-finish-{sanitize_ref_component(context.branch).replace('/', '-')}-{timestamp_suffix()}"
    git("stash", "push", "--include-untracked", "-m", stash_name)
    context.stash_revision = git("rev-parse", "refs/stash")

    git("switch", context.scratch_branch)
    git("stash", "apply", "--index", context.stash_revision)
    git("add", "-A")
    git("commit", "-m", "finish workflow snapshot")
    return git("rev-parse", "HEAD")


def prepare_input_head(context: FinishContext) -> str:
    if working_tree_is_dirty():
        return create_dirty_snapshot(context)

    git("switch", context.scratch_branch)
    return git("rev-parse", "HEAD")


def update_feature_branch(branch: str, target: str) -> None:
    git("branch", "-f", branch, target)
    git("switch", branch)


def drop_stash_revision(stash_revision: str | None) -> None:
    if not stash_revision:
        return

    output = git("stash", "list", "--format=%gd%x01%H")
    for line in output.splitlines():
        selector, revision = line.split("\x01", 1)
        if revision == stash_revision:
            git("stash", "drop", selector)
            return


def cleanup_success(context: FinishContext) -> None:
    drop_stash_revision(context.stash_revision)
    if git_quiet("show-ref", "--verify", context.safety_ref):
        git("update-ref", "-d", context.safety_ref)
    if git_quiet("show-ref", "--verify", f"refs/heads/{context.scratch_branch}"):
        git("branch", "-D", context.scratch_branch)


def print_recovery(context: FinishContext) -> None:
    print("")
    print("Recovery:")
    print(f"- safety ref: {context.safety_ref}")
    print(f"- scratch branch: {context.scratch_branch}")
    print(f"- restore branch: git branch -f {context.branch} {context.safety_ref}")
    print(f"- switch back: git switch {context.branch}")
    if context.stash_revision:
        print(f"- snapshot stash revision: {context.stash_revision}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default=DEFAULT_BASE_REF,
        help="Base ref used to calculate cleaned commits. Defaults to origin/main.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the cleanup plan without changing refs, stashes, branches, or commits.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    context: FinishContext | None = None

    try:
        if args.dry_run:
            print(f"Dry run: using existing local ref '{args.base}'.")
        else:
            git("fetch", "origin")

        ensure_base_exists(args.base)
        branch = ensure_feature_branch()
        dirty = working_tree_is_dirty()

        if not dirty and count_commits(args.base) == 0:
            print("No commits found between the feature branch and base. Nothing to finish.")
            return 0

        if args.dry_run:
            print(f"Current branch: {branch}")
            print(f"Base ref: {args.base}")
            if dirty:
                print("Working tree is dirty. Dry-run grouping is based on committed history only.")
                print("A real run would snapshot tracked and untracked changes before rewriting.")

            groups = build_plan(args.base, "HEAD")
            if not groups:
                print("No semantic commit groups were produced. Nothing to finish.")
                return 0

            print_plan(groups)
            print(f"Dry run completed for {branch}. No branches, refs, stashes, or commits were changed.")
            return 0

        context = create_finish_context(branch)
        print(f"Safety ref: {context.safety_ref}")
        print(f"Scratch branch: {context.scratch_branch}")

        input_head = prepare_input_head(context)
        groups = build_plan(args.base, input_head)
        if not groups:
            git("switch", context.branch)
            cleanup_success(context)
            print("No semantic commit groups were produced. Nothing to finish.")
            return 0

        print_plan(groups)
        git("reset", "--hard", args.base)
        created = apply_groups_to_current_branch(groups)
        if created == 0:
            update_feature_branch(context.branch, args.base)
            cleanup_success(context)
            print(f"No non-empty cleaned commits were produced. Reset {context.branch} to {args.base}.")
            return 0

        cleaned_head = git("rev-parse", "HEAD")
        update_feature_branch(context.branch, cleaned_head)
        print(f"Updated {context.branch} with {created} cleaned commit(s).")

        cleanup_success(context)
        print(f"Finish workflow completed on {context.branch}.")
        return 0
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        message = exc.stdout.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stdout else str(exc)
        print(f"Finish workflow failed: {message}", file=sys.stderr)
        if context is not None:
            print_recovery(context)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
