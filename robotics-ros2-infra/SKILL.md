---
name: robotics-ros2-infra
description: ROS 2 基础设施与通信层助手。当用户遇到话题收不到、消息丢帧、节点通信异常、回调阻塞、实时性不达标或需要做节点架构设计时使用，涵盖 QoS 配置与兼容性、DDS/RMW 选型与调优（Fast DDS / CycloneDDS）、生命周期节点、组件化与进程内通信、执行器与回调组、多机组网与 domain 边界、实时性配置。触发词示例：QoS、话题收不到、订阅不到消息、消息丢失、DDS、Fast DDS、CycloneDDS、RMW、ROS_DOMAIN_ID、多机通信、lifecycle 节点、生命周期、composition、组件化、intra-process、executor、回调组、callback group、回调阻塞、死锁、实时性、PREEMPT_RT、大消息传输慢。
license: LICENSE.txt
---

# ROS 2 Infrastructure

## Overview

Assist with ROS 2 middleware and node-architecture problems: QoS mismatches, DDS/RMW selection and tuning, lifecycle nodes, composition and intra-process communication, executors and callback groups, multi-machine discovery, and real-time configuration.

> **版本基准：Ubuntu 上的 ROS 2 Humble 二进制安装**。默认 RMW 和可用特性仍可能随平台/
> vendor 包变化。Humble 可用 `ROS_LOCALHOST_ONLY`；新版本更推荐
> `ROS_AUTOMATIC_DISCOVERY_RANGE` + `ROS_STATIC_PEERS`，但前者是逐步弃用而不是一概“已删除”。

## Workflow Decision Tree

- **话题明明在发但订阅不到** → Workflow A: QoS 兼容性（最高频问题）
- **能收但丢帧/延迟大/大消息卡** → Workflow B: DDS 调优
- **多机/跨网段收不到** → Workflow C: 发现与组网
- **回调不执行/卡死/服务调用死锁** → Workflow D: 执行器与回调组
- **要做节点架构**（启动顺序、减少复制、进程规划）→ Workflow E: 生命周期与组件化
- **控制环抖动、周期不稳** → Workflow F: 实时性

## Workflow A: QoS 兼容性

QoS 不兼容会阻止 endpoint 匹配。RMW、日志配置和客户端库可能提供 incompatible-QoS
事件或警告，也可能在应用层看起来像“没有数据”；不能把“绝对静默”当成协议行为。

```bash
ros2 topic info /scan --verbose    # 看每个 endpoint 的实际 QoS
```

兼容规则（**订阅者要求不能严于发布者**）：

| 维度 | 发布者 | 订阅者 | 结果 |
|---|---|---|---|
| Reliability | BEST_EFFORT | RELIABLE | ❌ **不连接** |
| Reliability | RELIABLE | BEST_EFFORT | ✅ 连接（降级） |
| Durability | VOLATILE | TRANSIENT_LOCAL | ❌ **不连接** |
| Durability | TRANSIENT_LOCAL | VOLATILE | ✅ 连接 |
| Deadline | 周期长 | 要求周期短 | ❌ 不连接 |
| Liveliness | AUTOMATIC | MANUAL_BY_TOPIC | ❌ 不连接 |

实践规则：

- **传感器数据**（激光、图像、IMU、点云）常以
  `rclcpp::SensorDataQoS()` / `rclpy` 的 `qos_profile_sensor_data`
  （BEST_EFFORT + KEEP_LAST(5)）为起点，适合“新鲜度优先于补发”的链路；估计器、记录或
  安全功能若不能容忍丢样本，必须按其数据契约、网络预算与故障行为另行选择并测试。
- **需要历史样本的状态**可用 TRANSIENT_LOCAL。订阅者也必须请求兼容的 durability 才能取得加入前的样本；`/map` 的实际 publisher/subscriber QoS 用 endpoint 信息核对。`/tf_static` 使用 tf2 定义的专用 QoS，不要泛化到所有“静态数据”。
- **命令类**（`/cmd_vel`、目标点）常用 RELIABLE + 浅 depth，但可靠送达不等于命令新鲜。
  控制链应带时间戳/序号、command timeout 或显式 action 状态，并验证断连与重连；depth 也由
  “只保留最新值”还是“每条命令都要处理”的语义决定。
