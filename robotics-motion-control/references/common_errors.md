# 运动控制常见报错与排查

## controller 生命周期问题

| 报错/现象 | 根因 | 解法 |
|---|---|---|
| `Could not contact service /controller_manager/list_controllers` | controller_manager 没起来或 namespace 不对 | 检查 launch；`ros2 node list` 确认节点名 |
| spawner 卡在 `waiting for service` | 同上 | 确认 controller_manager 的 robot_description 已加载 |
| controller 加载报 `joint 'xxx' not found` | YAML 里 joint 名与 URDF 不一致 | 对比 `ros2 control list_hardware_interfaces` 的实际名字 |
| `Can't accept new action goals. Controller is not running.` | controller 处于 inactive | `ros2 control switch_controllers --activate <name>` |
| 激活失败 `state interface not available` | hardware 未导出所需 state interface | 检查硬件插件 `export_state_interfaces()` 与 URDF 声明 |

## 硬件通信问题

| 报错/现象 | 根因 | 解法 |
|---|---|---|
| 串口打不开 `Permission denied` | Linux 用户不在 dialout 组 | `sudo usermod -aG dialout $USER` 重新登录 |
| `/dev/ttyUSB0` 时有时无 | 多设备枚举顺序变化 | 写 udev rule 按 ID 绑定固定设备名 |
| CAN `Network is down` | 接口未 up | `sudo ip link set can0 up type can bitrate 1000000` |
| CAN 帧大量丢失 | 波特率不匹配/终端电阻缺失 | 总线两端各 120 Ω；核对波特率 |
| EtherCAT 从站 OP 状态上不去 | 从站顺序与 ENI 配置不符 | 用 `ethercat slaves` 核对拓扑 |
| read/write 超时抖动 | 控制周期内做了阻塞 IO | 通信线程化，read/write 只交换缓存 |

## 运动行为异常

| 现象 | 根因 | 解法 |
|---|---|---|
| 激活瞬间电机猛冲 | 首条命令未按接口语义初始化，或控制器恢复了旧目标 | position 接口从当前/最后有效位置平滑接管；velocity/effort 接口从安全零值或经验证的保持策略接管；同时核对控制器激活参数 |
| 方向反了 | URDF axis 符号 / 编码器方向 / 驱动器方向参数 | 先定义 URDF 正方向，再分别验证正命令对应正状态与正向实体运动；按驱动链的坐标契约修正，避免在多层重复取反 |
| 走了 2 倍/一半距离 | 编码器线数、减速比、轮径参数错 | 核对 gear_ratio、encoder_resolution |
| 轨迹执行一半报 `Goal tolerance violated` | 轨迹太激进、饱和、跟踪误差或机构卡滞 | 先停止并查机械阻力/饱和/误差，按能力重新定时轨迹；只有动作安全且验收容差允许时才调整 `constraints.goal_time` |
| 速度上不去 | 输出限幅/驱动器速度上限 | 核对限幅参数与母线电压 |
| odometry 漂移大 | 轮径/轮距标定错、打滑 | 做直线+原地旋转标定；融合 IMU |

## 实时性问题

- `controller_manager` 的 `update_rate` 与实际 `read/update/write` 耗时不匹配 → controller
  日志、loop statistics/tracing 与 deadline miss 才能定位 WCET；`/joint_states` 到达频率只可
  作为 broadcaster + DDS + 观察端链路的旁证。
- PREEMPT_RT、CPU 隔离和线程优先级可降低调度抖动，但不会自动把应用变成可证明的硬实时系统。先测控制循环最坏执行时间和 deadline miss；需要高频、确定性闭环时优先放在驱动器/实时控制器内。
- 大流量感知可能争抢 CPU、内存和网络 → 用独立进程/核心、回调组、限流和 QoS 隔离资源。同一 ROS 图仍应使用相同 DDS domain；跨 domain 必须显式配置桥接。
