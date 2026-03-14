# Usage Card
Load this file only when the user asks how to use the skill.

- Resolve `<skill-root>` to the installed `commit-segmenter` directory before running any command.
- Ask for one action:
  - clean the current feature branch
  - publish the cleaned branch
- Preconditions:
  - stay on a feature branch, not `main`
  - use a branch based on `origin/main`
- Commands:
  - clean: `python <skill-root>/scripts/finish_workflow.py`
  - publish: `python <skill-root>/scripts/publish_workflow.py`
  - preview without changes: add `--dry-run`
  - alternate base: add `--base <ref>`
- Behavior:
  - `finish`: fetch, snapshot dirty work if needed, rewrite into cleaned Conventional Commits
  - `publish`: fetch, fast-forward `main` to `origin/main`, fast-forward `main` to the cleaned branch, push `main`
- Prompt templates:
  - `Use $commit-segmenter to clean the current feature branch.`
  - `Use $commit-segmenter to publish the cleaned branch.`
