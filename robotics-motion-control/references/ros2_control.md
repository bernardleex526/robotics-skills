# ros2_control 参考

## 架构

```
Trajectory / Cmd 来源 (MoveIt, Nav2, 自写节点)
        │  JointTrajectory / cmd_vel
        ▼
Controller (joint_trajectory_controller, diff_drive_controller, ...)
        │  读写 command/state interfaces
        ▼
Resource Manager ── Hardware Component (Actuator/Sensor/System 插件)
        │
        ▼
真实驱动 (CAN/EtherCAT/串口/Modbus)
```

- **controller_manager**：唯一入口节点，负责加载/切换 controller 与 hardware。所有 `ros2 control` CLI 都与它通信。
- **Hardware Component**：以 pluginlib 插件形式实现。自行编写时继承 `hardware_interface::SystemInterface`（多关节系统）或 `ActuatorInterface`（单执行器）。

## 硬件插件必须实现的回调

| 回调 | 作用 | 要点 |
|---|---|---|
| `on_init()` | 解析 URDF `<ros2_control>` 参数 | 校验 joint 数量、interface 类型，读串口号/波特率等参数 |
| `on_configure()` | 打开设备 | 打开串口/CAN，失败返回 `CallbackReturn::ERROR` |
| `on_activate()` | 使能控制 | 将 state 值同步到 command（避免启动瞬间跳变！） |
| `read()` | 读状态 | 从驱动读编码器/电流，写入 state interface；必须在控制周期内完成 |
| `write()` | 写命令 | 把 command interface 下发给驱动 |
| `on_deactivate()/on_cleanup()/on_shutdown()/on_error()` | 生命周期收尾 | 去使能力矩、关闭设备 |

**关键陷阱**：`on_activate()` 里不做 command=state 同步，激活瞬间电机会以全速冲向 0 位，极易损坏机构或伤人。

## URDF 声明示例

```xml
<ros2_control name="my_arm" type="system">
  <hardware>
    <!-- 无硬件验证用 mock_components/GenericSystem -->
    <plugin>my_robot_driver/MyArmHardware</plugin>
    <param name="serial_port">/dev/ttyUSB0</param>
  </hardware>
  <joint name="joint1">
    <command_interface name="position"/>
    <state_interface name="position"/>
    <state_interface name="velocity"/>
  </joint>
</ros2_control>
```

## 控制器 YAML 示例

```yaml
controller_manager:
  ros__parameters:
    update_rate: 100  # Hz
    joint_state_broadcaster:
      type: joint_state_broadcaster/JointStateBroadcaster
    arm_controller:
      type: joint_trajectory_controller/JointTrajectoryController

arm_controller:
  ros__parameters:
    joints: [joint1, joint2, joint3]
    command_interfaces: [position]
    state_interfaces: [position, velocity]
    constraints:
      goal_time: 0.5
      stopped_velocity_tolerance: 0.01
```

## 常用 CLI

```bash
ros2 control list_controllers            # 状态须为 active
ros2 control list_hardware_components    # 查 hardware 生命周期状态
ros2 control list_hardware_interfaces    # 查可用 command/state interface
ros2 control switch_controllers --activate arm_controller
ros2 control reload_controller_libraries # 改完 YAML 后热重载
```

## 常用 controller 速查

- `joint_trajectory_controller` — 关节轨迹（MoveIt 默认对接它）
- `forward_command_controller` — 直接透传单点命令，调试硬件时最简
- `diff_drive_controller` — 两轮差速底盘，订阅 `cmd_vel` 发布 `odom`
- `mecanum_drive_controller` — 麦克纳姆轮（Humble+）
- `gripper_action_controller` — 夹爪
- `admittance_controller` — 导纳控制（力控场景）
