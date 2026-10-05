---
name: robotics-nav2
description: ROS 2 Nav2 导航栈开发助手。当用户搭建或调试移动机器人自主导航时使用，涵盖 Nav2 bringup 与生命周期管理、costmap 分层配置、planner/controller 插件选型（NavFn/Smac/DWB/RPP/MPPI）、AMCL 定位调参、恢复行为与 Behavior Tree 定制、导航失败归因排查。触发词示例：Nav2、导航、路径规划、costmap、代价地图、膨胀层、AMCL、定位丢失、机器人绕圈、planner、controller、DWB、MPPI、recovery、behavior tree、bt_navigator、机器人撞障碍、导航目标失败。
license: LICENSE.txt
---

# Robotics Nav2

## Overview

Assist with ROS 2 Nav2 development: bringing up the navigation stack, configuring layered costmaps, choosing planner/controller plugins, tuning AMCL localization, customizing behavior trees, and diagnosing navigation failures from symptom to root cause.

> **版本基准：ROS 2 Humble / Nav2 humble 分支**。Nav2 参数与回补功能跨发行版、包版本变动较大，
> 本技能中的参数名核对自
> `nav2_bringup` 的 **humble 分支** `nav2_params.yaml`。用其他发行版前先跑
> `ros2 param list /controller_server` 核对；即使同为 Humble，也要检查目标系统实际安装的插件包。
> 已知跨版本差异见下方「跨版本陷阱」。

## Workflow Decision Tree

- **从零搭 Nav2**（有地图有定位，要跑起来）→ Workflow A: Bring-up
- **能跑但路径不对/撞障碍/绕圈** → Workflow B: Costmap 与插件调参
- **定位飘/丢失/位姿跳变** → Workflow C: AMCL 定位
- **要改导航逻辑**（自定义恢复、多目标、任务流）→ Workflow D: Behavior Tree
- **动不了/报错/goal 被拒** → Workflow E: 失败归因（`references/nav2_failures.md`）

## Workflow A: Bring-up

标准静态地图 + AMCL 导航的前置条件（SLAM 模式、无 static layer 或自定义 odom-only
拓扑不一定需要 `map_server`/`map→odom`，应按实际导航契约裁剪）：

1. **TF 完整且唯一**：`map → odom → base_link → <sensor>`。`map→odom` 只能由选定的定位节点发布，`odom→base_link` 由里程计链路发布。可用 `tf2_tools` 检查；安装整套技能包时也可调用 `robotics-ros2-infra` 的 TF 体检工作流。
2. **地图服务**：`map_server` 已加载 yaml/pgm 且完成 lifecycle 激活。
3. **传感器话题**：frame_id 与 URDF 一致，实测频率、时延、视场和量程满足 costmap 更新率、最大速度与停止距离预算。
4. **机器人尺寸**：`robot_radius`（圆形近似）或 `footprint`（多边形）二选一，别同时配。

启动与生命周期：

```bash
# 从零启动标准静态地图 + AMCL + navigation servers
ros2 launch nav2_bringup bringup_launch.py \
  map:=/absolute/path/map.yaml use_sim_time:=false autostart:=true \
  params_file:=./nav2_params.yaml

# 仅启动 navigation servers；map_server/AMCL 或 SLAM 定位链必须已经 active
ros2 launch nav2_bringup navigation_launch.py \
  use_sim_time:=false autostart:=true params_file:=./nav2_params.yaml

# 检查 lifecycle_manager 的 node_names 中受管的服务器
ros2 lifecycle get /controller_server        # 应为 active
```

手动排查 lifecycle 时才关闭自动启动。以下是上面自动启动命令的**替代方案**，不是再启动第二套
同名节点；先用 `autostart:=false` 启动，等服务就绪后在另一终端调用 STARTUP：

```bash
ros2 launch nav2_bringup navigation_launch.py \
  use_sim_time:=false autostart:=false params_file:=./nav2_params.yaml
ros2 service call /lifecycle_manager_navigation/manage_nodes nav2_msgs/srv/ManageLifecycleNodes "{command: 0}"  # 0=STARTUP
```

**常见 bring-up 失败**：某个节点 configure/activate 失败时，受管节点可能处于**混合状态**。
例如 configure 中途失败时，前面的节点可能已是 `inactive`，失败节点可能仍为 `unconfigured`
或进入错误状态，后续节点尚为 `unconfigured`；activate 中途失败时，前面的节点可能已
`active`。按 `lifecycle_manager` 的 `node_names` 逐个执行 `ros2 lifecycle get`，并从日志中的
第一个 transition 失败处排查，不能只看最后一个节点或假定所有节点同一状态。

