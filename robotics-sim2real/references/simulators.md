# 仿真器对比与选型

## 对比总表

| 维度 | Isaac Sim / Isaac Lab | Gazebo (Harmonic) | MuJoCo |
|---|---|---|---|
| 强项 | GPU 大规模并行 RL、高保真渲染、合成数据 | ROS/ROS 2 原生集成、生态成熟 | 接触动力学精确、轻量、MJX GPU 加速 |
| 弱项 | 重、吃显卡（RTX 起步）、学习曲线陡 | 渲染与接触精度一般、并行能力弱 | ROS 集成靠第三方桥 |
| 物理引擎 | PhysX 5 | DART/Bullet 可选 | MuJoCo 自研（接触模型优秀） |
| RL 并行规模 | 数千环境 | 单环境为主 | MJX 数千环境 |
| 典型用户 | 腿足/人形 RL 团队、视觉 sim2real | 导航/SLAM/传统机器人验证 | 操作（manipulation）研究 |
| 许可 | 免费（NVIDIA） | Apache 2.0 | Apache 2.0（DeepMind 开源） |

## 选型建议

- **RL 训练腿足/人形/四足** → Isaac Lab。它是事实标准，legged_gym 生态迁移过来最顺。
- **操作任务（抓取/插装）** → MuJoCo（接触好）或 Isaac Lab（要并行时）。ManiSkill 基准基于 SAPIEN 也可考虑。
- **验证完整 ROS 2 软件栈**（导航、SLAM、ros2_control）→ Gazebo + `ros_gz_bridge`，`ros2_control` 有官方 `gz_ros2_control` 插件。
- **视觉策略 sim2real** → Isaac Sim + Replicator 域随机化渲染。

## 组合用法（常见且推荐）

- 训练在 Isaac Lab，**部署前在 Gazebo 里做全栈联调**（连同导航、感知、ros2_control），因为真机栈跑的是 ROS 2。
- MuJoCo 做快速算法原型，Isaac 做最终大规模训练。

## 通用搭建要点

1. **仿真控制频率与真机一致**：策略推理频率（如 50 Hz）、底层控制频率（如 500 Hz）两边对齐，否则延迟特性全变。
2. **ros2_control 直通**：仿真里挂 `mock_components` 或 `gz_ros2_control`，让上层软件（MoveIt/Nav2/策略节点）完全感知不到仿真与真机的差别——切换只换 hardware plugin。
3. **时间同步**：仿真用 `use_sim_time:=true`，bag 回放与节点全链路统一。
4. **GPU 资源规划**：Isaac 并行数受显存限制；4090 大约 4096 个简单环境起步，人形带相机可能只有几百。
