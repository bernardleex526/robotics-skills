# 仿真器对比与选型

## 对比总表

| 维度 | Isaac Sim / Isaac Lab | Gazebo Sim（与 ROS 版本配套） | MuJoCo |
|---|---|---|---|
| 强项 | GPU 并行 RL、高保真渲染、合成数据 | ROS 2 集成生态成熟 | 轻量、接触任务常用，MJX 可加速部分工作负载 |
| 弱项 | 重、吃显卡（RTX 起步）、学习曲线陡 | 渲染与接触精度一般、并行能力弱 | ROS 集成靠第三方桥 |
| 物理引擎 | PhysX（版本随 Isaac Sim 锁定） | Gazebo Sim 默认 DART；其他 engine plugin 的能力随 release/安装变化 | MuJoCo 自研 |
| RL 并行规模 | 依模型/传感器/GPU 实测 | 通常用于少量全栈环境 | 依 MJX 兼容算子和硬件实测 |
| 典型用户 | 腿足/人形 RL 团队、视觉 sim2real | 导航/SLAM/传统机器人验证 | 操作（manipulation）研究 |

## 选型建议

- **RL 训练腿足/人形/四足** → Isaac Lab 是常见候选；还要按目标任务、支持的 GPU/版本、传感器和部署框架做基准。
- **操作任务（抓取/插装）** → MuJoCo（接触好）或 Isaac Lab（要并行时）。ManiSkill 基准基于 SAPIEN 也可考虑。
- **验证完整 ROS 2 软件栈**（导航、SLAM、ros2_control）→ Gazebo + `ros_gz_bridge`，`ros2_control` 有官方 `gz_ros2_control` 插件。
- **视觉策略 sim2real** → Isaac Sim + Replicator 域随机化渲染。

## 组合用法（常见且推荐）

- 训练与全栈联调可以使用不同仿真器，但模型转换、接触语义和执行器接口必须做一致性验证；“在另一个仿真器跑通”不是必选步骤，也不等于真机验收。
- MuJoCo 做快速算法原型，Isaac 做最终大规模训练。

## 通用搭建要点

1. **时间契约对齐**：明确 physics step、controller update、策略 decimation、传感器率和端到端延迟。仿真不一定与每个真机线程同频，但策略看到的采样/保持/延迟语义必须一致。
2. **ros2_control 分层**：`mock_components/GenericSystem` 只验证接口、controller 和 launch，不模拟接触/动力学；物理联调用与目标 Gazebo 版本匹配的 `gz_ros2_control`。切换 hardware plugin 后仍要验证时序、限幅、故障与传感器语义。
3. **时间同步**：仿真用 `use_sim_time:=true`，bag 回放与节点全链路统一。
4. **GPU 资源规划**：并行环境数取决于模型自由度、传感器、接触、渲染、训练算法、软件版本和 GPU；在目标场景测 steps/s、显存峰值和数值稳定性，不引用跨任务的固定数量。

## ROS/Gazebo 版本边界

下表是 2026-07-29 的核验入口，不使用浮动 `latest` 代替项目 lockfile/容器摘要：

| 组合 | 已知边界 | 项目动作 |
|---|---|---|
| Isaac Lab `v2.3.x` | 上游兼容表列 Isaac Sim 4.5 / 5.0 / 5.1；`v2.3.2` 是该稳定线的最终 patch | 锁定 Lab tag、Isaac Sim build、driver、Python/PyTorch 与训练依赖 |
| Isaac Lab `develop` / 3.0 beta | 面向 Isaac Sim 6.0、Python 3.12，含 quaternion WXYZ→XYZW 等 breaking changes | 不与 2.x checkpoint/配置混用；先按迁移指南重验 |
| Isaac Sim 5.0 ROS bridge | Ubuntu 22.04 推荐 Humble、24.04 推荐 Jazzy；自定义 ROS workspace 需匹配其 Python 3.11 runtime | 锁定 Ubuntu/ROS/Python/接口包 ABI；其他 Isaac Sim build 重新查对应文档 |
| ROS 2 Humble + Fortress | Humble 默认 Gazebo 组合；Fortress 2026-09 EOL，而 Humble 生命周期更长 | 新部署制定迁移计划；现有部署冻结包版本并做回归 |
| ROS 2 Humble + Harmonic | 官方支持的非默认组合；需安装 Harmonic/`ros_gzharmonic` 并以 `GZ_VERSION=harmonic` 构建 Humble `gz_ros2_control` | 在隔离 workspace/镜像验证 bridge、plugins、SDF 与 ros2_control |
| ROS 2 Jazzy + Harmonic | 默认配套组合 | 仍锁定具体包版本并做目标模型回归 |

Gazebo Sim 的默认 physics plugin 是 DART。Bullet/TPE 或其他后端是否可用、支持哪些 joint/contact/
solver 特性取决于 Gazebo release 与实际安装插件；切换后必须用同一模型基准验证，不能在选型表中
把它们写成无条件等价。

来源：

- [Humble `gz_ros2_control`](https://control.ros.org/humble/doc/gz_ros2_control/doc/index.html)
- [Gazebo release 生命周期](https://gazebosim.org/docs/harmonic/releases/)
- [Isaac Lab / Isaac Sim 兼容表](https://github.com/isaac-sim/IsaacLab)
- [Isaac Lab releases](https://github.com/isaac-sim/IsaacLab/releases)
- [Isaac Sim 5.0 ROS 2 兼容性](https://docs.isaacsim.omniverse.nvidia.com/5.0.0/installation/install_ros.html)
