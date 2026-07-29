# Nav2 导航失败归因

> 参数名核对自 `nav2_bringup` **humble 分支** 的 `nav2_params.yaml`。
> Humble 的 `NavigateToPose.action` result 是 `std_msgs/msg/Empty`。本版以 goal terminal
> status 与首个 server/BT 错误日志归因；planner/controller 错误码向 BT/action 结果的传播是
> Humble 之后加入的能力，不能照搬到 Humble。

## 归因顺序（按出现频率，从上到下查）

1. **TF 断了、重复发布或时间戳不对** → `tf2_tools`，或使用 `robotics-ros2-infra` 的 TF/话题体检工作流
2. **lifecycle 没全 active** → `ros2 lifecycle get /<node>`
3. **costmap 里根本没障碍或全是障碍** → RViz 看 `/global_costmap/costmap`
4. **机器人尺寸/膨胀半径配错** → `robot_radius` 与 `inflation_radius`
5. 最后才是 planner/controller 参数

## goal 相关

| 现象 | 根因 | 处理 |
|---|---|---|
| action 连接前/发送时被拒 | action server 未就绪、goal 格式/状态不允许或 BT navigator 未 active | 先查 lifecycle、action server 可用性与 goal response；不要把所有 rejected 都归因于障碍 |
| goal 已接受，随后规划失败/aborted | 目标或起点不可规划、planner 超时、TF/costmap 异常 | Humble 看 goal terminal status 与首个 planner/server/BT 错误日志；只在任务允许时调整 planner 插件的 `tolerance` / `allow_unknown` |
| `Failed to create global plan` | TF/超时、起终点越界或占据、unknown 策略、地图不连通等 | 先看 planner 的具体错误和起终点 cost；再核对 TF、地图边界、unknown 与连通性，不能见此日志就减 inflation |
| goal 接受但机器人不动 | controller 未 active，或 controller→smoother/collision monitor/mux→base 链路断裂 | 核对 lifecycle、完整 remap/subscriber 链与每一级输出；多个 publisher 会消息交错，只有显式 mux/锁才会仲裁 |
| 到点了不算到 | 跟踪/定位误差、速度未停稳、goal checker 选择或容差不匹配 | 对齐 desired/actual pose、速度与定位误差；只有任务验收和实际间隙允许时才调整 `xy_goal_tolerance` / `yaw_goal_tolerance` |

## 运动行为异常

| 现象 | 根因 | 处理 |
|---|---|---|
| 贴墙走甚至剐蹭 | footprint、定位/控制误差或代价梯度没有留下足够余量 | 先核对真实 footprint 与定位/跟踪误差，再联合调 inflation；用实测最小间隙验收 |
| 窄门/走廊完全无解 | footprint 确实过宽、inflation 软代价过宽，或 planner/controller 不满足运动学 | 可减小 `inflation_radius`；若要让软代价衰减更快则增大 `cost_scaling_factor`，并验证碰撞余量；绝不缩小真实 footprint |
| 蛇形摆动/画龙 | 速度/加速度限制、控制频率、路径采样、odom 延迟或 critic 组合不合适 | 录制候选轨迹/critic 分数并对齐 odom 与输出；一次只改一个有证据的参数，换 controller 也要重新验收 |
| 原地反复抖动不前进 | 幽灵障碍、controller critic/旋转行为、速度死区或 odom/TF 抖动 | 对齐 local costmap、controller debug 轨迹、实际/指令速度和 TF；按证据处理自体点、clearing、critic 或底盘死区 |
| 绕远路 / 不走明显捷径 | planner/代价权重、unknown 策略、地图拓扑或残留障碍 | 对比 global costmap 与规划器展开/路径代价；确认 clearing 后再按目标插件调代价，不能只凭路径形状归因 |
| 频繁触发 recovery（原地转圈） | planner、controller、TF 或 costmap 对应 BT 分支持续失败 | Humble 对齐 terminal status、触发 recovery 前的首个 server/BT 日志和 blackboard instrumentation；默认树有 contextual recovery，别用 recovery 次数代替根因 |
| 走着突然反向/掉头 | 定位修正、路径重规划或 controller 状态异常 | 对齐 action feedback、`map→odom`、AMCL 统计和局部规划输出；合法重定位也可能产生离散修正 |

## 幽灵障碍专项（最常见的"莫名不动"）

按顺序排除：

1. 激光扫到机器人自身（支架、天线）→ `laser_filters` 的 `LaserScanAngularBoundsFilter` 裁掉。
2. 地面反光、自身结构或低矮物体进入观测 → 先判定它是否是真实碰撞风险，再修 TF、传感器过滤或高度范围；不能为消除告警而忽略应避障的低矮物体。
3. 动态物体走了但代价没清 → `clearing: true`、`raytrace_max_range` ≥ `obstacle_max_range`。
4. TF 延迟导致点云投影错位 → 查 `/scan` 时间戳与 `transform_tolerance`。

## 日志速查

| 日志 | 含义 |
|---|---|
| `Timed out waiting for transform from base_link to map` | TF 缺失或 `transform_tolerance` 太小 |
| `Control loop missed its desired rate` | 控制回调 WCET、可视化/采样配置、CPU 争用或调度超过周期预算；先 profile，只有停止距离与闭环预算允许时才降频 |
| `Costmap2DROS transform timeout` | costmap 等不到 TF；同上 |
| `No valid control` / `Failed to compute a valid trajectory` | 碰撞、运动学/速度采样、critic（含 oscillation/goal）、TF 或无可用样本都可能使候选非法；结合 controller debug 输出归因 |
| `Behavior tree threw exception` | 保留完整异常与 backtrace；依次检查 BT XML、节点注册、ports/blackboard 类型与键、tick 中异常，以及 action/service 依赖，不能只归因于 `plugin_lib_names` |

## 验收清单

- [ ] 空旷环境点到点：路径平滑、无 recovery 触发
- [ ] 项目规定的最窄通道能通过，并记录实体最小间隙和定位/控制误差余量
- [ ] 动态障碍（人走过）能绕行且离开后代价恢复
- [ ] 覆盖规定时长和目标集合的巡航，无超出验收门槛的卡死、碰撞或定位丢失
- [ ] 经设备定义的安全停机后，按复位流程恢复且不会自动续跑旧 goal
