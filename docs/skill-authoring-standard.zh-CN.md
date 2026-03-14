# Skill 编写与开发规范

状态：已采纳  
生效范围：本仓库 `skills/` 下所有新增和修改的 skill  
基线日期：2026-03-13

本规范基于 2026-03-13 前可公开访问的 OpenAI、Anthropic、Google 官方资料，以及 Agent Skills 开放标准整理而成。后续在本仓库开发 skill，默认都以此文档为准；如目标运行时存在更严格限制，以运行时限制优先。

## 1. 官方定义与共识

| 来源 | 官方对 skill 的定义或等价概念 | 对本仓库的直接约束 |
| --- | --- | --- |
| OpenAI | Skill 是把指令、文件和可选脚本打包在一起的模块化能力；采用渐进式加载，只有相关时才把更多内容放进上下文。 | skill 必须单一职责；`description` 必须准确描述触发条件；默认先写指令，只有在确定性或复用要求高时再加脚本。 |
| Anthropic | Skill 通过 `SKILL.md` 扩展 Claude 的专门能力；frontmatter 决定何时使用，正文提供工作指令，支持配套文件按需加载。 | `SKILL.md` 只保留执行工作流；参考资料和样例必须外置并在正文里明确何时读取；过大的 skill 应拆分。 |
| Google | ADK Skill 是“自包含的功能单元”，由指令、资源和工具组成；采用三级增量加载：元数据、指令、资源。 | skill 设计必须围绕“元数据可发现、正文可执行、资源按需加载”；不要做大而全的万能 skill。 |

补充说明：

- OpenAI 与 Anthropic 已明确采用 Agent Skills 开放标准。
- Google 官方文档里同时使用 `skill`、`agent config`、`tools`、`sub-agent` 等概念；在本规范里统一把“可复用、可触发、带说明和资源的能力包”视为 skill。

## 2. 本仓库的统一标准

### 2.1 目录与边界

每个 skill 的源码必须放在 `skills/<skill-name>/` 下，推荐结构如下：

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

源码约束如下：

- `SKILL.md` 是必需项，也是行为规范的唯一事实源。
- `agents/openai.yaml` 是推荐项，用于 Codex UI 元数据、依赖和调用策略，不得替代 `SKILL.md` 的核心说明。
- `references/` 只放按需加载的参考资料。
- `scripts/` 只放需要确定性执行或高复用的脚本。
- `assets/` 只放输出会用到的模板、素材、样板文件，不放说明文档。
- `evals/` 是本仓库强烈推荐扩展，用于保存触发评估和回归样例；本仓库内置 skill 应提供最小 `evals/prompts.md`。
- skill 目录内不得新增 `README.md`、`CHANGELOG.md`、`INSTALLATION_GUIDE.md`、`QUICK_REFERENCE.md` 一类辅助文档。

说明：

- 本仓库的源码布局固定为 `skills/<skill-name>/...`。
- 如果需要让仓库对 `skill-installer` 更易发现，可额外维护导出的 catalog，例如 `skills/.curated/<skill-name>/` 或 `skills/.experimental/<skill-name>/`。
- `skills/.curated/` 和 `skills/.experimental/` 不是源码目录，而是面向安装器的导出目录；默认应由脚本从 `skills/<skill-name>/` 生成，而不是手工维护。
- 真正发布到不同运行时时，目录名可以由发布流程映射到目标位置；不要在源码仓库中混入 `.agents/skills/`、`.claude/skills/` 之类运行时专用目录。

### 2.2 命名与 frontmatter

`SKILL.md` 顶部 frontmatter 默认只保留 `name` 和 `description`：

```yaml
---
name: "skill-name"
description: "Use when ... Do not use when ..."
---
```

规则如下：

- `name` 必须与目录名完全一致。
- `name` 只能使用小写字母、数字和连字符，建议不超过 64 个字符。
- `description` 必须同时说明“什么时候该用”与“什么时候不该用”。
- `description` 必须使用用户意图语言，而不是实现语言。
- `description` 必须覆盖常见触发表述、任务边界和排除条件。
- 未确认目标运行时支持前，不要擅自增加额外 frontmatter 字段。

