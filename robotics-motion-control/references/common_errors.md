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
| 激活瞬间电机猛冲 | 未做 command=state 同步 | `on_activate()` 里同步 |
| 方向反了 | URDF axis 符号 / 编码器方向 / 驱动器方向参数 | 三者只改一处，保持一致性 |
| 走了 2 倍/一半距离 | 编码器线数、减速比、轮径参数错 | 核对 gear_ratio、encoder_resolution |
| 轨迹执行一半报 `Goal tolerance violated` | 轨迹太激进或机构卡滞 | 放宽 `constraints.goal_time`；查机械阻力 |
| 速度上不去 | 输出限幅/驱动器速度上限 | 核对限幅参数与母线电压 |
| odometry 漂移大 | 轮径/轮距标定错、打滑 | 做直线+原地旋转标定；融合 IMU |

## 实时性问题

- `controller_manager` 的 `update_rate` 与实际 `read/write` 耗时不匹配 → 用 `ros2 topic hz /joint_states` 验证实际频率。
- Linux 上追求硬实时：PREEMPT_RT 内核 + CPU 隔离 + 进程优先级（`chrt`）。USB 转串口做不到硬实时，>500 Hz 的环路放驱动器内闭环。
- ROS 2 DDS 默认配置在大流量时会拖慢控制回路 → 控制环路与感知/日志通信分开（不同 DDS domain 或独立进程）。