## Workflow B: Costmap 与插件

### Costmap 分层

| 层 | plugin | 作用 | 关键参数 |
|---|---|---|---|
| static_layer | `nav2_costmap_2d::StaticLayer` | 载入静态地图 | global 常用；local 可按任务启用 |
| obstacle_layer | `nav2_costmap_2d::ObstacleLayer` | 2D 激光标记/清除障碍 | `observation_sources`、`marking`、`clearing` |
| voxel_layer | `nav2_costmap_2d::VoxelLayer` | 维护 3D 体素观测并投影到 2D costmap | 同上 + `min_obstacle_height`/`max_obstacle_height` |
| inflation_layer | `nav2_costmap_2d::InflationLayer` | 障碍外扩代价梯度 | `inflation_radius`、`cost_scaling_factor` |

`plugins` 顺序决定各层的更新顺序，但不能概括成“后一层总会覆盖前一层”；合并行为由
各层实现决定。通常让 inflation 在所有产生障碍代价的层之后运行，使这些障碍都获得代价梯度。

机器人内接半径以内由 footprint 碰撞和 lethal/inscribed cost 处理；`inflation_radius`
控制其外的附加代价范围，不应简单等同于“机器人半径 + 固定余量”。根据定位误差、控制误差、
制动距离和所需间隙确定。`cost_scaling_factor` 越大，代价随距离衰减越快；调整后必须检查
规划路径的实际碰撞余量。

### local / global costmap 分工

- **global**：常见组合是 `static_layer + obstacle_layer + inflation_layer`，frame 用 `map`；
  `track_unknown_space` 根据地图是否保留 unknown 及 planner 策略选择，不固定开启。
- **local**：通常 `rolling_window: true`，frame 用 `odom`，窗口尺寸按制动距离和传感器范围确定。是否加入 static layer 取决于是否需要局部窗口继承静态/保留区信息，不设绝对禁令。

完整 Humble 示例和插件合并边界见 `references/costmap_and_plugins.md`。

### Planner 选型

| 场景 | plugin | 说明 |
|---|---|---|
| 差速/全向，2D 栅格，够用就好 | `nav2_navfn_planner/NavfnPlanner` | Dijkstra/A\*（`use_astar`），默认，快 |
| 需要 cost-aware 的 2D A* | `nav2_smac_planner/SmacPlanner2D` | 只在 x/y 栅格搜索，不施加朝向或转弯曲率约束 |
| 阿克曼/需运动学可行路径 | `nav2_smac_planner/SmacPlannerHybrid` | 在 SE2 搜索并使用运动模型/转弯半径；按车辆运动学验收 |

**关键**：`tolerance`、`allow_unknown` 等是具体 planner 插件的参数，不是 global costmap
通用参数。探索是否允许进入未知区还要与地图语义、行为树和安全策略一致。

### Controller 选型

不要用“ROS 2 Humble / Nav2 1.1.x”这个大版本标签推断 MPPI 必然存在；目标机先执行
`ros2 pkg prefix nav2_mppi_controller` 并核对已安装包/源码分支。命令失败时不要填写
`nav2_mppi_controller::MPPIController`，应选择本机已有 controller，或安装并验证与当前
Nav2 ABI 匹配的包。

| 场景 | plugin | 说明 |
|---|---|---|
| 通用差速，成熟稳定 | `dwb_core::DWBLocalPlanner` | DWB，critic 可插拔，调参项多 |
| 高保真路径跟随、较少主动偏离 | `nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController` | RPP 跟随给定路径，可按前向碰撞检查减速/停，但不替代动态局部绕障；先验证路径可跟踪性与运动学 |
| 需要采样优化与约束代价 | `nav2_mppi_controller::MPPIController` | MPPI，最坏计算时间和目标硬件负载需实测 |

DWB 的行为由速度采样、仿真时域和 critic 共同决定。蛇形摆动时录制候选轨迹/critic 分数，
同时检查速度/加速度限幅、controller 频率、路径采样和 odom；不要固定归因给某一个权重。
不敢过窄门时先确认真实 footprint、costmap 代价和运动学可行性，再区分 planner 与 controller。

## Workflow C: AMCL 定位

```yaml
amcl:
  ros__parameters:
    robot_model_type: "nav2_amcl::DifferentialMotionModel"   # Humble 写法（旧版是 "differential"）
    laser_model_type: "likelihood_field"
    min_particles: 500
    max_particles: 2000
    update_min_d: 0.25        # 移动多少米才更新
    update_min_a: 0.2         # 转多少弧度才更新
    alpha1: 0.2               # 里程计旋转噪声 → 旋转
    alpha2: 0.2               # 里程计平移噪声 → 旋转
    alpha3: 0.2               # 里程计平移噪声 → 平移
    alpha4: 0.2               # 里程计旋转噪声 → 平移
    alpha5: 0.2               # 仅 omni 模型用
    base_frame_id: "base_footprint"
    global_frame_id: "map"
    odom_frame_id: "odom"
```

