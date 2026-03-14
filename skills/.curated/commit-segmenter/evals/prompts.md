# commit-segmenter evals

## Should trigger

- Clean the current feature branch into Conventional Commits and publish it if everything looks good.
- I have checkpoint commits and a dirty feature branch. Segment and clean it up against `origin/main`.
- Use `commit-segmenter` to finish my branch workflow before I open a PR.
- Rewrite this mixed feature-branch history into cleaned Conventional Commits.
- Dry-run the branch cleanup first so I can inspect the grouped commits.

## Should not trigger

- Show the latest commits on this branch.
- Create a new feature branch from `origin/main`.
- Rebase my current branch and resolve conflicts manually.
- Walk me through a merge conflict after an interactive rebase.
- Just show the git log and summarize what changed.

## Task samples

### Success path

- Run `finish_workflow.py` on a feature branch with checkpoint commits and verify it leaves a clean Conventional Commits history.

### Failure path

- Attempt the workflow on a non-feature branch and verify the skill stops with a recovery-oriented explanation.
