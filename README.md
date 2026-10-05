# robotics-skills

面向机器人 SLAM、激光/RGB 建图、VLN、目标跟随和系统集成的可移植 Agent Skills。

## 完整扩展版

当前提供 **24 个独立技能**：保留 14 个既有技能，补齐 10 个专项模块。既有可执行 ROS 示例仍以 **ROS 2 Humble** 为基线，而不是自动升级到最新发行版；新增工作流优先采用版本显式的接口契约。

- 默认项目级启用，不修改全局配置或用户已有规则。
- SKILL.md 只承载工作流；详细工程知识按需读 references，检查工具放在技能自己的 scripts 中。
- 新方案选型/大规模自研前检索论文和作者代码；普通修复不强制联网。
- 工具和模板可复用，但不伪造你的个人项目经验。将真实经验填入 [案例模板](docs/experience-case.template.md)。
- 不覆盖功能安全认证、真实硬件验收或所有机器人子领域；不宣称所有 Agent 客户端均已实测。
- 仓库不包含 Codex/Claude 插件 manifest，交付单位仍是独立技能及项目级安装适配。

### 模块索引

| 模块 | 主要职责 |
|---|---|
| [robotics-3d-perception](robotics-3d-perception/SKILL.md) | 点云契约、过滤、配准与 3D 评估 |
| [robotics-benchmarking](robotics-benchmarking/SKILL.md) | 实验设计、执行、统计和回归门禁 |
| [robotics-calibration-sync](robotics-calibration-sync/SKILL.md) | 内外参、时钟偏移/漂移与验证 |
| [robotics-data-replay](robotics-data-replay/SKILL.md) | 录包、数据谱系、时间戳审计与回放 |
| [robotics-edge-deployment](robotics-edge-deployment/SKILL.md) | 模型部署、性能、watchdog 和回滚 |
| [robotics-force-control](robotics-force-control/SKILL.md) | 力传感、接触控制与分阶段验证 |
| [robotics-frontend](robotics-frontend/SKILL.md) | 机器人 Web 可视化、桥接和 teleop 边界 |
| [robotics-hand-eye-calibration](robotics-hand-eye-calibration/SKILL.md) | 手眼标定、可观性和独立验证 |
| [robotics-legged-wbc](robotics-legged-wbc/SKILL.md) | 足式状态、接触、任务约束和 WBC |
| [robotics-lidar-odometry](robotics-lidar-odometry/SKILL.md) | LiDAR-IMU、去畸变与退化 |
| [robotics-localization-fusion](robotics-localization-fusion/SKILL.md) | 轮速/IMU/GNSS 融合与重定位 |
| [robotics-manipulation](robotics-manipulation/SKILL.md) | MoveIt、规划场景、轨迹执行 |
| [robotics-map-management](robotics-map-management/SKILL.md) | 稠密/语义/占据地图、多会话与版本 |
| [robotics-motion-control](robotics-motion-control/SKILL.md) | ros2_control、PID 和执行链 |
| [robotics-nav2](robotics-nav2/SKILL.md) | 路径规划、costmap、控制器和故障归因 |
| [robotics-research-discovery](robotics-research-discovery/SKILL.md) | 联网论文/开源检索、证据与复用决策 |
| [robotics-research-reproduction](robotics-research-reproduction/SKILL.md) | 论文复现、来源、环境和基线 |
| [robotics-ros2-infra](robotics-ros2-infra/SKILL.md) | TF、QoS、时钟与 ROS 运行基础 |
| [robotics-sim2real](robotics-sim2real/SKILL.md) | 动力学、域差异、策略部署契约 |
| [robotics-slam](robotics-slam/SKILL.md) | SLAM 选型、闭环、漂移与导航接入 |
| [robotics-target-following](robotics-target-following/SKILL.md) | 身份关联、跟随目标、丢失和重获 |
| [robotics-vision-perception](robotics-vision-perception/SKILL.md) | 相机输入契约、推理与视觉评测 |
| [robotics-visual-slam](robotics-visual-slam/SKILL.md) | 单目、双目、RGB-D、VIO 与尺度 |
| [robotics-vln](robotics-vln/SKILL.md) | 视觉语言 grounding、导航与评测 |

