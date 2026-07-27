---
name: robotics-motion-control
description: 机器人运动控制开发助手。当用户进行机器人关节/底盘运动控制开发时使用，涵盖 ros2_control 架构搭建与配置、PID 整定、轨迹规划（点到点/样条/MoveIt）、逆运动学求解、电机驱动调试与常见控制报错排查。触发词示例：运动控制、PID 整定、轨迹规划、逆运动学、ros2_control、controller_manager、关节抖动、电机不转、motion control、trajectory planning、inverse kinematics。
agent_created: true
---

# Robotics Motion Control

## Overview

Assist with robot motion-control development on ROS/ROS 2: setting up the `ros2_control` stack, tuning PID loops, choosing and executing trajectory-planning approaches, solving inverse kinematics, and debugging control failures from symptom to root cause.

## Workflow Decision Tree

Identify the user's situation first, then follow the matching workflow:

- **从头搭建控制栈**（新机器人/新驱动）→ Workflow A: Controller Bring-up
- **控制效果差**（抖动、超调、跟踪不上、稳态误差）→ Workflow B: PID Tuning
- **需要规划运动**（机械臂点到点、底盘速度平滑、时间最优）→ Workflow C: Trajectory Planning
- **笛卡尔空间控制**（给定位姿求关节角）→ Workflow D: Inverse Kinematics
- **报错/不动作**（controller 起不来、电机无响应）→ Workflow E: Debugging，并查阅 `references/common_errors.md`

## Workflow A: Controller Bring-up (ros2_control)

1. 在 URDF/xacro 中声明 `<ros2_control>` 标签：定义每个 joint 的 `command_interface`（position/velocity/effort）与 `state_interface`，选择 hardware plugin（`mock_components/GenericSystem` 用于无硬件验证）。
2. 编写 controller 配置 YAML（`controller_manager` 节点参数），先加载 `joint_state_broadcaster`，再加载一个轨迹类控制器（`joint_trajectory_controller` 或 `forward_command_controller`）。
3. 启动顺序：`controller_manager`（含 hardware）→ `spawner joint_state_broadcaster` → `spawner <motion_controller>`。用 `ros2 control list_controllers` 确认状态为 `active`。
4. 先用 `mock_components` 全流程验证，再切换真实硬件插件。

详细架构、硬件接口实现要点与完整 YAML 示例见 `references/ros2_control.md`。

## Workflow B: PID Tuning

1. **先判型**：区分是位置环、速度环还是电流/力矩环问题；内环未整定好之前不要整外环。
2. **整定顺序**：电流环（驱动器内）→ 速度环 → 位置环。每一步先纯 P 抬到临界，再加 D 抑振，最后加小 I 消稳态误差。
3. **防护**：整定前设置输出限幅、积分 anti-windup、微分滤波；关节悬空或轻载状态下先试。
4. **验证指标**：阶跃响应的上升时间、超调量（<10% 为宜）、稳态误差、以及正弦跟踪的相位滞后。

标准整定流程（临界比例度法、继电器法、手动经验法）与现象-原因对照表见 `references/pid_tuning.md`。

## Workflow C: Trajectory Planning

按需求选择方案：

| 需求 | 方案 |
|---|---|
| 关节空间点到点、带速度/加速度约束 | 五次多项式或梯形速度曲线；ROS 2 直接发 `trajectory_msgs/JointTrajectory` 给 `joint_trajectory_controller` |
| 机械臂笛卡尔/避障规划 | MoveIt 2（OMPL 采样规划器 + 时间参数化）；先用 `moveit_py` 或 RViz MotionPlanning 插件验证 |
| 实时避障/反应式控制 | 模型预测控制（MPC）或势场法，控制频率 ≥ 50 Hz |
| 底盘速度平滑 | 对 `cmd_vel` 做加速度限幅与低通滤波，参考 Nav2 的 velocity smoother 实现 |

要点：轨迹点时间间隔建议 10–50 ms；发送前确认控制器 `constraints.goal_time` 与 `stopped_velocity_tolerance` 匹配任务精度。

## Workflow D: Inverse Kinematics

- **解析解优先**：6/7 轴机械臂有解析解时用 IKFast 或手写几何解，速度快且可多解筛选。
- **数值解**：用 TRAC-IK（容忍关节限位、收敛率优于 KDL）或 KDL 的 `ChainIkSolverPos_LMA`；设置合理的 `eps` 与超时（典型 5–50 ms）。
- **常见坑**：seed 初值离解太远导致不收敛 → 用当前关节角作 seed；多解分支跳变 → 加解空间连续性约束或选对当前构型最近的解。

## Workflow E: Debugging

快速定位清单（按出现频率排序）：

1. `ros2 control list_controllers` 无输出或状态 `inactive` → hardware 插件未加载成功，查 `controller_manager` 日志。
2. 发轨迹报 `Can't accept new action goals` → controller 未 active 或 joint 名与 URDF 不一致。
3. 电机不转但无报错 → command_interface 类型与驱动不匹配（发了 position 但驱动只收 velocity）。
4. 运动方向反了 → URDF 中 joint axis 或编码器方向符号错误。
5. 抖动/啸叫 → 见 `references/pid_tuning.md` 的现象对照表。

更多报错信息到根因的映射见 `references/common_errors.md`。

## References

- `references/ros2_control.md` — ros2_control 架构、硬件组件实现、控制器配置示例
- `references/pid_tuning.md` — PID 整定标准流程与现象-原因对照表
- `references/common_errors.md` — 运动控制常见报错与排查路径