- **按数据语义选择 QoS**：endpoint introspection 用于诊断，不应盲目复制“第一个发布者”的 QoS；同一 topic 可能有多个不同 endpoint。

## Workflow B: DDS 调优

### RMW 选型

| RMW | 强项 | 弱项 |
|---|---|---|
| `rmw_fastrtps_cpp`（Humble 默认） | 生态默认、共享内存传输成熟 | 大量节点时发现开销大 |
| `rmw_cyclonedds_cpp` | 配置模型简洁，常用于资源受限或多机部署 | 与目标平台/消息负载的性能仍需基准测试 |

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

不同 DDS vendor 以互操作为目标，但并非所有特性、版本和配置组合都保证互通。受支持部署优先统一
RMW vendor/版本；混用时做端到端 discovery、QoS、service/action 和大消息测试，不能直接断言必然不通信。

### 大消息（点云/图像）传输慢

按性价比顺序：

1. **同机减少序列化**：评估组件化 + intra-process（见 Workflow E）。是否真正无拷贝取决于发布所有权、订阅拓扑和 RMW；一对多场景可能仍需复制。
2. **评估共享内存传输**：Fast DDS 在支持的平台和默认 participant 配置中通常启用 SHM；
   用实际 endpoint/日志与基准确认，XML profile、容器 IPC、权限或版本可能改变结果。
3. **调 socket 缓冲**（跨机大消息丢包的常见根因）：

```bash
# 仅作字段示例；数值必须由消息大小、并发流和主机内存预算计算
sudo sysctl -w net.core.rmem_max=8388608 net.core.rmem_default=8388608
```

4. **压缩或降采样**：图像用 `compressed`，点云做体素降采样后再发。
5. **控制与感知做资源隔离**：可分进程、CPU、回调组、网卡/流量等级并限制大消息。仍需直接通信的节点必须在同一 DDS domain；不同 domain 默认互不可见，除非部署显式 bridge/router。

### 配置文件入口

```bash
export FASTRTPS_DEFAULT_PROFILES_FILE=/path/to/fastdds_profile.xml   # Fast DDS
export CYCLONEDDS_URI=file:///path/to/cyclonedds.xml                 # CycloneDDS
```

## Workflow C: 发现与组网

```bash
export ROS_DOMAIN_ID=42        # 同 domain 才直接发现；可用范围受系统端口规划影响
export ROS_LOCALHOST_ONLY=1    # Humble 可用；新发行版先查 discovery-range 文档
```

排查顺序：

1. `ros2 node list` 两边都能看到对方？看不到 = 发现层问题，不是 QoS 问题。
2. `ROS_DOMAIN_ID` 两边一致？
3. RMW vendor/版本是否属于已验证的同构或互操作组合？
4. 防火墙放开 UDP（DDS 用多播发现 + 单播数据）；容器要 `--net=host` 或正确映射。
5. 多播不可用（很多企业网/WiFi AP 隔离）→ 配 DDS 静态 peer 列表（Fast DDS 的 initialPeersList / CycloneDDS 的 `<Peers>`）。
6. 机器人 WiFi 场景：多播在弱网下极不可靠，**优先配静态 peer**。

## Workflow D: 执行器与回调组

**最经典的死锁**：在回调里同步等一个服务返回（`spin_until_future_complete`），而该服务由**同一个** SingleThreadedExecutor 处理 → 永久卡死。

规则：

- 默认 `SingleThreadedExecutor`：所有回调串行。一个慢回调会饿死其他所有回调（包括定时器）。
- `MultiThreadedExecutor` + 回调组才有并行：
  - `MutuallyExclusive`（默认）：组内串行，组间可并行。
  - `Reentrant`：组内也可并行 —— 共享状态必须自己加锁。
