# Skill 仓库兼容改造说明

基线日期：2026-03-13

本文说明如何把本仓库改造成同时兼容以下两类工作流：

- `skill-creator`：适合创建和更新源码 skill
- `skill-installer`：适合从 GitHub 仓库导入 skill，并安装到本地 `.codex/skills`

## 目标

更通用的 skill 仓库应该同时满足这三件事：

1. 开发时只有一份源码，不出现多处手工维护。
2. 本地能一键发布到 `.codex/skills` 供 Codex 立即读取。
3. 远端 GitHub 仓库能被 `skill-installer` 安装，必要时还能列出可安装 skill。

## 推荐结构

推荐把仓库分成两层：

```text
skills/
├── <skill-name>/              # 源码，给 skill-creator / 日常维护使用
├── .curated/<skill-name>/     # 导出的安装 catalog，可选
└── .experimental/<skill-name>/# 导出的实验 catalog，可选
```

规则：

- `skills/<skill-name>/` 是唯一源码。
- `.curated/` 和 `.experimental/` 只做导出镜像，不手工编辑。
- 本地发布到 `.codex/skills` 时，默认从源码目录发布。
- 远端安装时，有两种路径：
  - 直接安装源码路径：`skills/<skill-name>`
  - 安装 catalog 路径：`skills/.curated/<skill-name>`

## 当前仓库已做的改造

### 1. `scripts/skill_repo.py` 成为统一入口

新的 CLI 统一承载以下子命令：

- `list`
- `publish`
- `export`
- `validate`
- `release-check`

其中 `publish` 默认具备安全语义：

- 默认发布到 `$CODEX_HOME/skills`；未设置时发布到 `~/.codex/skills`
- 已有同名 skill 时先备份到 `.backup/`
- 支持 `--what-if`、`--no-clobber`、`--force`

PowerShell 的 `publish_skills.ps1` 保留为 Windows wrapper，不再承载核心逻辑。

### 2. catalog 导出仍保留兼容脚本

`scripts/export_skill_catalog.py` 现在只是兼容 wrapper，真正逻辑由 `skill_repo.py export` 承载。

默认命令：

```bash
uv run python scripts/skill_repo.py export --catalog curated --delete-stale
```

默认效果：

- 从 `skills/<skill-name>/` 读取源码
- 导出到 `skills/.curated/<skill-name>/`
- 删除 catalog 里已不存在的旧 skill

只导出单个 skill：

```bash
uv run python scripts/skill_repo.py export commit-segmenter
```

导出到实验目录：

```powershell
uv run python scripts/skill_repo.py export commit-segmenter `
  --catalog experimental
```

### 3. CI 开始承接 repo 级校验

新增 GitHub Actions：

- PR / main push：`validate --check-export-drift`
- tag push：`release-check --ref <tag>`

这样 `.curated` 是否漂移、skill 结构是否有效，不再只靠人工检查。

### 4. 规范文档已补充源码与 catalog 的边界

统一规范见：

- [skill-authoring-standard.zh-CN.md](skill-authoring-standard.zh-CN.md)

核心原则：

- 源码只写在 `skills/<skill-name>/`
- catalog 通过脚本导出
- 不在 skill 目录里混入多套运行时专用结构

## `skill-creator` 和 `skill-installer` 分别怎么用

### 面向 `skill-creator`

创建或更新 skill 时，只操作源码目录：

```text
skills/<skill-name>/
```

要求：

- `SKILL.md` 必须存在
- `agents/openai.yaml` 按需维护
- `references/`、`scripts/`、`assets/` 按需增加

### 面向 `skill-installer`

远端安装有两种方式。

方式一：直接装源码路径。最简单，不需要 catalog。

```powershell
python <CODEX_HOME>/skills/.system/skill-installer/scripts/install-skill-from-github.py `
  --repo <owner>/<repo> `
  --path skills/commit-segmenter
```

方式二：装导出的 catalog 路径。更标准，也便于列出可安装 skill，也是默认推荐路径。

```powershell
python <CODEX_HOME>/skills/.system/skill-installer/scripts/install-skill-from-github.py `
  --repo <owner>/<repo> `
  --path skills/.curated/commit-segmenter
```

如果要列出仓库里可安装的 curated skills：

```powershell
python <CODEX_HOME>/skills/.system/skill-installer/scripts/list-skills.py `
  --repo <owner>/<repo> `
  --path skills/.curated
```

注意：

- 只有把 `.curated` 推到 GitHub 之后，上面的 listing 和 catalog 安装才会生效。
- 如果只是直接安装 `skills/<skill-name>`，那么即使没有 `.curated` 也能工作。

## 更通用的发布流程

推荐把仓库工作流固定成下面这样：

1. 在 `skills/<skill-name>/` 里开发和更新 skill。
2. 本地用 `skill_repo.py publish` 发布到 `.codex/skills` 做真实验证。
3. 用 `skill_repo.py validate --check-export-drift` 做 repo 级校验。
4. 验证通过后，运行 `skill_repo.py export` 生成 `.curated/` 或 `.experimental/`。
5. 提交源码和导出的 catalog。
6. 推送到 GitHub。
7. 对外安装时优先使用 tag，而不是漂移的 `main`。

tag 安装示例：

```powershell
python <CODEX_HOME>/skills/.system/skill-installer/scripts/install-skill-from-github.py `
  --repo <owner>/<repo> `
  --ref v0.1.0 `
  --path skills/.curated/commit-segmenter
```

## 为什么这是更通用的改法

相比把所有 skill 直接搬到 `.curated/`，现在这套方案更稳：

- 开发与分发分层，避免源码目录为安装器让步。
- `skill-creator` 继续面对简洁的源码树。
- `skill-installer` 既支持直接路径安装，也支持 catalog 安装。
- 本地发布、本地验证、远端安装都走清晰边界。
- 仓库可以逐步增加 `.experimental/`、版本 tag、CI 校验，而不破坏现有 skill。

## 对当前仓库的直接建议

如果你想让这个仓库立刻更通用，按下面做：

1. 继续把 `skills/<skill-name>/` 作为唯一源码。
2. 本地验证时执行：

```bash
uv run python scripts/skill_repo.py publish commit-segmenter
uv run python scripts/skill_repo.py validate --check-export-drift
```

3. 分发前执行：

```bash
uv run python scripts/skill_repo.py export --catalog curated --delete-stale
```

4. 把 `skills/.curated/` 一起提交到 GitHub。
5. 对外文档和示例命令优先写 `skills/.curated/<skill-name>`。
6. 对本地开发者仍保留 `publish_skills.ps1` 作为 Windows wrapper。

这样你同时兼容了：

- `skill-creator` 的源码维护方式
- `skill-installer` 的 GitHub 安装方式
- Codex 本地运行时的 `.codex/skills` 加载方式
- 只在源码仓库里维护个人编写的 skills