## 如何使用：安装到你的机器人项目

**本仓库是知识和工具的来源；`--project` 指向你实际开发机器人的代码仓库。**
不是把整个仓库放进系统提示，也不需要先部署 MCP 服务。

### 1. 准备源码与环境

需要 Python 3.10+ 和 Git。安装器、联网检索及新增离线工具只依赖 Python 标准库；运行原有工程工具或完整测试时，再安装 `requirements-dev.txt`。

```bash
git clone https://github.com/bernardleex526/robotics-skills.git
cd robotics-skills
python --version
```

已有本仓库时直接进入现有目录，不要重复 clone。Linux/macOS 若只有 `python3`，将后文的 `python` 替换成 `python3`。

### 2. 选择 Agent，安装完整 24 个技能

目标项目必须已经存在。以下从**本知识仓库根目录**运行，并将路径替换成真实机器人项目：

```powershell
# Windows + OpenCode：先预览，不写文件
python tools/install_skills.py --project "E:\robots\my-project" --agent opencode --profile all
# 确认 destination、skills 和 conflicts 后实际安装
python tools/install_skills.py --project "E:\robots\my-project" --agent opencode --profile all --apply
```

Linux/macOS 示例：

```bash
python tools/install_skills.py --project /home/you/robots/my-project --agent opencode --profile all
python tools/install_skills.py --project /home/you/robots/my-project --agent opencode --profile all --apply
```

按客户端替换 `--agent`：

| 使用环境 | 参数 | 安装器写入的项目相对目录 |
|---|---|---|
| OpenCode | `opencode` | `.opencode/skills` |
| Antigravity（agy） | `antigravity` | `.agents/skills` |
| Codex | `codex` | `.agents/skills` |
| Claude Code | `claude` | `.claude/skills` |
| Cursor | `cursor` | `.cursor/skills` |
| 支持 Agent Skills 的 Copilot 环境 | `copilot` | `.github/skills` |
| 使用共享目录的客户端 | `agents` | `.agents/skills` |
| 其他可读取本地文件的 Agent | `generic` | `robotics-knowledge/skills` |

Antigravity 的完整安装示例：

```powershell
python tools/install_skills.py --project "E:\robots\my-project" --agent antigravity --profile all --apply
```

成功时返回 `status: installed`。除技能文件外，项目内还会生成：

```text
.robotics-skills/<agent>/ROUTER.md       # 按需路由索引
.robotics-skills/<agent>/installed.json  # 安装清单和源文件 hash
```

安装器不修改全局配置、现有规则，也不自动运行机器人控制命令。
以上是安装器的目标映射，不代表已经逐个实测所有客户端版本，详见 [跨 Agent 兼容](docs/compatibility.md)。
不要为同一个客户端在多个发现目录重复安装同名技能；共用 `.agents/skills` 的客户端可复用同一份文件。

### 3. 在机器人项目里正常对话

**在 Agent 中打开目标机器人项目，而不是只打开这个技能仓库。**安装后新建会话；如果技能列表未刷新，再重新打开项目/客户端，不承诺所有客户端热加载。

原生技能模式下通常无需反复指定技能名称。直接描述问题，并给出必要的项目证据：

> FAST-LIO 在转弯时墙面重影。请先检查本项目点时间字段、IMU 时间和外参方向，再决定是否调参数；不要直接控制机器人。

> 我想把 RGB-D 地图用于重定位和导航。请区分需要保存的地图产物，检查当前代码缺哪些接口。

> 机器人跟随目标被遮挡后会追错人。请检查检测、身份关联、丢失状态和目标重获门控。

> 准备做 VLN。先检索近期论文、作者开源代码和成熟基线，给出复用或改造方案，再决定是否自研。