调参逻辑：

- **位姿收敛慢/初期乱跳** → 先给可信初始位姿，检查 scan/TF、地图和运动模型。`max_particles`
  只是 KLD 自适应粒子数上限；应结合覆盖范围、`min_particles`、`pf_err`、`pf_z` 和目标 CPU
  录包基准联合调整，单独调高不保证更快收敛。
- **走直线还行、转弯就飘** → `alpha1`/`alpha2` 调大（承认旋转里程计更不可信）。
- **位姿突然跳变** → 先检查地图质量、scan/TF 时间、激光模型、初始位姿与 odom；确认是粒子模型问题后，才依据录包调整 `alpha*`、粒子数和重采样参数。
- **`base_frame_id` 写错** → AMCL/TF 通常会产生 transform 错误日志；对照实际 URDF 和 `ros2 node info /amcl` 排查，不能称为静默失败。

## Workflow D: Behavior Tree

- BT XML 在 `bt_navigator` 的 `default_nav_to_pose_bt_xml` 指定；不改也能跑（有默认树）。
- 自定义节点要编译成 plugin 并加进 `plugin_lib_names` 列表，**漏加会在运行时报找不到节点**。
- 恢复/行为插件在 `behavior_server` 的 `behavior_plugins`；可用名称与默认集合以目标 Nav2
  发行版的 `nav2_params.yaml` 为准。
- 改 BT 前先确认 action terminal status、首个 planner/controller/BT 错误日志并对齐 costmap
  录包。Humble 的 `NavigateToPose` result 是 `std_msgs/msg/Empty`，不能从中读取 Nav2 error
  code；较新发行版只有在 action 接口和 BT 配置确实支持时才能使用细分错误码。

### 运行安全与约束

- `nav2_collision_monitor`、速度限制区、keepout filter 和 velocity smoother 是可选的运行约束层，
  但不是安全认证组件；是否使用及配置由机器人风险分析决定。依赖其中某个包时先用
  `ros2 pkg prefix <package>` 检查目标 Humble 安装，不能把后续发行版或回补包当作基础安装能力。
- footprint 必须覆盖实体和不可忽略的载荷，不能为了过窄门把 footprint 改得比机器人更小。
- 浏览器/无线 teleop、Nav2 cancel 和软件 stop 不能替代独立硬件安全链路。

## 跨版本陷阱

| 参数 | Humble | 更新版本 |
|---|---|---|
| `progress_checker_plugin` | **单数**（字符串） | Iron 起使用 `progress_checker_plugins`（列表）；其他版本仍以对应发行版文档为准 |
| `goal_checker_plugins` | **复数**（列表） | 同 |
| `robot_model_type` | `"nav2_amcl::DifferentialMotionModel"` | Galactic 及更早使用 `"differential"` / `"omnidirectional"` |
| `NavigateToPose` result | `std_msgs/msg/Empty`；只能结合 goal terminal status 与首个 server/BT 日志归因 | Iron 起的接口与 BT 链加入细分错误码；按目标 action 定义核对 |

抄博客配置最容易在这三项翻车。**照抄前先 `ros2 param list`**。

## References

- `references/nav2_failures.md` — 导航失败现象 → 归因 → 处理（含 goal 被拒、绕圈、撞障碍、原地抖动）
- `references/costmap_and_plugins.md` — costmap 分层完整配置与 planner/controller 参数对照

参数与插件入口：

- [Nav2 配置指南](https://docs.nav2.org/configuration/index.html)
- [Humble `nav2_params.yaml`](https://github.com/ros-navigation/navigation2/blob/humble/nav2_bringup/params/nav2_params.yaml)

## 按需扩展与复用边界

- 仅在明确相关的机器人任务中使用本技能；通用代码/网页/文案工作不加载机器人参考资料。
- 按当前故障读取单个参考文件，不预读整个知识库。脚本路径相对技能目录，运行时解析成绝对路径。
- 新架构、算法替换或明显重复实现前，使用可用的在线搜索核验论文及作者代码；若已安装可选的 `robotics-research-discovery`，可按需读取。小修复不强制联网。无网明确声明未核验，不能声称最新或无现成实现。
- 本模块的补充检查见 `references/review_addendum.md`，仅在涉及其中问题时读取。
