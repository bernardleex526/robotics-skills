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
- **Hardware Component**：以 pluginlib 插件形式实现。自行编写时继承
  `hardware_interface::SystemInterface`（多关节系统）、`ActuatorInterface`（单执行器）或
  `SensorInterface`（只读传感器）。

## Humble 硬件接口契约与常用生命周期回调

Humble 的 System/Actuator 驱动需导出 state/command interfaces 并实现有界的 `read()`/`write()`；
Sensor 只导出 state interfaces 并实现 `read()`。生命周期基类提供部分默认行为，但真实驱动若在
configure/activate 等阶段申请、使能或释放资源，就应覆盖相应回调并明确失败状态，不能依赖默认
成功掩盖设备未就绪。

| 回调 | 作用 | 要点 |
|---|---|---|
| `on_init()` | 解析 URDF `<ros2_control>` 参数 | 校验 joint 数量、interface 类型，读串口号/波特率等参数 |
| `export_state_interfaces()` | 向 Resource Manager 导出状态句柄 | Humble 中为每个声明的 state interface 返回绑定到稳定存储的句柄 |
| `export_command_interfaces()` | 导出可被 controller claim 的命令句柄 | Humble 的 System/Actuator 实现；`SensorInterface` 没有 command export |
| `on_configure()` | 打开设备 | 打开串口/CAN，失败返回 `CallbackReturn::ERROR` |
| `on_activate()` | 准备接管控制 | 按 command interface 语义建立安全初值，并确认状态有效后再使能 |
| `read()` | 读状态 | 从驱动读编码器/电流，写入 state interface；必须在控制周期内完成 |
| `write()` | 写命令 | System/Actuator 把 command interface 下发给驱动；Sensor 没有该路径 |
| `on_deactivate()` | active → inactive | 停止接收运动目标并进入设备定义的安全 inactive 状态；通常保留重新激活所需通信/资源 |
| `on_cleanup()` | inactive → unconfigured | 撤销 configure 阶段资源并按实现关闭通信 |
| `on_shutdown()` / `on_error()` | 终止或故障处理 | 执行经风险分析的受控停机、记录故障并释放相应资源；重力负载不能笼统假设“去使能力矩”就是安全 |

**关键陷阱**：不能把所有 command 都机械地设成 state。position command 通常应从当前位置或
最后有效命令平滑接管；velocity/effort command 通常从安全零值或经风险分析的保持策略接管。
还要检查 controller 是否恢复旧目标、驱动器自身的上电模式及命令超时。首次激活必须在受控测试条件下验证。

以上接口是 **Humble** 契约；较新 ros2_control 版本可按 URDF 自动创建已声明接口，不能把新版本
示例反向套到 Humble。实现类末尾还要导出 pluginlib 类型，例如：

```cpp
PLUGINLIB_EXPORT_CLASS(
  my_robot_driver::MyArmHardware,
  hardware_interface::SystemInterface)
```

同时在 plugin XML 中声明类与 base type，并在 CMake/package manifest 中导出该 XML。缺任一步，
Resource Manager 都无法按 URDF 中的 `<plugin>my_robot_driver/MyArmHardware</plugin>` 加载它。

## robot_description 接入（Humble）

controller manager 订阅私有话题 `~/robot_description`。通常由 `robot_state_publisher` 在
`/robot_description` 发布 URDF，并在 launch 中显式 remap：

```python
control_node = Node(
    package="controller_manager",
    executable="ros2_control_node",
    parameters=[robot_controllers],
    remappings=[("~/robot_description", "/robot_description")],
)
```

直接把 URDF 作为 controller manager 的 `robot_description` 参数传入在 Humble 已标为 deprecated；
启动时还要确认发布者使用适合静态模型交付的 QoS，且 manager 实际收到非空 URDF。

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
ros2 run controller_manager unspawner arm_controller
ros2 run controller_manager spawner arm_controller \
  --param-file /absolute/path/to/controllers.yaml
```

**关于改完 YAML 生效**：`ros2 control reload_controller_libraries` 重载的是 controller 的
**pluginlib 共享库**，不读取磁盘上的 YAML。单独执行 `load_controller` 也不会自动知道刚修改的
文件路径：用对应发行版 spawner 的 `--param-file` 重新加载，或重启加载该参数文件的 launch/
`controller_manager`。切换前先停稳机构，并按依赖顺序处理 controller。

只有 controller 明确声明为动态可写的参数，才可对该 controller 节点执行 `ros2 param set`；
参数节点归属和可写性用 `ros2 param list /<controller>` 与 `ros2 param describe` 核对，不能假定
参数都属于 `/controller_manager`。

来源：ROS 2 Humble
[`controller_manager` 用户文档](https://control.ros.org/humble/doc/ros2_control/controller_manager/doc/userdoc.html)。

## 常用 controller 速查

- `joint_trajectory_controller` — 关节轨迹（MoveIt 默认对接它）
- `forward_command_controller` — 订阅 `~/commands`
  (`std_msgs/msg/Float64MultiArray`) 并直接前馈接口值；适合硬件接口烟测，不接收
  `trajectory_msgs/msg/JointTrajectory`，也不提供 `FollowJointTrajectory` action
- `diff_drive_controller` — 两轮差速底盘，订阅 `cmd_vel` 发布 `odom`
- `mecanum_drive_controller` — 麦克纳姆轮（Humble+）
- `gripper_action_controller` — 夹爪
- `admittance_controller` — 导纳控制（力控场景）
