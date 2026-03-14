# Recovery
Load this file only when a workflow fails.

- Re-run with `--dry-run` first when the user wants to inspect the next attempt without changing history.
- `finish_workflow.py` may leave:
  - `refs/codex-safety/<branch>/head-<timestamp>`
  - `codex/finish/<branch>/<timestamp>`
  - a printed stash revision when dirty work was snapshotted
- restore the original feature branch:
  - `git branch -f <feature-branch> <safety-ref>`
  - `git switch <feature-branch>`
- inspect the rewritten scratch state:
  - `git switch <scratch-branch>`
- re-apply a printed stash revision in PowerShell:
  - `git stash apply --index "stash@{0}"`
- `publish_workflow.py` prints the pre-merge `main` SHA instead of creating extra refs.
