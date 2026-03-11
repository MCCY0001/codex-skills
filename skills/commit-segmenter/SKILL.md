---
name: "commit-segmenter"
description: "Use when the user wants to finish feature work by turning dirty work or checkpoint commits into clean Conventional Commits, rebasing on origin/main, merging to main, pushing, and cleaning temporary workflow refs."
---

# Commit Segmenter

Use this skill to finish branch work after implementation. It covers two cases:
- rewrite an existing commit range into cleaner Conventional Commits
- finish a dirty working tree by creating seed commits, segmenting them, rebasing on `origin/main`, merging to `main`, pushing, and cleaning temporary refs

Prefer the bundled script for history-based segmentation. For dirty worktrees, use `references/feature-workflow.md`.

## When to use
- The user finished a requirement and wants clean commits before merge.
- The branch has rough checkpoint commits that should be rewritten.
- The working tree is dirty and needs a safe endgame before rebase, merge, and push.
- The user wants the full finish workflow, not just a commit plan.
- The user only wants a grouping plan with no history changes.

## Capability boundary
- `scripts/segment_commits.py` only segments an existing commit range.
- It does not split a dirty working tree directly.
- For dirty work, first create a backup and a few seed commits.
- Run `--apply` only on a clean working tree.

## Defaults
- Default base: `origin/main`
- Local `main` is the integration branch, not the primary truth source when it differs from `origin/main`
- In PowerShell, quote stash refs like `"stash@{0}"`

## Workflow
1. Inspect branch state, upstream, `git status`, and divergence from `origin/main`.
2. If the tree is dirty, create a backup branch and stash snapshot, then turn the work into a small number of seed commits.
3. Run the script in plan mode first and review the grouped messages and file lists.
4. Apply the grouped history onto a clean rewrite branch.
5. Move the working branch to the rewritten history and rebase onto `origin/main`.
6. Merge to local `main`, push, then clean `backup/`, `seed/`, `rewrite/`, and temporary stashes.

Read `references/feature-workflow.md` when the request involves dirty trees, backup branches, merge/push completion, or cleanup.

## Script usage
- Plan:
  - `python scripts/segment_commits.py --n 40`
  - `python scripts/segment_commits.py --base <base> --head <head>`
- Apply:
  - `python scripts/segment_commits.py --base <base> --head <head> --apply --target-branch <branch_name>`

## Output contract
`commit message: ...`

`commit files: ...`

## Validation
- Confirm scopes match the main directories or outcomes touched by each group.
- If grouping is wrong, narrow the range or rebuild seed commits.
- Before cleanup, confirm the cleaned diff matches the intended work and that push succeeded, unless the user wants local-only cleanup.

## Notes
- Existing CLI args remain compatible: `--base`, `--head`, `--n`, `--apply`, `--target-branch`, `--no-project-rules`, `--spec-file`.
- If the user asks only for planning, do not rewrite history, merge, or push.
- Do not delete release or milestone tags by default; only clean temporary recovery refs unless the user explicitly asks for broader cleanup.