推荐写法：

- `Use when the user needs ...`
- `Do not use when the task is ...`

不推荐写法：

- `Helpful for many repository tasks`
- `Handles automation`
- 只写技术实现，不写触发条件

### 2.3 `SKILL.md` 正文

`SKILL.md` 正文只保留执行所需的最小信息，通常应控制在 500 行以内，并显著低于 5k 词。

正文必须满足：

- 先写默认工作流，再写例外情况和失败恢复。
- 使用祈使句和可执行指令，不写大段背景介绍。
- 明确前置条件、输入、输出、成功判定和失败处理。
- 如果有副作用、破坏性操作或高风险操作，必须在正文里显式写出保护条件。
- 所有可选参考资料都要写成“何时读取某文件”的形式。
- 只保留真正会影响执行决策的信息；背景知识、长样例、FAQ 一律移入 `references/`。

推荐结构：

```md
# Skill Name

Default flow:
- ...
- ...

Decision rules:
- ...
- ...

Load `references/...` only when ...
Run `scripts/...` when ...
```

### 2.4 渐进式加载

所有 skill 都必须遵守“元数据 -> 正文 -> 资源”的三层加载原则：

1. 元数据只负责让模型知道这个 skill 是否相关。
2. `SKILL.md` 正文只负责指导执行。
3. `references/`、`scripts/`、`assets/` 只在需要时加载或执行。

具体要求：

- 不要把参考资料全文复制进 `SKILL.md`。
- 不要让 `references/` 再深层引用更多文档；原则上只允许从 `SKILL.md` 直接发现。
- 超过 100 行的参考文件应该带目录，便于快速定位。
- 同一条信息只能有一个权威位置；正文与参考资料不得重复维护。

### 2.5 何时写脚本，何时只写指令

默认先写指令，只有在以下场景才新增脚本：

- 同一段逻辑已经被反复手写两次以上。
- 任务对确定性要求高，纯提示词容易漂移。
- 需要稳定处理文件格式、API、解析或批量操作。
- 需要把复杂实现从上下文中剥离，降低 token 成本。

脚本必须满足：

- 可非交互运行。
- 有清晰的退出码。
- `--help` 或等效帮助可用。
- stdout 只输出结果，stderr 输出诊断。
- 使用相对路径或显式参数，不依赖隐式当前目录。
- 对危险操作提供 dry-run、预检查或显式保护。
- 错误信息必须可操作，能够指导修复。

Python 脚本推荐：

- 优先 `uv`。
- 能用内联依赖时优先内联依赖。
- 依赖说明放在 `openai.yaml` 或脚本头部，不要在 skill 目录再写安装说明文档。

### 2.6 `references/` 与 `assets/`

`references/` 规则：

- 只放模型可能需要阅读的资料。
- 文件名要表达主题或语言，例如 `usage.md`、`usage.zh-CN.md`、`api.md`。
- 如果有多语言版本，正文中必须说明按用户语言选择读取。
- 只保留会影响决策的信息，不要堆积“资料库”。

`assets/` 规则：

- 只放输出资源，例如模板、样板代码、图标、示例文件。
- 不要把解释性文档放进 `assets/`。

### 2.7 `agents/openai.yaml`

当 skill 需要在 Codex UI 中可发现、需要声明依赖，或需要设置调用策略时，应维护 `agents/openai.yaml`。

规则如下：

- `SKILL.md` 更新后，必须确认 `agents/openai.yaml` 没有过期。
- `openai.yaml` 只承载界面元数据、依赖和策略，不承载核心流程。
- 如果某 skill 只能显式调用，不应允许默认隐式触发。

## 3. 开发流程

新增或大改一个 skill，按以下顺序执行：

