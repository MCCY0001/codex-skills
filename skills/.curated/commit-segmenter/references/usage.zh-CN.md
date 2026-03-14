# 使用卡片
仅当用户询问如何使用该 skill 时加载此文件。

- 先把 `<skill-root>` 解析为已安装的 `commit-segmenter` 目录，再执行命令。
- 先确认动作：
  - 清理当前功能分支
  - 发布已清理分支
- 前提：
  - 保持在功能分支上，不能是 `main`
  - 当前分支应基于 `origin/main`
- 命令：
  - 清理：`python <skill-root>/scripts/finish_workflow.py`
  - 发布：`python <skill-root>/scripts/publish_workflow.py`
  - 预览但不改动：追加 `--dry-run`
  - 改用其他基线：追加 `--base <ref>`
- 行为：
  - `finish`：先 `fetch`，必要时快照 dirty worktree，再重写成干净的 Conventional Commits
  - `publish`：先 `fetch`，将 `main` fast-forward 到 `origin/main`，再 fast-forward 到已清理分支，最后推送 `main`
- Prompt 模板：
  - `Use $commit-segmenter to clean the current feature branch.`
  - `Use $commit-segmenter to publish the cleaned branch.`
