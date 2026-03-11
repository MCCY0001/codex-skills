#!/usr/bin/env python3
"""Generate semantic commit segments from git history and optionally apply them."""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
from collections import OrderedDict
from pathlib import Path
from typing import Iterable


CONVENTIONAL_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?:\s*(?P<desc>.+)$")
STOP_WORDS = {
    "a",
    "and",
    "the",
    "for",
    "with",
    "from",
    "that",
    "this",
    "those",
    "these",
    "have",
    "when",
    "where",
    "which",
    "while",
}

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SPEC_FILE = SCRIPT_DIR.parent / "assets" / "conventional_commits.md"

DEFAULT_SCOPE_RULES = OrderedDict(
    [
        ("docs", "docs"),
        ("documentation", "docs"),
        ("design", "docs"),
        ("scripts", "scripts"),
        ("tests", "tests"),
        ("testing", "tests"),
        ("test", "tests"),
        ("tooling", "tooling"),
        ("tools", "tooling"),
        ("src", "src"),
        ("source", "src"),
        ("packages", "src"),
        ("pkg", "src"),
        ("infra", "infra"),
        ("infrastructure", "infra"),
        ("config", "config"),
        ("configs", "config"),
        ("assets", "assets"),
        ("artifact", "artifacts"),
        ("artifacts", "artifacts"),
        ("plots", "artifacts"),
        ("runs", "artifacts"),
        ("ci", "ci"),
    ]
)

DEFAULT_IGNORE_PATTERNS = [
    ".git",
    ".idea",
    ".vscode",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    ".venv",
    "venv",
    "build",
    "dist",
    "node_modules",
]


