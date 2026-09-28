# Agent Workbench

个人 Agent 开发工作台，目前维护可复用的 Codex 技能及其校验、分发和安装工具。

当前技能：[tech-doc-driven-development](skills/tech-doc-driven-development/SKILL.md)，用于技术路线、分阶段实现计划和实施证据记录。

## 目录

```text
skills/<name>/          技能源码
skills/.curated/        自动导出的安装副本
scripts/skill_repo.py   统一命令入口
.github/workflows/     CI 校验与发布检查
AGENTS.md              开发约定
```

只修改源码，再导出安装副本；运行时安装目录独立于仓库。

## 快速开始

在 WSL 仓库根目录执行，使用 Python 3.10+，无需第三方依赖：

```bash
python3 scripts/skill_repo.py list
python3 scripts/skill_repo.py validate --check-export-drift
```

Windows 可使用 `python`；也可通过 `uv run python` 执行同一入口。

## 修改与分发

编辑 `skills/<name>/` 后，导出并检查：

```bash
python3 scripts/skill_repo.py export --catalog curated --delete-stale
python3 scripts/skill_repo.py validate --check-export-drift
```

将源码和导出副本一起提交。PR 和 main 推送会自动校验；`v*` tag 会触发发布检查。
发布前可执行 `python3 scripts/skill_repo.py release-check --ref main`；正式分发时将 `main` 替换为实际发布 tag。

## 安装到本机

在 WSL 中显式指定目标，先预览，再去掉 `--what-if` 安装：

```bash
python3 scripts/skill_repo.py publish tech-doc-driven-development \
  --runtime-path /home/caden/.codex/skills --what-if
```

安装到本机 Windows 时，将目标改为 `/mnt/c/Users/mccy0/.codex/skills`。
其他机器请替换为自己的路径。更新仓库不会自动更新已安装技能。

默认覆盖前会备份；`--no-clobber` 禁止覆盖，`--force` 跳过备份。
未指定目标时使用 `$CODEX_HOME/skills`，未设置该变量则使用 `~/.codex/skills`。
安装后在新会话中验证技能发现和实际调用。

更多参数：`python3 scripts/skill_repo.py --help`。开发规则见 [AGENTS.md](AGENTS.md)。
