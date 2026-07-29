---
name: robotics-sim2real
description: Sim-to-Real（仿真到现实迁移）开发助手。当用户进行机器人仿真训练/验证并向真机部署时使用，涵盖仿真器选择（Isaac Sim/Lab、Gazebo、MuJoCo）、URDF/SDF 模型对齐、域随机化策略、系统辨识与动力学参数对齐、强化学习策略的 sim-to-real 部署流程与真机安全检查清单。触发词示例：sim-to-real、sim2real、域随机化、domain randomization、Isaac Sim、Isaac Lab、Gazebo、MuJoCo、系统辨识、reality gap、策略部署、仿真训练迁移真机。
license: LICENSE.txt
---

# Robotics Sim-to-Real

## Overview

Assist with transferring robot behaviors (RL policies, controllers, pipelines) from simulation to real hardware: picking a simulator, aligning models and dynamics, applying domain randomization, running system identification, and executing a staged real-robot deployment with safety gates.

## Workflow Decision Tree

- **刚开始/选仿真器** → Step 1（`references/simulators.md`）
- **仿真里行为就不对** → Step 2: 模型与动力学对齐（`references/dynamics_alignment.md`）
- **仿真行、真机不行（reality gap）** → Step 3: 域随机化 + 系统辨识（`references/domain_randomization.md`）
- **准备上真机** → Step 4: 先冻结策略部署契约，再分阶段部署

## Step 1: 仿真器选型速查

| 需求 | 选择 |
|---|---|
| RL 大规模并行训练（腿足/机械臂） | Isaac Lab（GPU 并行，生态最活跃） |
| ROS 2 Humble 全栈集成验证、导航/SLAM | 默认配套 Gazebo Fortress + `gz_ros2_control`；Harmonic 是需显式安装/验证的非默认组合 |
| 接触丰富的操作任务、轻量快速 | MuJoCo（接触模型好，MJX 可 GPU 加速） |
| 高保真渲染/视觉 sim2real | Isaac Sim（RTX 光追 + Replicator 合成数据） |

细节对比与联合使用方式见 `references/simulators.md`。

## Step 2: 模型对齐（先于任何训练）

1. **模型源一致性**：明确 URDF 或 SDF 的唯一 source of truth；若经过 URDF→SDF/USD/MJCF
   转换，锁定转换器版本并对 frame、惯量、joint/limit/mimic、contact、sensor 和 plugin 做语义
   diff。转换成功不代表语义无损。
2. **关节限位与力矩限幅**：仿真限位 = 真机限位；`effort`、`velocity` 上限按驱动器 datasheet 填，这是最常见的 gap 来源。
3. **传动建模**：减速器背隙、皮带弹性、谐波减速器柔性——先用「驱动器一阶延迟 + 死区」近似，不够再上柔性关节模型。
4. **执行器动力学**：至少建模速度环一阶惯性（时间常数实测）；RL 训练时把「动作 → 电机指令」的延迟也建进去。
5. **传感器模型**：噪声、延迟、量化按实测数据加；相机仿真先做几何对齐再谈渲染保真。

验证方法与参数辨识流程见 `references/dynamics_alignment.md`。

## Step 3: 缩小 Reality Gap

两条路并用：

- **系统辨识（SysID）建立 nominal model**：在风险允许的有界激励下拟合质量、摩擦、执行器带宽和延迟，并报告置信区间/残差。
- **域随机化（DR）覆盖残余不确定性和真实变化**：分布来自实测批次、温度、载荷、磨损与辨识残差，并保持物理约束和参数相关性。固定百分比只可作为待验证实验假设。

参数选择对照表（哪些该辨识、哪些该随机化、随机化范围经验值）见 `references/domain_randomization.md`。
DR 事件按 `startup / reset / interval / temporal process` 分类，不能把所有参数都在 episode
边界重采样。

**视觉 sim2real**：按部署时可得模态和目标数据选择 RGB、深度、分割或融合；分别建模真实传感器
噪声与缺失。RGB 可做材质/光照/曝光随机化，深度也要覆盖边缘、空洞和距离相关噪声。

## Step 4: 分阶段真机部署（不可跳步）

1. **冻结策略部署契约**：按 `references/policy_deployment_contract.md` 归档有序 observation/action、
   单位/frame、scale/offset/clip、normalization、history、recurrent reset、控制频率、action hold、
   模型格式/版本/hash；actor 输入不得混入训练期 privileged observations。
2. **离线回放**：真机传感器数据录包，在部署 adapter 中回放，用固定 golden vectors 比对
   pre-processing、策略输出与 reset 行为。
3. **硬件在环**：策略在真传感器输入下运行，但输出不接执行器，只记录动作；契约或 hash
   不匹配直接拒绝进入下一阶段。
4. **受控执行器接入**：按厂商安全模式和风险评估设置速度/力矩/功率限制，使用适合该机构的夹具、支撑或隔离区；固定百分比可能让重力负载失稳。
5. **逐级扩大工作包络**：每级只放开一个经验证的速度、负载、环境或策略范围，并保留独立安全监控。
6. **常态运行候选**：验证 watchdog、越界、温度、通信中断和恢复状态；异常进入风险分析定义的安全状态，而不是泛称“软件自动急停”。

**每次升级前必须过完 `references/deployment_checklist.md`**。它是工程审查模板，不是设备风险评估、
安全功能 PL/SIL 验证或认证文件。

## 调试真机失败的归因顺序

1. 观测不一致？（先在仿真回放真机数据对比）
2. 动作执行不一致？（延迟/限幅/驱动器模式不匹配，最常见）
3. 动力学不一致？（摩擦、负载与训练分布不符 → 补 SysID 或扩 DR）
4. 任务分布不一致？（真机初始状态超出训练分布 → 改训练初始化采样）

## References

- `references/simulators.md` — 仿真器对比与选型
- `references/dynamics_alignment.md` — URDF/执行器/传感器建模与系统辨识流程
- `references/domain_randomization.md` — 域随机化策略与参数范围经验表
- `references/policy_deployment_contract.md` — 训练/回放/HIL/真机共用的策略接口与制品门禁
- `references/deployment_checklist.md` — 真机部署安全检查清单（强制执行）