- **服务调用不要放在回调里同步等**。优先用异步回调链。若设计上必须等待，需要
  `MultiThreadedExecutor` **并且**把等待方与完成回调放入可并行的不同回调组（或使用经验证的
  专用线程方案）；只建一个独立 callback group 不能让 `SingleThreadedExecutor` 并行。
- 控制回路的定时器可放入独立回调组，但只有 executor 线程、CPU 调度、锁与资源也允许并行时
  才能隔离感知回调；callback group 本身不是实时性保证。

诊断：回调不执行时先确认「是不是被同 executor 的慢回调堵住了」，把可疑回调里加时间戳日志，看是没被调用还是执行太久。

## Workflow E: 生命周期与组件化

### Lifecycle 节点

状态机：`unconfigured → inactive → active → finalized`

```bash
ros2 lifecycle nodes                       # 列出所有 lifecycle 节点
ros2 lifecycle get /my_node
ros2 lifecycle set /my_node configure      # 再 activate
```

- 通常在 `on_configure()` 申请资源、在 `on_activate()` 启动任务数据流，但这是节点实现必须遵守
  的契约，不是状态机自动替你完成的行为。
- `LifecyclePublisher` 未激活时会阻止发布；普通 publisher/timer 不会因节点进入 `inactive` 自动停，
  实现必须显式 gate、cancel 或停用它们。
- Nav2 的 lifecycle manager 只编排其 `node_names` 中支持 lifecycle 的服务器；manager 本身和
  图中的辅助节点不能笼统称为 lifecycle 节点。调试时核对受管列表和各自状态。
- Lifecycle 提供启动/停机的编排契约，不是硬件就绪证明。转换回调还应验证设备通信、状态有效性、
  失败转移和端到端健康条件。

### 组件化（Composition）

```bash
ros2 run rclcpp_components component_container_mt        # 多线程容器
ros2 component load /ComponentManager my_pkg my_pkg::MyNode
```

- 同一进程内的组件可启用 intra-process，减少序列化和复制；收益必须用目标拓扑测量。
- `unique_ptr`/ownership-aware publish 有利于转移所有权，但一个 publisher 对多个订阅者时至少某些分支可能复制。
- 跨进程也可能使用共享内存或 loaned message；不能用“组件一定数量级更快”替代 profiling。
- 代价：一个组件崩溃会影响整个容器。按故障域、恢复策略、数据复制成本和风险分析决定进程边界；
  safety-rated 功能还需独立的合规架构，不能仅凭“拆进程”获得安全完整性。

## Workflow F: 实时性

- PREEMPT_RT 可降低 Linux 调度延迟，但内核、驱动、内存、锁、executor 和应用 WCET 都属于实时性证据；它本身不提供硬实时或功能安全保证。
- `chrt -f` 需要权限，错误的高优先级线程可能饿死系统和安全监控。先在隔离测试环境测 WCET/deadline miss，再由系统级调度方案设置优先级与 CPU affinity。
- 在**实时关键路径**中避免动态内存分配、阻塞 IO 和磁盘日志，并按量测结果预分配缓冲；非实时
  诊断回调无需机械套用这一禁令。
- `mlockall()` 只有在 memlock 权限/限额足够且调用成功时才锁页；还要预触碰栈/堆并监测
  page fault 与分配失败，不能把一行调用当作实时性证明。
- 对高频或低抖动闭环，先测总线、驱动和 ROS 路径的 WCET/抖动；超过预算的环路应下沉到具备确定性接口的驱动器/实时控制器，而不是用固定频率划线。
- 交换 ROS 时间戳、TF 或定时契约的节点必须使用一致时钟域；仿真链路中混用 wall time 与
  `/clock` 会产生 age/外推错误。

## 快速诊断表

