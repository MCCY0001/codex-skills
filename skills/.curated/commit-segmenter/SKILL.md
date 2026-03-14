---
name: "commit-segmenter"
description: "Use when a feature branch with checkpoint commits, mixed history, or a dirty worktree should be cleaned into Conventional Commits and then optionally published. Do not use for git log inspection, branch creation, or manual rebase and conflict-resolution tasks."
---

# Commit Segmenter

Default flow:
- resolve `<skill-root>` to this installed skill directory before running any script
- clean the current feature branch:
  - `python <skill-root>/scripts/finish_workflow.py`
- publish only when needed:
  - `python <skill-root>/scripts/publish_workflow.py`

Decision rules:
- use `finish` for dirty worktrees, checkpoint commits, or mixed states
- use `--dry-run` before touching history when the user wants a preview or safety check
- use `--base <ref>` only when the repo's canonical base is not `origin/main`
- do not run bare `scripts/...` paths from the user's repo root; always resolve paths from the installed skill copy

Defaults:
- base defaults to `origin/main`
- run `finish` only on a feature branch
- cleanup on success, keep recovery state on failure

Load `references/usage.md` or `references/usage.zh-CN.md` only when the user asks how to use the skill or what inputs it expects. These are minimal usage cards; match the user's language.
Load `references/feature-workflow.md` only when a run fails or recovery steps are needed.
