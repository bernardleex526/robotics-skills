---
name: robotics-motion-control
description: 机器人运动控制开发助手。当用户进行机器人关节/底盘运动控制开发时使用，涵盖 ros2_control 架构搭建与配置、PID 整定、轨迹规划（点到点/样条/MoveIt）、逆运动学求解、电机驱动调试与常见控制报错排查。触发词示例：运动控制、PID 整定、轨迹规划、逆运动学、ros2_control、controller_manager、关节抖动、电机不转、motion control、trajectory planning、inverse kinematics。
license: LICENSE.txt
---

# Robotics Motion Control

## Overview

Assist with robot motion-control development on ROS/ROS 2: setting up the `ros2_control` stack, tuning PID loops, choosing and executing trajectory-planning approaches, solving inverse kinematics, and debugging control failures from symptom to root cause.

> 版本基准：ROS 2 Humble。控制器参数、spawner 选项和插件可用性跨发行版变化；
> 使用其他版本时先查对应版本的 `ros2_control`/`ros2_controllers` 文档和本机 `--help`。

## Workflow Decision Tree

Identify the user's situation first, then follow the matching workflow:

- **从头搭建控制栈**（新机器人/新驱动）→ Workflow A: Controller Bring-up
- **控制效果差**（抖动、超调、跟踪不上、稳态误差）→ Workflow B: PID Tuning
- **需要规划运动**（机械臂点到点、底盘速度平滑、时间最优）→ Workflow C: Trajectory Planning
- **笛卡尔空间控制**（给定位姿求关节角）→ Workflow D: Inverse Kinematics
- **报错/不动作**（controller 起不来、电机无响应）→ Workflow E: Debugging，并查阅 `references/common_errors.md`

## Workflow A: Controller Bring-up (ros2_control)

1. 在 URDF/xacro 中声明 `<ros2_control>` 标签：定义每个 joint 的
   `command_interface`（position/velocity/effort）与 `state_interface`，选择 hardware plugin
   （`mock_components/GenericSystem` 用于无硬件验证）。Humble 自定义插件还必须完成硬件接口导出、
   pluginlib 宏与 plugin XML 注册，不能只实现 `read()` / `write()`。
2. 编写 controller 配置 YAML：`<controller>.type` 等加载信息属于
   `controller_manager`，`joints`/interfaces/constraints 等运行参数属于 controller 自身节点
   namespace。先加载 `joint_state_broadcaster`；轨迹执行用 `joint_trajectory_controller`，
   只想对 hardware interface 做最小烟测时可用 `forward_command_controller`，它从
   `~/commands` 接收 `std_msgs/msg/Float64MultiArray` 并直接前馈接口值，不执行轨迹。
3. 由 `robot_state_publisher` 发布 URDF，并把 controller manager 的
   `~/robot_description` remap 到 `/robot_description`；Humble 已弃用直接传
   `robot_description` 参数。启动顺序为 `controller_manager`（含 hardware）→
   `spawner joint_state_broadcaster` → `spawner <motion_controller>`。用
   `ros2 control list_controllers` 确认状态为 `active`。
4. 先用 `mock_components` 全流程验证，再切换真实硬件插件。

详细架构、硬件接口实现要点与完整 YAML 示例见 `references/ros2_control.md`。

## Workflow B: PID Tuning

1. **先判型**：区分是位置环、速度环还是电流/力矩环问题；内环未整定好之前不要整外环。
2. **整定顺序**：电流环（通常在驱动器内）→ 速度环 → 位置环。优先用厂家模型、系统辨识或有界闭环实验得到初值，再小步调整。
3. **防护**：先完成风险评估、输出限幅、anti-windup、微分滤波和独立停机链路；夹具、支撑方式与允许负载按机构风险选择，不能笼统地用“悬空”代替安全方案。
4. **验证指标**：按任务定义上升时间、超调、稳态误差、跟踪带宽、饱和占比与热稳定性；示例阈值不能替代项目验收标准。

模型不可得且风险可控时的手动法、临界比例度法及现象-原因对照表见
`references/pid_tuning.md`。

## Workflow C: Trajectory Planning

按需求选择方案：

| 需求 | 方案 |
|---|---|
| 关节空间点到点、带速度/加速度约束 | 五次多项式或梯形速度曲线；ROS 2 发 `trajectory_msgs/msg/JointTrajectory` 给 `joint_trajectory_controller` |
| 机械臂笛卡尔/避障规划 | MoveIt 2（OMPL 采样规划器 + 时间参数化）；先用 `moveit_py` 或 RViz MotionPlanning 插件验证 |
| 实时避障/反应式控制 | MPC、优化控制或反应式方法；频率由机器人动力学、感知延迟和最坏执行时间预算决定 |
| 底盘速度平滑 | 按任务限制速度及加/减速度，并按输出频率插值，参考 Nav2 velocity smoother；若另加低通滤波，需单独评估相位延迟与停止距离 |

要点：轨迹采样间隔应与控制器更新率、插值方式和网络抖动匹配；发送前确认
`constraints.goal_time` 与 `constraints.stopped_velocity_tolerance` 符合任务验收标准。

## Workflow D: Inverse Kinematics

- **解析解可选**：机构和约束允许时，IKFast 或经过验证的几何解延迟低且便于枚举分支；仍需做关节限位、奇异位形与碰撞检查。
- **数值解**：TRAC-IK、KDL 的 `ChainIkSolverPos_LMA` 或 MoveIt 2 插件各有适用范围；用本机器人的可达率、耗时分位数和解连续性比较，不能只靠通用排名选型。
- **常见坑**：seed 初值离解太远导致不收敛 → 用当前关节角作 seed；多解分支跳变 → 加解空间连续性约束或选对当前构型最近的解。

## Workflow E: Debugging

快速定位清单（按出现频率排序）：

1. `ros2 control list_controllers` 无输出 → 先查 manager service/namespace；controller 为
   `inactive` → 再查它是否按 `--inactive` 启动、尚未 switch，或配置/interface claim 失败。
   分别用 hardware component 状态、interfaces、controller 状态和 activate 错误定位，不能直接
   判成 hardware 插件加载失败。
2. 发轨迹报 `Can't accept new action goals. Controller is not running.` → 先查
   `joint_trajectory_controller` 是否为 `active`；joint 名或轨迹字段不匹配会产生另一类校验日志，
   应按实际错误分别处理。
3. 电机不转但无报错 → command_interface 类型与驱动不匹配（发了 position 但驱动只收 velocity）。
4. 运动方向反了 → URDF 中 joint axis 或编码器方向符号错误。
5. 抖动/啸叫 → 见 `references/pid_tuning.md` 的现象对照表。

更多报错信息到根因的映射见 `references/common_errors.md`。

## References

- `references/ros2_control.md` — ros2_control 架构、硬件组件实现、控制器配置示例
- `references/pid_tuning.md` — PID 整定标准流程与现象-原因对照表
- `references/common_errors.md` — 运动控制常见报错与排查路径
