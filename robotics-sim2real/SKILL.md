---
name: robotics-sim2real
description: Sim-to-Real（仿真到现实迁移）开发助手。当用户进行机器人仿真训练/验证并向真机部署时使用，涵盖仿真器选择（Isaac Sim/Lab、Gazebo、MuJoCo）、URDF/SDF 模型对齐、域随机化策略、系统辨识与动力学参数对齐、强化学习策略的 sim-to-real 部署流程与真机安全检查清单。触发词示例：sim-to-real、sim2real、域随机化、domain randomization、Isaac Sim、Isaac Lab、Gazebo、MuJoCo、系统辨识、reality gap、策略部署、仿真训练迁移真机。
agent_created: true
---

# Robotics Sim-to-Real

## Overview

Assist with transferring robot behaviors (RL policies, controllers, pipelines) from simulation to real hardware: picking a simulator, aligning models and dynamics, applying domain randomization, running system identification, and executing a staged real-robot deployment with safety gates.

## Workflow Decision Tree

- **刚开始/选仿真器** → Step 1（`references/simulators.md`）
- **仿真里行为就不对** → Step 2: 模型与动力学对齐（`references/dynamics_alignment.md`）
- **仿真行、真机不行（reality gap）** → Step 3: 域随机化 + 系统辨识（`references/domain_randomization.md`）
- **准备上真机** → Step 4: 分阶段部署（必须过完安全检查清单）

## Step 1: 仿真器选型速查

| 需求 | 选择 |
|---|---|
| RL 大规模并行训练（腿足/机械臂） | Isaac Lab（GPU 并行，生态最活跃） |
| 传统 ROS 集成验证、导航/SLAM | Gazebo（Harmonic）+ ros2_control 官方桥 |
| 接触丰富的操作任务、轻量快速 | MuJoCo（接触模型好，MJX 可 GPU 加速） |
| 高保真渲染/视觉 sim2real | Isaac Sim（RTX 光追 + Replicator 合成数据） |

细节对比与联合使用方式见 `references/simulators.md`。

## Step 2: 模型对齐（先于任何训练）

1. **URDF 一致性**：仿真与真机驱动用同一份 URDF；检查惯性参数（`<inertial>`）不是默认立方体近似——用 CAD 导出或测量值。
2. **关节限位与力矩限幅**：仿真限位 = 真机限位；`effort`、`velocity` 上限按驱动器 datasheet 填，这是最常见的 gap 来源。
3. **传动建模**：减速器背隙、皮带弹性、谐波减速器柔性——先用「驱动器一阶延迟 + 死区」近似，不够再上柔性关节模型。
4. **执行器动力学**：至少建模速度环一阶惯性（时间常数实测）；RL 训练时把「动作 → 电机指令」的延迟也建进去。
5. **传感器模型**：噪声、延迟、量化按实测数据加；相机仿真先做几何对齐再谈渲染保真。

验证方法与参数辨识流程见 `references/dynamics_alignment.md`。

## Step 3: 缩小 Reality Gap

两条路并用：

- **系统辨识（SysID）把仿真调准**：对真机做阶跃/扫频激励，拟合质量、摩擦（库仑+粘性）、延迟。原则：能测准的参数就别靠随机化去覆盖。
- **域随机化（DR）覆盖测不准的部分**：摩擦 ±50%、质量/质心 ±10~20%、延迟 0~20 ms、外力扰动、观测噪声。渐进式 DR：先小范围，策略收敛后逐步扩大。

参数选择对照表（哪些该辨识、哪些该随机化、随机化范围经验值）见 `references/domain_randomization.md`。

**视觉 sim2real**：优先深度/分割等几何模态而非 RGB；必须 RGB 时用 Replicator 做材质/光照/相机位姿随机化，或做域适配（CyCADA 类）。

## Step 4: 分阶段真机部署（不可跳步）

1. **离线回放**：真机传感器数据录包，在仿真里回放，比对观测一致性。
2. **硬件在环**：策略在真传感器输入下运行，但输出不接执行器，只记录动作。
3. **低功率使能**：限压/限流到 20–30%，策略输出再乘安全系数；手放急停上。
4. **受限空间全功率**：吊装或围栏内运行，逐步解除输出限幅。
5. **常态运行**：加监控看门狗（心跳、越界、温度），异常自动急停。

**每次升级前必须过完 `references/deployment_checklist.md` 的安全检查清单**——包括急停链路、限位、失能行为、通信中断行为等 20+ 项硬性检查。

## 调试真机失败的归因顺序

1. 观测不一致？（先在仿真回放真机数据对比）
2. 动作执行不一致？（延迟/限幅/驱动器模式不匹配，最常见）
3. 动力学不一致？（摩擦、负载与训练分布不符 → 补 SysID 或扩 DR）
4. 任务分布不一致？（真机初始状态超出训练分布 → 改训练初始化采样）

## References

- `references/simulators.md` — 仿真器对比与选型
- `references/dynamics_alignment.md` — URDF/执行器/传感器建模与系统辨识流程
- `references/domain_randomization.md` — 域随机化策略与参数范围经验表
- `references/deployment_checklist.md` — 真机部署安全检查清单（强制执行）
