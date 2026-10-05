---
name: robotics-localization-fusion
description: Diagnose robot EKF/UKF, wheel-IMU-GNSS fusion, covariance, frame ownership and global relocalization. Use for estimator consistency, not generic location services.
license: LICENSE.txt
---

# 融合定位与重定位

## 使用边界

仅处理明确的机器人相关任务。只读取当前问题需要的参考文件；不因普通“导航、地图、跟随、标定”等词触发。路径相对本技能目录，执行脚本时使用已解析的绝对路径，不假定当前工作目录。

## 工作流

1. 画出测量来源、状态、坐标和 TF 发布权；区分局部连续里程计与全局修正。
2. 读取 `references/diagnosis.md`，核对协方差、相关观测、延迟与 GNSS 基准。
3. 使用可回放的正常/故障段，先诊断输入与可观性，再改过程噪声或融合开关。
4. 验证失锁、打滑、传感器掉线、跳变及恢复；不可只验正常轨迹。
5. 交付误差、创新、覆盖率及降级策略。

## 工程约束

区分项目事实、上游事实和待验证假设。记录版本与测量证据；示例和离线检查不构成真机安全验收。先核验现有实现再决定自研；相关检索技能未安装时直接使用可用搜索工具，禁止依赖其他技能必然存在。
