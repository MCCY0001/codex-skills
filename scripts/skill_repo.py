#!/usr/bin/env python3
"""Manage skill sources, catalogs, runtime sync, and release checks."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_ROOT = REPO_ROOT / "skills"
CATALOG_NAMES = ("curated", "experimental")
IGNORE_PATTERNS = ("__pycache__", "*.pyc", "*.pyo", ".DS_Store", "Thumbs.db")
DISALLOWED_SKILL_FILES = {
    "README.md",
    "CHANGELOG.md",
    "INSTALLATION_GUIDE.md",
    "QUICK_REFERENCE.md",
}


class SkillRepoError(Exception):
    """Raised when a skill repository operation fails."""


@dataclass(frozen=True)
class ValidationResult:
    name: str
    errors: list[str]


def default_runtime_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser().resolve() / "skills"
    return (Path.home() / ".codex" / "skills").resolve()


def catalog_root(source_root: Path, catalog: str) -> Path:
    return source_root / f".{catalog}"


def is_ignored(path: Path) -> bool:
    parts = path.parts
    for part in parts:
        if part == "__pycache__":
            return True
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(path.name, pattern):
            return True
    return False


def is_skill_dir(path: Path) -> bool:
    return path.is_dir() and (path / "SKILL.md").is_file()


def iter_skill_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        raise SkillRepoError(f"Source root not found: {root}")

    skills: list[Path] = []
    for child in sorted(root.iterdir()):
        if child.name.startswith(".") or not is_skill_dir(child):
            continue
        skills.append(child)
    return skills


def resolve_skill_dirs(root: Path, names: list[str] | None) -> list[Path]:
    if not names:
        return iter_skill_dirs(root)

    selected: list[Path] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        path = root / name
        if not is_skill_dir(path):
            raise SkillRepoError(f"Skill source not found or missing SKILL.md: {path}")
        selected.append(path)
    return selected


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_skill_frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillRepoError(f"SKILL.md is missing YAML frontmatter: {skill_md}")

    try:
        end_index = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise SkillRepoError(f"SKILL.md frontmatter is not closed: {skill_md}") from exc

    metadata: dict[str, str] = {}
    for line in lines[1:end_index]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            continue
        key, raw_value = match.groups()
        metadata[key] = strip_quotes(raw_value)
    return metadata


def parse_openai_interface(openai_yaml: Path) -> dict[str, str]:
    text = openai_yaml.read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^interface:\s*\n(?P<body>(?:^[ \t]+.*\n?)*)",
        text,
    )
    if not match:
        raise SkillRepoError(f"agents/openai.yaml is missing an interface block: {openai_yaml}")

    interface: dict[str, str] = {}
    for line in match.group("body").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", stripped)
        if not key_match:
            continue
        key, raw_value = key_match.groups()
        interface[key] = strip_quotes(raw_value)
    return interface


def collect_manifest(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}

    manifest: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel_path = path.relative_to(root)
        if is_ignored(rel_path):
            continue
        key = rel_path.as_posix()
        if path.is_dir():
            manifest[key] = "dir"
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest[key] = f"file:{digest}"
    return manifest


def copy_skill_tree(source_dir: Path, dest_dir: Path) -> None:
    shutil.copytree(source_dir, dest_dir, ignore=shutil.ignore_patterns(*IGNORE_PATTERNS))


def remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def validate_skill_dir(skill_dir: Path) -> ValidationResult:
    errors: list[str] = []
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        errors.append("missing SKILL.md")
        return ValidationResult(name=skill_name, errors=errors)

    try:
        metadata = parse_skill_frontmatter(skill_md)
    except SkillRepoError as exc:
        errors.append(str(exc))
        return ValidationResult(name=skill_name, errors=errors)

    frontmatter_name = metadata.get("name", "").strip()
    description = metadata.get("description", "").strip()
    if not frontmatter_name:
        errors.append("SKILL.md frontmatter is missing `name`")
    elif frontmatter_name != skill_name:
        errors.append(f"frontmatter name `{frontmatter_name}` does not match folder name `{skill_name}`")
    if not description:
        errors.append("SKILL.md frontmatter is missing `description`")

    for disallowed_name in sorted(DISALLOWED_SKILL_FILES):
        if (skill_dir / disallowed_name).exists():
            errors.append(f"disallowed auxiliary file present: {disallowed_name}")

    openai_yaml = skill_dir / "agents" / "openai.yaml"
    if openai_yaml.is_file():
        try:
            interface = parse_openai_interface(openai_yaml)
        except SkillRepoError as exc:
            errors.append(str(exc))
        else:
            for key in ("display_name", "short_description", "default_prompt"):
                value = interface.get(key, "").strip()
                if not value:
                    errors.append(f"agents/openai.yaml interface is missing `{key}`")
            for icon_key in ("icon_large", "icon_small"):
                icon_value = interface.get(icon_key, "").strip()
                if icon_value.startswith("./"):
                    icon_path = skill_dir / icon_value[2:]
                    if not icon_path.exists():
                        errors.append(f"agents/openai.yaml references missing asset `{icon_value}`")

    evals_dir = skill_dir / "evals"
    if evals_dir.exists() and not (evals_dir / "prompts.md").is_file():
        errors.append("evals directory exists but evals/prompts.md is missing")

    for script_path in sorted((skill_dir / "scripts").glob("*.py")):
        try:
            source = script_path.read_text(encoding="utf-8")
            compile(source, str(script_path), "exec")
        except SyntaxError as exc:
            errors.append(
                f"python script failed to compile: {script_path.name}: line {exc.lineno}: {exc.msg}"
            )

    return ValidationResult(name=skill_name, errors=errors)


def compare_export_drift(source_dir: Path, catalog_dir: Path) -> list[str]:
    if not catalog_dir.exists():
        return [f"catalog entry is missing: {catalog_dir}"]

    source_manifest = collect_manifest(source_dir)
    catalog_manifest = collect_manifest(catalog_dir)
    if source_manifest == catalog_manifest:
        return []

    errors: list[str] = []
    missing = sorted(set(source_manifest) - set(catalog_manifest))
    extra = sorted(set(catalog_manifest) - set(source_manifest))
    changed = sorted(
        key for key in source_manifest.keys() & catalog_manifest.keys() if source_manifest[key] != catalog_manifest[key]
    )
    if missing:
        errors.append("catalog is missing paths: " + ", ".join(missing))
    if extra:
        errors.append("catalog has extra paths: " + ", ".join(extra))
    if changed:
        errors.append("catalog has drifted files: " + ", ".join(changed))
    return errors


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_list(args: argparse.Namespace) -> int:
    source_root = Path(args.source_root).resolve()

    def names_for_catalog(kind: str) -> list[str]:
        if kind == "source":
            return [path.name for path in iter_skill_dirs(source_root)]
        catalog_dir = catalog_root(source_root, kind)
        if not catalog_dir.is_dir():
            return []
        return [path.name for path in iter_skill_dirs(catalog_dir)]

    if args.catalog == "all":
        payload = {
            "source": names_for_catalog("source"),
            "curated": names_for_catalog("curated"),
            "experimental": names_for_catalog("experimental"),
        }
        if args.format == "json":
            print_json(payload)
            return 0
        for title, names in payload.items():
            print(f"{title}:")
            if names:
                for index, name in enumerate(names, start=1):
                    print(f"{index}. {name}")
            else:
                print("(none)")
        return 0

    names = names_for_catalog(args.catalog)
    if args.format == "json":
        print_json(names)
        return 0
    if args.format == "names":
        for name in names:
            print(name)
        return 0
    for index, name in enumerate(names, start=1):
        print(f"{index}. {name}")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    if args.no_clobber and args.force:
        raise SkillRepoError("--no-clobber and --force cannot be used together.")

    source_root = Path(args.source_root).resolve()
    runtime_path = Path(args.runtime_path).expanduser().resolve()
    backup_dir = (
        Path(args.backup_dir).expanduser().resolve() if args.backup_dir else runtime_path / ".backup"
    )
    selected = resolve_skill_dirs(source_root, args.names)

    actions: list[str] = []
    for source_dir in selected:
        target_dir = runtime_path / source_dir.name
        if target_dir.exists():
            if args.no_clobber:
                raise SkillRepoError(f"Destination already exists and --no-clobber is set: {target_dir}")
            if args.force:
                actions.append(f"remove {target_dir}")
            else:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_target = backup_dir / f"{source_dir.name}-{timestamp}"
                actions.append(f"backup {target_dir} -> {backup_target}")
        actions.append(f"publish {source_dir} -> {target_dir}")

    if args.what_if:
        for action in actions:
            print(f"Would {action}")
        return 0

    runtime_path.mkdir(parents=True, exist_ok=True)
    for source_dir in selected:
        target_dir = runtime_path / source_dir.name
        if target_dir.exists():
            if args.force:
                remove_tree(target_dir)
            else:
                backup_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_target = backup_dir / f"{source_dir.name}-{timestamp}"
                if backup_target.exists():
                    raise SkillRepoError(f"Backup target already exists: {backup_target}")
                shutil.move(str(target_dir), str(backup_target))
                print(f"Backed up {source_dir.name} -> {backup_target}")
        copy_skill_tree(source_dir, target_dir)
        print(f"Published {source_dir.name}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    source_root = Path(args.source_root).resolve()
    dest_root = catalog_root(source_root, args.catalog)
    if source_root == dest_root:
        raise SkillRepoError("Source root and destination root must be different.")

    selected = resolve_skill_dirs(source_root, args.names)
    dest_root.mkdir(parents=True, exist_ok=True)

    exported_names: set[str] = set()
    for source_dir in selected:
        dest_dir = dest_root / source_dir.name
        remove_tree(dest_dir)
        copy_skill_tree(source_dir, dest_dir)
        exported_names.add(source_dir.name)
        print(f"Exported {source_dir.name} -> {dest_dir}")

    if args.delete_stale and dest_root.is_dir():
        for child in iter_skill_dirs(dest_root):
            if child.name in exported_names:
                continue
            remove_tree(child)
            print(f"Deleted stale catalog entry {child.name}")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    source_root = Path(args.source_root).resolve()
    selected = resolve_skill_dirs(source_root, args.names)
    results: list[ValidationResult] = []

    for skill_dir in selected:
        result = validate_skill_dir(skill_dir)
        errors = list(result.errors)
        if args.check_export_drift:
            catalog_dir = catalog_root(source_root, args.catalog) / skill_dir.name
            errors.extend(compare_export_drift(skill_dir, catalog_dir))
        results.append(ValidationResult(name=result.name, errors=errors))

    failures = [result for result in results if result.errors]
    if args.format == "json":
        payload = {
            "ok": not failures,
            "results": [{"name": result.name, "errors": result.errors} for result in results],
        }
        print_json(payload)
    else:
        for result in results:
            if result.errors:
                print(f"[FAIL] {result.name}")
                for error in result.errors:
                    print(f"  - {error}")
            else:
                print(f"[OK] {result.name}")

    if failures:
        raise SkillRepoError("Validation failed.")
    return 0


def detect_origin_repo(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    remote = result.stdout.strip()
    if not remote:
        return None

    patterns = (
        r"^https://github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?$",
        r"^git@github\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?$",
        r"^ssh://git@github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.match(pattern, remote)
        if match:
            return match.group("repo")
    return None


def cmd_release_check(args: argparse.Namespace) -> int:
    validate_args = argparse.Namespace(
        source_root=args.source_root,
        names=args.names,
        check_export_drift=True,
        catalog=args.catalog,
        format="text",
    )
    cmd_validate(validate_args)

    source_root = Path(args.source_root).resolve()
    selected = resolve_skill_dirs(source_root, args.names)
    repo_name = args.repo or detect_origin_repo(REPO_ROOT)

    print("Release check passed.")
    if not repo_name:
        print("GitHub repo could not be auto-detected. Re-run with --repo owner/repo for install commands.")
        return 0

    print("Install commands:")
    for skill_dir in selected:
        print(
            "python <CODEX_HOME>/skills/.system/skill-installer/scripts/install-skill-from-github.py "
            f"--repo {repo_name} --ref {args.ref} --path skills/.{args.catalog}/{skill_dir.name}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage source, catalog, and runtime skill workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_source_root_argument(target: argparse.ArgumentParser) -> None:
        target.add_argument(
            "--source-root",
            default=str(DEFAULT_SOURCE_ROOT),
            help="Root directory that contains canonical source skills.",
        )

    list_parser = subparsers.add_parser("list", help="List source skills and exported catalogs.")
    add_source_root_argument(list_parser)
    list_parser.add_argument(
        "--catalog",
        choices=("all", "source", *CATALOG_NAMES),
        default="all",
        help="Which catalog to list.",
    )
    list_parser.add_argument(
        "--format",
        choices=("text", "json", "names"),
        default="text",
        help="Output format.",
    )
    list_parser.set_defaults(func=cmd_list)

    publish_parser = subparsers.add_parser("publish", help="Publish source skills into a runtime directory.")
    add_source_root_argument(publish_parser)
    publish_parser.add_argument("names", nargs="*", help="Skill names to publish. Defaults to all source skills.")
    publish_parser.add_argument(
        "--runtime-path",
        default=str(default_runtime_root()),
        help="Target runtime directory, usually $CODEX_HOME/skills.",
    )
    publish_parser.add_argument(
        "--backup-dir",
        help="Backup directory for replaced skills. Defaults to <runtime-path>/.backup.",
    )
    publish_parser.add_argument("--what-if", action="store_true", help="Preview actions without modifying files.")
    publish_parser.add_argument("--no-clobber", action="store_true", help="Fail if a target skill already exists.")
    publish_parser.add_argument("--force", action="store_true", help="Replace targets without creating a backup.")
    publish_parser.set_defaults(func=cmd_publish)

    export_parser = subparsers.add_parser("export", help="Export source skills into an installer catalog.")
    add_source_root_argument(export_parser)
    export_parser.add_argument("names", nargs="*", help="Skill names to export. Defaults to all source skills.")
    export_parser.add_argument(
        "--catalog",
        choices=CATALOG_NAMES,
        default="curated",
        help="Catalog to export into.",
    )
    export_parser.add_argument(
        "--delete-stale",
        action="store_true",
        help="Delete catalog entries that are no longer part of the selected export set.",
    )
    export_parser.set_defaults(func=cmd_export)

    validate_parser = subparsers.add_parser("validate", help="Validate skill structure and export drift.")
    add_source_root_argument(validate_parser)
    validate_parser.add_argument("names", nargs="*", help="Skill names to validate. Defaults to all source skills.")
    validate_parser.add_argument(
        "--check-export-drift",
        action="store_true",
        help="Fail if the selected catalog has drifted from source skills.",
    )
    validate_parser.add_argument(
        "--catalog",
        choices=CATALOG_NAMES,
        default="curated",
        help="Catalog to compare when --check-export-drift is enabled.",
    )
    validate_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    validate_parser.set_defaults(func=cmd_validate)

    release_parser = subparsers.add_parser("release-check", help="Run release validations and print install commands.")
    add_source_root_argument(release_parser)
    release_parser.add_argument("names", nargs="*", help="Skill names to release-check. Defaults to all source skills.")
    release_parser.add_argument("--ref", default="main", help="Git ref to use in the printed install commands.")
    release_parser.add_argument("--repo", help="Explicit GitHub repo in owner/repo format.")
    release_parser.add_argument(
        "--catalog",
        choices=CATALOG_NAMES,
        default="curated",
        help="Catalog to validate and print install commands for.",
    )
    release_parser.set_defaults(func=cmd_release_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except SkillRepoError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
