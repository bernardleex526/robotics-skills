---
name: robotics-calibration-sync
description: Calibrate robot sensor intrinsics, LiDAR-camera-IMU extrinsics and acquisition clocks; diagnose offsets, drift and observability. For hand-eye use its dedicated skill.
license: LICENSE.txt
---

# 时空标定与同步

## 使用边界

仅处理明确的机器人相关任务。只读取当前问题需要的参考文件；不因普通“导航、地图、跟随、标定”等词触发。路径相对本技能目录，执行脚本时使用已解析的绝对路径，不假定当前工作目录。

## 工作流

1. 列出传感器时钟、触发线、stamp 定义、frames、机械安装和标定目标；不要把消息配对叫硬件同步。
2. 用 `references/diagnosis.md` 区分时钟 offset/drift、传输延迟、rolling shutter 和外参误差。
3. 固定标定数据与独立验证数据，检查运动激励/可观性后求解。
4. 记录变换方向、单位、模型、协方差/不确定性和标定版本。
5. 验收动态回放与温度/装配变更后的稳定性，禁止仅凭训练残差发布。

## 工程约束

区分项目事实、上游事实和待验证假设。记录版本与测量证据；示例和离线检查不构成真机安全验收。先核验现有实现再决定自研；相关检索技能未安装时直接使用可用搜索工具，禁止依赖其他技能必然存在。