Agent 应先选一个最相关的技能，再只读取需要的参考；不要要求“先读完全部技能”。普通登录页、通用 C++ 工具或文案修改不应加载机器人参考资料。

### 4. 验证技能是否真正生效

先用一次诊断请求：

> 请列出当前项目可发现的 robotics 技能及来源路径，不要加载全部正文。然后针对“LIO 转弯重影”，只读取最相关的一个技能，告诉我实际读取了哪个文件。

检查客户端工具记录中的真实文件读取，不只相信模型说“已加载”。再用负例检查边界：

> 只修改登录页按钮样式，不涉及机器人功能，不读取机器人知识文件。

未自动发现时，核对项目根目录、目标目录、技能开关/权限、客户端版本和重复安装。
也可明确要求 Agent 读取 `.opencode/skills/robotics-lidar-odometry/SKILL.md`（以 OpenCode 安装为例）。
手动读文件成功不等于自动发现已经验收，其他客户端应使用对应的真实路径。

### 5. 其他 Agent 的通用接入

```bash
python tools/install_skills.py --project /path/to/robot-project --agent generic --profile all --apply
```

然后由你在该客户端的**项目规则**中加入一次短路由；安装器不会擅自修改规则：

> 仅当任务明确涉及本项目机器人开发时，读取 `.robotics-skills/generic/ROUTER.md`，选择最相关的一个技能，再按需读取参考。其他任务不读取机器人知识。工具或网络不可用时说明限制。

规则文件名按客户端配置。没有文件读取能力的 Agent 无法采用此方式；不能执行脚本的客户端仍可使用知识文本，但检查工具需要你手动运行。
无需为了兼容而粘贴全部知识或部署额外 MCP。

### 6. 安装范围与个人经验

完整版本使用 `--profile all`。只有希望缩小项目发现范围时，才使用可选配置：

```bash
# SLAM 主线：预览，写入时加 --apply
python tools/install_skills.py --project /path/to/robot-project --agent opencode --profile slam
# VLN / 跟随主线
python tools/install_skills.py --project /path/to/robot-project --agent opencode --profile embodied
# 精确选择；--skills 优先于 --profile
python tools/install_skills.py --project /path/to/robot-project --agent opencode --skills robotics-vln robotics-research-discovery
```

已安装其他配置的目标可能产生清单冲突，按下方更新流程处理。
完整安装仍有 24 个名称/描述的发现成本，不是零 token；正文和参考按需读取，项目级安装避免影响其他工作区。

个人经验从 [案例模板](docs/experience-case.template.md) 开始，写清平台/版本、症状、证据、根因、修改及验证条件。
在相关技能中增加按需索引；私有 bag、现场图像、地图、密钥保留在项目本地，不提交到公开仓库。

### 7. 更新、冲突与卸载

本工具采用复制安装，**更新本知识仓库不会自动更新机器人项目中的副本**。

1. 在干净的本仓库中执行 `git pull --ff-only`。有个人修改时先保存/提交，不使用强制 reset。
2. 重跑不带 `--apply` 的安装命令。相同内容重复安装是幂等的；不同内容会报告 `conflict` 并拒绝覆盖。
3. 有冲突时，在另一个临时项目中安装新版本，比较 `installed.json` 和目标实际文件，保留个人修改。
4. 审核后，在项目版本控制/备份保护下，手动替换确认为本包管理的技能文件与对应安装记录，再验证。
   没有 `--force`、自动合并或自动卸载；不要整体删除 `.agents`、`.opencode` 等可能存放其他配置的目录。
5. 卸载时按清单识别本次安装的技能，确认是否被其他客户端共享、是否有个人修改，再移除相应文件；generic 模式还需移除手动添加的那段路由。安装器不自动删除。

### 常见问题

