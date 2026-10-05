---
name: robotics-edge-deployment
description: "Deploy robotic perception/SLAM/VLN to edge computers: inference parity, end-to-end latency, resources, watchdogs and rollout. Not generic web deployment."
license: LICENSE.txt
---

# 端侧部署与性能

## 使用边界

仅处理明确的机器人相关任务。只读取当前问题需要的参考文件；不因普通“导航、地图、跟随、标定”等词触发。路径相对本技能目录，执行脚本时使用已解析的绝对路径，不假定当前工作目录。

## 工作流

1. 固定目标 OS/ROS、CPU/GPU、驱动、runtime、模型 hash 与功耗/温度状态。
2. 阅读 `references/diagnosis.md`，把模型推理与完整传感器到输出延迟分开。
3. 比较原模型和导出/量化模型的数值、任务指标及动态输入边界。
4. 压测地图增长、录包、网络异常、热降频和重启；检查 watchdog 与停止路径。
5. 交付性能证据、可回滚包和兼容矩阵；容器构建成功不代表硬件验收。

## 工程约束

区分项目事实、上游事实和待验证假设。记录版本与测量证据；示例和离线检查不构成真机安全验收。先核验现有实现再决定自研；相关检索技能未安装时直接使用可用搜索工具，禁止依赖其他技能必然存在。
