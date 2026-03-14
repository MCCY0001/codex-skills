"""Internal helpers for semantic commit segmentation."""

from __future__ import annotations

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


def git_args(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout.strip()


def parse_commit_message(subject: str) -> tuple[str, str, str]:
    match = CONVENTIONAL_RE.match(subject.strip())
    if match:
        return match.group("type"), match.group("scope") or "", match.group("desc").strip()
    return "chore", "", subject.strip()


def normalize_scope(scope: str) -> str:
    return scope.strip().lower().replace(" ", "-")


def load_rule_config() -> tuple[OrderedDict[str, str], list[str], str]:
    try:
        spec_text = DEFAULT_SPEC_FILE.read_text(encoding="utf-8").removeprefix("\ufeff").strip()
    except (FileNotFoundError, OSError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"Cannot load commit spec: {DEFAULT_SPEC_FILE}") from exc

    scope_rules = OrderedDict(DEFAULT_SCOPE_RULES)
    ignore_patterns = list(DEFAULT_IGNORE_PATTERNS)
    fallback_scope = "type"
    section = ""

    for raw_line in spec_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        if line.startswith("#") or not line.startswith("-"):
            continue

        item = line[1:].strip()
        if not item:
            continue

        if section.startswith("scope rules"):
            if "->" in item:
                left, right = item.split("->", 1)
            elif ":" in item:
                left, right = item.split(":", 1)
            else:
                continue
            scope = normalize_scope(right)
            if not scope:
                continue
            for prefix in left.split(","):
                key = normalize_scope(prefix.strip())
                if key:
                    scope_rules[key] = scope
            continue

        if section.startswith("ignore patterns"):
            pattern = item.strip().strip("*").strip().lower()
            if pattern and pattern not in ignore_patterns:
                ignore_patterns.append(pattern)
            continue

        if section.startswith("fallback scope"):
            candidate = item.lower()
            if "path component" in candidate:
                fallback_scope = "first_path_component"

    return scope_rules, ignore_patterns, fallback_scope


def is_ignored(path: str, ignore_patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/").lower()
    segments = normalized.split("/")
    for pattern in ignore_patterns:
        normalized_pattern = pattern.strip().strip("/").lower()
        if not normalized_pattern:
            continue
        if normalized == normalized_pattern or normalized.startswith(normalized_pattern + "/"):
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
) -> str:
    if scope:
        return normalize_scope(scope)

    normalized_files = [path.replace("\\", "/").strip() for path in files if path and path.strip()]
    normalized_files = [path for path in normalized_files if not is_ignored(path, ignore_patterns)]
    if not normalized_files:
        return commit_type

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
    output = git_args("show", "--pretty=format:", "--name-only", "--no-color", sha)
    return [line.strip() for line in output.splitlines() if line.strip()]


def list_commits(base: str, head: str) -> list[tuple[str, str]]:
    output = git_args("log", "--reverse", "--format=%H%x01%s", f"{base}..{head}")
    commits = []
    for line in output.splitlines():
        if not line.strip():
            continue
        sha, subject = line.split("\x01", 1)
        commits.append((sha, subject.strip()))
    return commits


def describe_group(commits: list[tuple[str, str, list[str]]], commit_type: str, scope: str) -> str:
    if not commits:
        return f"{commit_type}({scope}): semantic refactor"

    descriptions = [desc for _, subject, *_ in commits if (desc := parse_commit_message(subject)[2])]
    base_desc = descriptions[0] if len(descriptions) == 1 else "group related changes"
    tokens = [word.lower() for word in base_desc.replace("-", " ").split() if word.lower() not in STOP_WORDS]
    if tokens:
        base_desc = " ".join(tokens[:5])
    return f"{commit_type}({scope}): {base_desc}"


def build_plan(base: str, head: str) -> list[dict]:
    scope_rules, ignore_patterns, fallback_scope = load_rule_config()
    groups: list[dict] = []

    for sha, subject in list_commits(base, head):
        commit_type, parsed_scope, _ = parse_commit_message(subject)
        files = commit_files(sha)
        scope = infer_scope_from_files(commit_type, parsed_scope, files, scope_rules, ignore_patterns, fallback_scope)
        group_key = (commit_type, scope)

        if groups and groups[-1]["type"] == group_key[0] and groups[-1]["scope"] == group_key[1]:
            groups[-1]["commits"].append((sha, subject, files))
            groups[-1]["files"].update(files)
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


def apply_groups_to_current_branch(groups: list[dict]) -> int:
    if git_args("status", "--porcelain").strip():
        raise RuntimeError("Working tree is not clean. Commit only with a clean tree.")

    created = 0
    for group in groups:
        for sha, _, _ in group["commits"]:
            git_args("cherry-pick", "--no-commit", sha)

        try:
            git_args("diff", "--cached", "--quiet")
            print(f"Skipping empty group: {group['message']}")
            git_args("reset")
            continue
        except subprocess.CalledProcessError:
            pass

        git_args("commit", "-m", group["message"])
        created += 1

    return created