1. 收集真实用例，至少整理一组“应该触发”和“一组不该触发”的提示语。
2. 判断是扩展现有 skill，还是拆成新 skill；默认优先拆分，而不是把现有 skill 做成大杂烩。
3. 先写最小可用版 `SKILL.md`，只保留核心工作流。
4. 只有在必要时再增加 `references/`、`scripts/`、`assets/`、`openai.yaml`。
5. 为 skill 补充最小 `evals/prompts.md`，至少覆盖触发样例、非触发样例、一个成功路径和一个失败路径。
6. 如果需要被 `skill-installer` 统一列出或按 catalog 安装，再将源码 skill 导出到 `skills/.curated/` 或 `skills/.experimental/`。
7. 用真实提示语评估触发准确率、输出质量和失败恢复。
8. 使用 `uv run python scripts/skill_repo.py validate --check-export-drift` 做 repo 级校验。
9. 验证通过后再发布到运行时目录或推送可安装版本。

## 4. 评估与发布门槛

每个 skill 在发布前至少完成以下检查：

- 触发评估：至少 8 条应该触发的提示语，8 条不应触发的提示语。
- 输出评估：至少 3 条真实任务样例，覆盖默认路径、边界路径和失败路径。
- 回归评估：对已有 skill 的修改，必须重跑历史关键样例。
- 一致性检查：`SKILL.md`、`references/`、`scripts/`、`agents/openai.yaml` 之间不得相互矛盾。

满足以下条件才算完成：

- `name`、目录名和对外标识一致。
- `description` 能让模型正确判断是否使用该 skill。
- `SKILL.md` 足够短，但能独立指导执行。
- 参考资料都按需加载，没有重复信息。
- 脚本可直接运行，错误可诊断。
- 如存在 `agents/openai.yaml`，它与 `SKILL.md` 同步。

## 5. 推荐模板

最小模板：

```md
---
name: "skill-name"
description: "Use when the user needs ... Do not use when ..."
---

# Skill Name

Default flow:
- Step 1
- Step 2

Decision rules:
- Rule 1
- Rule 2

Load `references/...` only when ...
Run `scripts/...` when ...
```

复杂 skill 的最小扩展：

```text
skills/<skill-name>/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── domain.md
│   └── usage.zh-CN.md
├── scripts/
│   └── run_task.py
└── evals/
    └── prompts.md
```

## 6. 本仓库的默认取舍

如果没有特殊理由，统一采用以下默认值：

- 小 skill 优先，不做万能 skill。
- 指令优先，脚本次之。
- `SKILL.md` 精简优先，细节放 `references/`。
- `skills/<skill-name>/` 作为唯一源码；installer catalog 用导出目录承接。
- 源码仓库结构优先保持稳定，由发布脚本处理运行时差异。
- 先验证触发准确率，再追求说明完整度。

## 7. 参考来源

官方资料：

- OpenAI Academy: [Custom Skills](https://academy.openai.com/public/clubs/work-users-ynjqu/resources/custom-skills)
- OpenAI GitHub: [openai/skills](https://github.com/openai/skills)
- Anthropic Docs: [Extend Claude with skills](https://docs.anthropic.com/en/docs/claude-code/skills)
- Anthropic Docs: [Subagents](https://docs.anthropic.com/en/docs/claude-code/sub-agents)
- Anthropic Docs: [Slash commands](https://docs.anthropic.com/en/docs/claude-code/slash-commands)
- Google ADK Docs: [Skills](https://google.github.io/adk-docs/agents/skills/)
- Google ADK Docs: [Agent Config](https://google.github.io/adk-docs/agents/agent-config/)
- Google ADK Docs: [Function tools](https://google.github.io/adk-docs/tools/function-tools/)

开放标准：

- Agent Skills: [What are Agent Skills?](https://www.agentskills.io/introduction)
- Agent Skills: [Optimizing descriptions](https://www.agentskills.io/creating-skills/optimizing-descriptions)
- Agent Skills: [Using scripts](https://www.agentskills.io/creating-skills/using-scripts)
- Agent Skills: [Evaluating skills](https://www.agentskills.io/creating-skills/evaluating-skills)
