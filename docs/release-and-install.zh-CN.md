# Skill 发布与安装

基线日期：2026-03-14

本仓库的发布与安装分成三层：

- 源码层：`skills/<skill-name>/`
- 分发层：`skills/.curated/<skill-name>/`
- 运行时层：`$CODEX_HOME/skills` 或 `~/.codex/skills`

## 常用命令

列出源码 skill：

```bash
uv run python scripts/skill_repo.py list --catalog source --format names
```

如果你已经有一个可用的 Python 解释器，也可以继续用：

```powershell
python .\scripts\skill_repo.py list --catalog source --format names
```

发布到本地运行时：

```bash
uv run python scripts/skill_repo.py publish commit-segmenter
```

预览发布动作但不写入：

```bash
uv run python scripts/skill_repo.py publish commit-segmenter --what-if
```

禁止覆盖已有本地 skill：

```bash
uv run python scripts/skill_repo.py publish commit-segmenter --no-clobber
```

跳过备份直接覆盖：

```bash
uv run python scripts/skill_repo.py publish commit-segmenter --force
```

导出稳定 catalog：

```bash
uv run python scripts/skill_repo.py export --catalog curated --delete-stale
```

校验源码和 `.curated` 漂移：

```bash
uv run python scripts/skill_repo.py validate --check-export-drift
```

发布前总检查：

```bash
uv run python scripts/skill_repo.py release-check --ref v0.1.0
```

## 本地发布语义

默认是安全优先：

- 目标 skill 不存在：直接发布
- 目标 skill 已存在：先备份到 `~/.codex/skills/.backup/<skill-name>-<timestamp>`，再发布新版本
- `--no-clobber`：发现同名目标就失败
- `--force`：不备份，直接替换
- `--what-if`：只打印计划动作

Windows 下也可以继续用 PowerShell wrapper：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish_skills.ps1 commit-segmenter
```

## GitHub 安装

对外推荐始终从 `.curated` 安装，并尽量固定到 tag：

```powershell
python <CODEX_HOME>/skills/.system/skill-installer/scripts/install-skill-from-github.py `
  --repo <owner>/<repo> `
  --ref v0.1.0 `
  --path skills/.curated/commit-segmenter
```

列出仓库里可安装的 curated skills：

```powershell
python <CODEX_HOME>/skills/.system/skill-installer/scripts/list-skills.py `
  --repo <owner>/<repo> `
  --path skills/.curated
```

如果未设置 `CODEX_HOME`，把上面的 `<CODEX_HOME>/skills` 理解为 `~/.codex/skills`。

## 推荐发布流程

1. 在 `skills/<skill-name>/` 更新源码。
2. 用 `publish` 发布到本地 `.codex/skills` 做验证。
3. 用 `validate --check-export-drift` 确认结构和 catalog 一致性。
4. 用 `export --catalog curated --delete-stale` 更新 `.curated`。
5. 提交源码和 `.curated`。
6. 打 tag。
7. 用 `release-check --ref <tag>` 产出最终安装命令。
