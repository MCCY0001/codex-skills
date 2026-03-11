# Feature Branch Finish Workflow

Load this file only when the request includes dirty worktrees, checkpoint commits, rebase onto `origin/main`, merge to `main`, push, or cleanup.

## Temporary names

- `backup/<branch>-<timestamp>`
- `seed/<branch>-<timestamp>`
- `rewrite/<branch>-<timestamp>`
- stash message: `safety-snapshot-<branch>-<timestamp>`

## Mode A: Dirty working tree

1. `git fetch origin`
2. Record the branch name and compare it with `origin/main`.
3. Create a backup branch from current `HEAD`.
4. Create a stash snapshot with untracked files.
5. Create a seed branch from `origin/main`.
6. Re-apply the stash snapshot on the seed branch.
7. Normalize staged and unstaged state if needed so each seed commit captures final file content.
8. Create a few seed commits grouped by outcome, then continue with the shared finish steps below.

## Mode B: Existing checkpoint commits

1. `git fetch origin`
2. Inspect `origin/main..HEAD`.
3. If the tree is dirty, stash it or convert it into seed commits first.
4. Continue with the shared finish steps below.

## Shared finish steps

1. Run `commit-segmenter` plan mode on the selected range.
2. Review the messages and file lists.
3. Run `--apply` onto a clean rewrite branch.
4. Move the working branch to the rewritten history.
5. Rebase onto `origin/main`.
6. Merge to local `main`.
7. Push.
8. After remote sync succeeds, delete temporary branches and clear the safety stash.

## Rules

- Default base: `origin/main`
- Never run `--apply` on a dirty working tree
- If there are no commits in range, the work is probably still only in the working tree; create seed commits first
- Prefer a few human-reviewable seed commits over one giant snapshot commit
- If repo policy does not allow direct push to `main`, stop at the cleaned feature branch or local merge point

## Failure points

- PowerShell stash refs:
  `git stash apply --index "stash@{0}"`
- No upstream:
  compare directly against `origin/main`
- Push failure:
  keep local cleaned history and postpone cleanup
- Cleanup:
  do not delete temporary refs until the cleaned history is safely attached where the user wants it
