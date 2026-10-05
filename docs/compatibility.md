# 跨 Agent 兼容与上下文边界

## 分层承诺

1. **文件可移植**：SKILL.md + references/assets/scripts，无强制 MCP、插件或 Agent 私有 API。每个技能可独立复制；新增脚本仅依赖 Python 标准库。旧有部分工具需要 PyYAML，完整开发验证还需 requirements-dev.txt。
2. **原生发现**：由客户端负责扫描技能路径与按需读取；路径适配不等于在所有版本中完成实测。
3. **通用降级**：能读本地 Markdown 的 coding agent 可通过生成的 ROUTER.md 使用技能，但是否自动发现取决于其规则机制；仅会聊天、不能读文件/运行脚本的客户端不能保证同等功能。
4. **联网能力**：有浏览工具则优先用浏览工具；有 shell+网络+Python 则可用检索脚本；两者都没有只能离线工作，不能宣称最新。

## 项目级安装目标

| agent 参数 | 默认技能路径 | 接入性质 |
|---|---|---|
| agents / codex | .agents/skills | 标准共享目录 / Codex 文档路径 |
| opencode | .opencode/skills | OpenCode 项目路径 |
| antigravity | .agents/skills | 共享路径；目标版本须核验 |
| claude | .claude/skills | Claude Code 项目路径 |
| cursor | .cursor/skills | Cursor 项目路径；旧版本须核验 |
| copilot | .github/skills | 支持技能的 Copilot 环境；不代表所有 Copilot 模式 |
| generic | robotics-knowledge/skills | 文件可读降级，不自动注入规则 |

各目标额外生成 `.robotics-skills/<agent>/ROUTER.md` 和 `installed.json`（内容 hash）。
未知客户端用 `--destination` 指定项目相对路径。安装器拒绝越界路径、目标符号链接/目录联接和覆盖不同内容。

## 不支持原生技能时

不要把全部技能正文粘到系统提示。由用户在客户端**项目规则**中加入一个短路由，例如：

> 仅当任务明确涉及本项目机器人开发时，读取 `.robotics-skills/generic/ROUTER.md`，选择最相关的一个技能，再按需读取参考。其他任务不读取机器人知识。工具或网络不可用时说明限制。

安装器不自动修改 AGENTS.md、CLAUDE.md、GEMINI.md 或其它已有规则，避免覆盖/重复注入。
规则文件名字和匹配范围必须按目标客户端文档配置。这是手动一次性接入，不承诺所有客户端“零配置自动发现”。

## 上下文与可用性验收

- 项目安装隔离的是工作区；同项目中的通用任务仍需要描述边界和负例测试。
- 安装完整 24 技能会带来 24 个名称/描述的发现成本；并不等于读取全部正文。
- generic 模式只常驻短路由，相关任务再读取 catalog。原生模式不要叠加同一份完整 catalog。
- 离线测试只能验证路径、脚本与格式；路由质量、工具权限、模型选择和真实上下文增量需在客户端观测。
- `tests/routing_cases.json` 是行为验收集，不是已经跑过所有 Agent 的证据。记录客户端版本、模型、命中技能、读取文件、token 和偏离情况。

## 官方核验入口

- https://agentskills.io/specification
- https://developers.openai.com/codex/skills/
- https://opencode.ai/docs/skills/
- https://antigravity.google/docs/skills
- https://code.claude.com/docs/en/skills
- https://cursor.com/docs/context/skills
- https://docs.github.com/en/copilot/concepts/agents/about-agent-skills

网络可达性和页面标记检查见 source-audit.json；可达并不意味着完整技术审计，未抓取的页面必须在安装前另行核验。