| 现象 | 最可能根因 | 一条命令确认 |
|---|---|---|
| 订阅不到但话题在发 | QoS 不兼容（RELIABLE vs BEST_EFFORT / VOLATILE vs TRANSIENT_LOCAL） | `ros2 topic info <topic> --verbose` |
| late-join 后收不到 `/map` | publisher 未 active/未发布、durability 不兼容，或 TRANSIENT_LOCAL 历史缓存已不存在 | 查 map server lifecycle、publisher endpoint QoS 与当前缓存/重启行为 |
| 两台机器互相看不到节点 | DOMAIN_ID、发现范围、多播/peer、防火墙或未验证的 RMW 组合 | 对照两端环境并抓发现流量 |
| 回调不执行 | 被同 executor 的慢回调阻塞 | 回调入口加时间戳日志 |
| 服务调用卡死 | 回调内同步等服务 + 单线程执行器 | 看是否 `spin_until_future_complete` 在回调里 |
| 节点进程存在但无数据 | lifecycle 未 active，或实现未启动数据源 | `ros2 lifecycle get /<node>` 并检查设备/定时器 |
| 点云跨机延迟秒级 | 分片、丢包重传、带宽或消费者处理不足 | 量测网络与端点队列；压缩/降采样，或把必须共享大消息的流水线共置后只跨机发送结果 |
| 控制输出到达抖动 | 发布/传输/调度/消费者任一环节抖动 | `ros2 topic hz` 只能看观察端到达间隔；用 tracing、控制环 telemetry 和 deadline miss 定位 |

## 安全、测试与部署边界

- 多机/浏览器暴露前评估 SROS2、证书轮换、网络分区、最小权限与桥接器白名单；DDS domain 不是安全边界。
- 用 rosbag2 录制可复现输入，结合 tracing/metrics 检查 deadline、callback latency 和丢包。
- lifecycle “active”只证明状态转换完成，不证明传感器、执行器或任务链路端到端可用。
- launch 测试、systemd/容器启动、健康检查和回滚见 `references/testing_deployment.md`。
- QoS/DDS 详细诊断和互操作边界见 `references/qos_dds.md`。

## 配套脚本

- `scripts/check_topic_health.py` — 用 monotonic 时长测频率、抖动和可观测 stamp 性质；QoS 由参数显式选择
- `scripts/check_tf_tree.py` — TF 根、父子环、连通性、期望链路与动态变换时效检查

脚本输出是诊断证据，不是因果证明；运行前先 source 目标 ROS 2 环境。Agent 必须把
`<skill-root>` 解析为**当前这份 `SKILL.md` 所在目录的绝对路径**；不要假定用户 shell 的 cwd
就是技能目录，也不要虚构跨客户端通用环境变量。用法：

```bash
ROS_INFRA_SKILL_ROOT=<skill-root>
python3 "$ROS_INFRA_SKILL_ROOT/scripts/check_topic_health.py" /scan --expect-hz 10 --duration 5
python3 "$ROS_INFRA_SKILL_ROOT/scripts/check_topic_health.py" /map --transient-local --duration 2
python3 "$ROS_INFRA_SKILL_ROOT/scripts/check_tf_tree.py" --chain map odom base_link laser
```

参考：

- [ROS 2 Humble QoS](https://docs.ros.org/en/humble/Concepts/Intermediate/About-Quality-of-Service-Settings.html)
- [DDS vendor 互操作边界](https://docs.ros.org/en/humble/Concepts/Intermediate/About-Different-Middleware-Vendors.html)
- [ROS domain ID](https://docs.ros.org/en/humble/Concepts/Intermediate/About-Domain-ID.html)

## 按需扩展与复用边界

- 仅在明确相关的机器人任务中使用本技能；通用代码/网页/文案工作不加载机器人参考资料。
- 按当前故障读取单个参考文件，不预读整个知识库。脚本路径相对技能目录，运行时解析成绝对路径。
- 新架构、算法替换或明显重复实现前，使用可用的在线搜索核验论文及作者代码；若已安装可选的 `robotics-research-discovery`，可按需读取。小修复不强制联网。无网明确声明未核验，不能声称最新或无现成实现。
- 本模块的补充检查见 `references/review_addendum.md`，仅在涉及其中问题时读取。
