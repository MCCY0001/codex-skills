# Agent Workbench

个人 Agent 开发工作台，用于维护可复用的技能，并逐步扩展工具、工作流、评测和开发脚本。
A personal workbench for agent development: reusable skills, tools, workflows, evaluations, and development scripts.

当前已实现的能力是 Codex skills 的开发、校验、分发与本地安装；其他能力将按实际需求逐步加入。

GitHub: https://github.com/MCCY0001/agent-workbench

## Repository Model

这个仓库采用三层模型，分别服务于开发、分发和运行时加载。

- 源码层 / Source: `skills/<skill-name>/`
- 分发层 / Distribution: `skills/.curated/<skill-name>/`
- 运行时层 / Runtime: `~/.codex/skills` or `$CODEX_HOME/skills`

原则：

- 只在 `skills/<skill-name>/` 里维护源码。
- `skills/.curated/` 只保存导出的安装镜像，不手工编辑。
- 本地个人 skills 通过发布流程同步到 `~/.codex/skills`。
- 不要把运行时的 `.system/` 目录放进这个仓库。

## Directory Responsibilities

- `skills/<skill-name>/`: 唯一源码目录，供日常开发、更新和验证 skill。
- `skills/.curated/<skill-name>/`: 导出的安装 catalog，供 GitHub 安装和列出可安装 skills。
- `scripts/`: 仓库级 CLI 和辅助脚本，例如 `skill_repo.py`、`publish_skills.ps1`。
- `docs/`: 规范、互操作和发布安装文档。
- `.github/workflows/`: 仓库 CI，负责结构校验和 release-check。
- `.vscode/`: 工作区级编辑器设置，固定 uv + `.venv` 开发体验。

## Quick Start

推荐把 `uv` 和 workspace 级 `.venv` 作为本地开发默认方式。

```bash
uv venv .venv
```

创建完成后，VS Code 会按工作区设置优先发现并使用该环境。仓库当前没有集中式 `pyproject.toml`；`.venv` 主要用于让编辑器、终端和 repo 工具链共享一个稳定解释器。

常用的跨平台命令统一写成：

```bash
uv run python scripts/skill_repo.py <subcommand> ...
```

Windows 下也可以继续使用 PowerShell wrapper：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish_skills.ps1 tech-doc-driven-development
```

## Common Commands

列出源码 skills / List source skills:

```bash
uv run python scripts/skill_repo.py list --catalog source --format names
```

预览本地发布 / Preview a local publish:

```bash
uv run python scripts/skill_repo.py publish tech-doc-driven-development --what-if
```

发布到本地运行时 / Publish to the local runtime:

```bash
uv run python scripts/skill_repo.py publish tech-doc-driven-development
```

校验源码和导出目录 / Validate source skills and curated export drift:

```bash
uv run python scripts/skill_repo.py validate --check-export-drift
```

导出安装 catalog / Export the installer catalog:

```bash
uv run python scripts/skill_repo.py export --catalog curated --delete-stale
```

发布前检查 / Run a release check:

```bash
uv run python scripts/skill_repo.py release-check --ref v0.1.0
```

Windows 便利入口 / Windows convenience entrypoint:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish_skills.ps1 tech-doc-driven-development -WhatIfPreview
```

## Add a New Skill

新增 skill 时，统一从源码层开始。

1. 在 `skills/<skill-name>/` 创建目录。
2. 至少添加 `SKILL.md`，并保证 frontmatter 的 `name` 与目录名一致。
3. 按需添加 `agents/`、`references/`、`scripts/`、`assets/`、`evals/`。
4. 先在源码目录完成迭代，再决定是否导出到 `skills/.curated/`。
5. 运行校验，再发布到本地运行时验证实际触发和使用体验。

推荐先看这些文档：

- [docs/skill-authoring-standard.zh-CN.md](docs/skill-authoring-standard.zh-CN.md)
- [docs/skill-repo-interop.zh-CN.md](docs/skill-repo-interop.zh-CN.md)
- [docs/release-and-install.zh-CN.md](docs/release-and-install.zh-CN.md)

最小 skill 结构：

```text
skills/<skill-name>/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
├── scripts/
├── assets/
└── evals/
```

## Apply Repo Skills Locally

如果你想把这个 repo 里的某个 skill 应用到本机 Codex，推荐走发布流程，而不是手工复制。

1. 先预览：

```bash
uv run python scripts/skill_repo.py publish tech-doc-driven-development --what-if
```

2. 确认无误后正式发布：

```bash
uv run python scripts/skill_repo.py publish tech-doc-driven-development
```

3. 发布目标默认是：

- `~/.codex/skills`
- 如果设置了 `CODEX_HOME`，则是 `$CODEX_HOME/skills`

4. 发布完成后，新开一个 Codex 会话，用显式调用先验证：

```text
使用 $tech-doc-driven-development 为需求编写技术路线和分阶段实现计划。
```

如果你主要在 Windows 上工作，也可以直接用：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish_skills.ps1 tech-doc-driven-development
```

## GitHub Distribution

如果你后续要把这个仓库托管到 GitHub，并让别的 Codex 实例安装技能，推荐额外维护 `.curated` 导出目录。

- 本地开发仍然只改 `skills/<skill-name>/`
- 分发前运行 `export --catalog curated --delete-stale`
- 把 `skills/.curated/` 一起提交到 GitHub
- 对外安装时优先使用 tag，而不是漂移的 `main`

CI 已覆盖两类检查：

- `.github/workflows/skill-repo-validate.yml`: PR 和 `main` push 时校验 skill 结构与 export drift
- `.github/workflows/skill-repo-release-check.yml`: tag push 时运行 `release-check`

## Notes

- 这个仓库是源码仓库，不是运行时目录。
- `.venv/` 应保持本地存在但不纳入版本控制。
- 如果本机 `python` 命中 WindowsApps stub，优先使用 `uv run python ...` 或 `scripts/publish_skills.ps1`。

## 当前维护的自有技能

- `tech-doc-driven-development`：技术路线、分阶段实现计划、单步实施与证据化回填。完整保留原技能的 4 个文件。
- `commit-segmenter` 已从当前源码和安装 catalog 退役；Git 历史保留。
- `wecom-unified` 是第三方技能，独立安装，不纳入本仓库。内置 `.system` 技能、插件和凭证也不纳入。

## Windows 与 WSL 双端更新

本机维护目录：`/home/caden/gitRepo/agent-workbench`。以后在此仓库 `skills/<name>/` 编辑；原内网 GitLab 仓库保持原样，本流程不会自动回写它。

修改后导出、校验并上传 GitHub：

```bash
cd /home/caden/gitRepo/agent-workbench
python3 scripts/skill_repo.py export --catalog curated --delete-stale
python3 scripts/skill_repo.py validate --check-export-drift
git add skills docs README.md
git commit -m "docs(skills): 更新技能"
git push origin main
```

从 GitHub 更新并同步安装（先确认工作树干净）：

```bash
cd /home/caden/gitRepo/agent-workbench
git pull --ff-only
python3 scripts/skill_repo.py validate --check-export-drift
python3 scripts/skill_repo.py publish --source-root skills/.curated --runtime-path /home/caden/.codex/skills
python3 scripts/skill_repo.py publish --source-root skills/.curated --runtime-path /mnt/c/Users/mccy0/.codex/skills
```

两个安装路径显式指定，不依赖可能指向 Windows 的 `CODEX_HOME`。发布脚本默认备份被替换的技能；只同步本仓库技能，不清空其他技能。此流程是手动更新，不是后台自动同步。安装后在下一轮对话核对技能发现；如未刷新，重开聊天。