| 现象 | 处理 |
|---|---|
| `project must be an existing directory` | 指定实际存在的机器人项目，不要照抄示例路径 |
| `dry_run` 但没有技能文件 | 这是预览；确认后加 `--apply` |
| `conflict` / 拒绝覆盖 | 保留现有文件，按更新流程比较迁移；没有强制覆盖开关 |
| Agent 没识别技能 | 核对打开的项目、目标目录、权限/版本和会话刷新，再用明确文件路径诊断 |
| 脚本缺少依赖 | 核对 Python 环境；旧工程工具可安装 `requirements-dev.txt` |
| 联网超时、403 或限流 | 查看每个来源的 error；用原生浏览工具、稍后重试或显式离线，不把失败当零命中 |
| 普通任务仍读机器人文件 | 排查全局安装/长规则，用负例复测；必要时缩小安装范围或隔离工作区 |

## 联网查论文和开源实现

可以直接要求 Agent：“先查近期论文和官方开源实现，比较后再决定是否自研”。
也可手动运行以下命令。命令从**本知识仓库根目录**执行；使用已安装副本时，改为该技能的实际脚本路径。

```bash
# 近期结果：强制重新联网，不将 TTL 内缓存当成最新
python robotics-research-discovery/scripts/search_robotics.py --query "lidar inertial odometry" --days 365 --limit 10 --cache-dir .research-cache --refresh --output research-result.json
# 相同查询、窗口和排序的离线缓存；保留原 fetched_at
python robotics-research-discovery/scripts/search_robotics.py --query "lidar inertial odometry" --days 365 --limit 10 --cache-dir .research-cache --offline
# 不限制首次提交日期，补查成熟基线
python robotics-research-discovery/scripts/search_robotics.py --query "visual language navigation" --limit 10 --refresh
# 补查旧论文的新修订；不加 --days，避免排除首次提交较早的论文
python robotics-research-discovery/scripts/search_robotics.py --query "visual language navigation" --paper-sort updated --limit 10 --refresh
```

`research-result.json` 必须尚不存在；再次保存时换一个输出文件名，或不传 `--output` 直接查看终端 JSON。
脚本用 arXiv 和 GitHub 公共 API，只做有界候选发现，不自动证明作者身份、许可证适用性或代码可运行。
GitHub 可通过环境变量 `GITHUB_TOKEN` 提高配额；不要把 token 写进技能、查询或 Git 仓库，不向搜索服务发送私有信息。

读取结果时检查：

- `fetched_at`：原始获取时间，不把旧缓存说成今日新检索。
- `cache_hit` / `offline`：是否使用缓存及离线模式。
- `sources.arxiv` / `sources.github`：各来源是否成功、候选条目、错误和不完整标记。
- 退出 0：两源请求成功，可以零命中；退出 1：部分或全部来源失败；退出 2：输入/文件错误。都不代表候选已经可用。

Agent 应继续阅读论文和作者代码，用 [复用决策模板](robotics-research-discovery/assets/reuse_decision.template.json) 比较许可、接口、维护、实验条件与移植成本，形成 reuse/adapt/implement/defer 结论。未找到不等于不存在。


### 离线验证

```bash
python robotics-data-replay/scripts/audit_timestamps.py robotics-data-replay/assets/timestamps.example.csv
python robotics-target-following/scripts/check_follow_trace.py robotics-target-following/assets/trace.example.json
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools/check_repository.py
python tools/check_engineering_skills.py
python tools/check_doc_params.py
python tools/check_portability.py
```

新增工具的 JSON 和退出码在各技能参考中定义；它们不冒充旧有八个工程技能的统一结果 schema。
默认测试不联网、不控制硬件。真实 API smoke 与客户端行为验收必须单独记录，不能由结构测试代替。

- [升级审查与验收记录](docs/upgrade-review.md)
- [自动验证结果](docs/verification-results.json)
- [真实联网 smoke 记录](docs/research-live-smoke.json)
- [触发行为验收用例](tests/routing_cases.json)
- [旧版详细运行指南](docs/legacy-guide.md)
- [已有工程模块验证说明](docs/engineering-expansion-verification.md)

源码：`git clone https://github.com/bernardleex526/robotics-skills.git`