def run(cmd: str) -> str:
    return subprocess.run(
        cmd,
        check=True,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout.strip()


def git(cmd: str) -> str:
    return run(f"git {cmd}")


def has_unmerged(_: str = ".") -> bool:
    return bool(git("status --porcelain").strip())


def parse_commit_message(subject: str) -> tuple[str, str, str]:
    m = CONVENTIONAL_RE.match(subject.strip())
    if m:
        return m.group("type"), m.group("scope") or "", m.group("desc").strip()
    return "chore", "", subject.strip()


def normalize_scope(scope: str) -> str:
    return scope.strip().lower().replace(" ", "-")


def read_text_optional(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return None


def normalize_spec_text(spec_text: str) -> str:
    if not spec_text:
        return ""
    return spec_text.removeprefix("\ufeff").strip()


def load_spec_text(spec_file: str | None) -> tuple[str, Path, bool]:
    """
    Returns (spec_text, used_path, used_fallback_default).
    used_fallback_default=True means user-provided path was unavailable.
    """
    requested_path = None
    if spec_file:
        requested_path = Path(spec_file).expanduser().resolve()

    candidates: list[Path] = []
    if requested_path is not None:
        candidates.append(requested_path)
    candidates.append(DEFAULT_SPEC_FILE)

    for candidate in candidates:
        text = read_text_optional(candidate)
        if text is not None:
            if requested_path is not None and candidate != requested_path:
                return text, candidate, True
            return text, candidate, False

    return "", DEFAULT_SPEC_FILE, True


def parse_spec_rules(spec_text: str) -> tuple[OrderedDict[str, str], list[str], str, bool]:
    scope_rules = OrderedDict(DEFAULT_SCOPE_RULES)
    ignore_patterns = list(DEFAULT_IGNORE_PATTERNS)
    fallback_scope = "type"
    section = ""
    parsed = False

    for raw_line in spec_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        if line.startswith("#"):
            continue
        if not line.startswith("-"):
            continue

        item = line[1:].strip()
        if not item:
            continue

        if section.startswith("scope rules"):
            parsed = True
            if "->" in item:
                left, right = item.split("->", 1)
                scope = normalize_scope(right)
            elif ":" in item:
                left, right = item.split(":", 1)
                scope = normalize_scope(right)
            else:
                continue
            if not scope:
                continue
            for prefix in left.split(","):
                key = normalize_scope(prefix.strip())
                if key:
                    scope_rules[key] = scope
            continue

        if section.startswith("ignore patterns"):
            parsed = True
            pattern = item.strip().strip("*").strip().lower()
            if pattern and pattern not in ignore_patterns:
                ignore_patterns.append(pattern)
            continue

        if section.startswith("fallback scope"):
            parsed = True
            candidate = item.lower()
            if "path component" in candidate:
                fallback_scope = "first_path_component"
            elif candidate == "type" or "commit type" in candidate:
                fallback_scope = "type"

    return scope_rules, ignore_patterns, fallback_scope, parsed


def is_ignored(path: str, ignore_patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/").lower()
    segments = normalized.split("/")
    for pattern in ignore_patterns:
        normalized_pattern = pattern.strip().strip("/").lower()
        if not normalized_pattern:
            continue
        if normalized == normalized_pattern:
            return True
        if normalized.startswith(normalized_pattern + "/"):
            return True
        if normalized_pattern in segments:
            return True
    return False


def infer_scope_from_files(
    commit_type: str,
    scope: str,
    files: Iterable[str],
    scope_rules: OrderedDict[str, str],
    ignore_patterns: list[str],
    fallback_scope: str,
    no_project_rules: bool = False,
) -> str:
    if scope:
        return normalize_scope(scope)

    normalized_files = [path.replace("\\", "/").strip() for path in files if path and path.strip()]
    normalized_files = [path for path in normalized_files if not is_ignored(path, ignore_patterns)]
    if not normalized_files:
        return commit_type

    if no_project_rules:
        first_part = normalized_files[0].split("/", 1)[0]
        return normalize_scope(first_part or commit_type)

    for path in normalized_files:
        for prefix, inferred in scope_rules.items():
            if path == prefix or path.startswith(prefix + "/"):
                return inferred
        first_part = path.split("/", 1)[0]
        if first_part in scope_rules:
            return scope_rules[first_part]

    if fallback_scope == "first_path_component":
        return normalize_scope(normalized_files[0].split("/", 1)[0] or commit_type)

    return commit_type


def commit_files(sha: str) -> list[str]:
    output = git(f"show --pretty=format: --name-only --no-color {sha}")
    return [ln.strip() for ln in output.splitlines() if ln.strip()]


def list_commits(base: str | None, head: str, n: int | None) -> list[tuple[str, str]]:
    if n is not None:
        range_spec = f"{head}~{n}..{head}"
    else:
        range_spec = f"{base}..{head}"
    out = git(f"log --reverse --format=%H%x01%s {range_spec}")
    commits = []
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, subject = line.split("\x01", 1)
        commits.append((sha, subject.strip()))
    return commits


def describe_group(
    commits: list[tuple[str, str, list[str]]],
    commit_type: str,
    scope: str,
) -> str:
    if not commits:
        return f"{commit_type}({scope}): semantic refactor"

    descs = [desc for _, subject, *_ in commits if (desc := parse_commit_message(subject)[2])]
    base_desc = descs[0] if len(descs) == 1 else "group related changes"
    tokens = [w.lower() for w in base_desc.replace("-", " ").split() if w.lower() not in STOP_WORDS]
    if tokens:
        base_desc = " ".join(tokens[:5])
    return f"{commit_type}({scope}): {base_desc}"


def plan_segments(
    commits: list[tuple[str, str]],
    scope_rules: OrderedDict[str, str],
    ignore_patterns: list[str],
    fallback_scope: str,
    no_project_rules: bool = False,
) -> list[dict]:
    groups: list[dict] = []
    for sha, subject in commits:
        commit_type, parsed_scope, _ = parse_commit_message(subject)
        files = commit_files(sha)
        scope = infer_scope_from_files(
            commit_type,
            parsed_scope,
            files,
            scope_rules,
            ignore_patterns,
            fallback_scope,
            no_project_rules=no_project_rules,
        )
        group_key = (commit_type, scope)

        if groups and groups[-1]["type"] == group_key[0] and groups[-1]["scope"] == group_key[1]:
            group = groups[-1]
            group["commits"].append((sha, subject, files))
            group["files"].update(files)
        else:
            groups.append(
                {
                    "type": group_key[0],
                    "scope": group_key[1],
                    "commits": [(sha, subject, files)],
                    "files": set(files),
                }
            )
    for group in groups:
        group["message"] = describe_group(group["commits"], group["type"], group["scope"])
    return groups


def print_plan(groups: list[dict]) -> None:
    for group in groups:
        print(f"commit message: {group['message']}")
        print("commit files:")
        for file in sorted(group["files"]):
            print(f"- {file}")
        print("")


def apply_segments(groups: list[dict], target_branch: str, base: str | None, start_sha: str | None) -> None:
    if has_unmerged("."):
        raise RuntimeError("Working tree is not clean. Commit only with a clean tree.")

    if base is None and start_sha is None:
        raise RuntimeError("Cannot determine apply base. Please pass --base or use --n for a range.")
    if base is None:
        base = run(f"git rev-parse {start_sha}^")

    git(f"switch -c {target_branch} {base}")
    for group in groups:
        for sha, _, _ in group["commits"]:
            git(f"cherry-pick --no-commit {sha}")

        try:
            run("git diff --cached --quiet")
            print(f"Skipping empty group: {group['message']}")
            run("git reset")
            continue
        except subprocess.CalledProcessError:
            pass

        git(f"commit -m \"{group['message']}\"")

    run(f"git log --oneline {base}..{target_branch} --reverse")


def pick_default_base() -> str:
    try:
        return git("rev-parse --verify origin/main")
    except subprocess.CalledProcessError:
        return git("rev-parse --verify --max-parents=0 HEAD")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Segment commits by semantic scope")
    parser.add_argument("--base", default=None, help="Base ref, default origin/main")
    parser.add_argument("--head", default="HEAD", help="Head ref, default HEAD")
    parser.add_argument("--n", type=int, default=None, help="Use HEAD~N..HEAD when provided")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create a new branch with segmented commits",
    )
    parser.add_argument(
        "--target-branch",
        default=None,
        help="Branch name when apply=True (default commit-segment-<timestamp>)",
    )
    parser.add_argument(
        "--spec-file",
        default=None,
        help=f"Path to Conventional Commits rule file (default: {DEFAULT_SPEC_FILE})",
    )
    parser.add_argument(
        "--no-project-rules",
        action="store_true",
        help="Skip project directory mapping and use first path component as scope fallback",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base = args.base or pick_default_base()
    head = args.head

    spec_text, used_spec, used_fallback = load_spec_text(args.spec_file)
    spec_text = normalize_spec_text(spec_text)

    if args.spec_file and used_fallback:
        print(f"Warning: spec file not found or unreadable: {args.spec_file}. Falling back to {used_spec}.")
    elif used_fallback and not args.spec_file:
        if not spec_text:
            print(f"Warning: default spec file missing: {used_spec}. Using built-in fallback rules.")
        else:
            print(f"Warning: default spec file unavailable. Using built-in fallback rules.")

    scope_rules, ignore_patterns, fallback_scope, spec_parsed = parse_spec_rules(spec_text)
    if spec_text and not spec_parsed:
        print(f"Warning: spec file could not be parsed: {used_spec}. Falling back to built-in defaults.")
    if not spec_text:
        print("Warning: conventional commit spec is unavailable; using built-in fallback rules.")

    commits = list_commits(base, head, args.n)
    groups = plan_segments(
        commits,
        scope_rules,
        ignore_patterns,
        fallback_scope,
        no_project_rules=args.no_project_rules,
    )
    if not groups:
        print("No commits found in the selected range.")
        return

    print_plan(groups)

    if args.apply:
        branch = args.target_branch or f"segment-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        apply_base = base if args.n is None else None
        start_sha = commits[0][0] if commits else None
        apply_segments(groups, branch, apply_base, start_sha)
        print(f"Applied segmented commits on {branch}")


if __name__ == "__main__":
    main()
