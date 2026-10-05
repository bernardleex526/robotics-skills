---
name: robotics-lidar-odometry
description: Diagnose robotic LiDAR-inertial odometry (LIO), point timing, deskew, scan geometry and degeneracy. Use for FAST-LIO/LIO-SAM integration, not generic point-cloud rendering.
license: LICENSE.txt
---

# 激光惯性里程计

## 使用边界

仅处理明确的机器人相关任务。只读取当前问题需要的参考文件；不因普通“导航、地图、跟随、标定”等词触发。路径相对本技能目录，执行脚本时使用已解析的绝对路径，不假定当前工作目录。

## 工作流

1. 固定雷达扫描模式、驱动提交、IMU 型号、时钟域、点时间字段/单位和算法版本。先区分原版、ROS 2 移植和自研修改。
2. 从静止、受控转弯、退化路段各抽取短包；沿驱动→预处理→去畸变→残差→状态更新定位最早失真环节。
3. 读取 `references/diagnosis.md`，检查扫描参考时刻、IMU 插值范围和外参方向，不能仅靠提高迭代次数补偿坏输入。
4. 以相同原始数据比较修改前后轨迹、地图重影、失败率和尾延迟，保留失败片段。
5. 交付输入契约、根因证据、最小改动、回归结果；里程计成功不代表已有全局重定位或闭环。

## 工程约束

区分项目事实、上游事实和待验证假设。记录版本与测量证据；示例和离线检查不构成真机安全验收。先核验现有实现再决定自研；相关检索技能未安装时直接使用可用搜索工具，禁止依赖其他技能必然存在。
