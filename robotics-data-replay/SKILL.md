---
name: robotics-data-replay
description: Prepare and audit robotics rosbag2/MCAP datasets, sensor timestamps, replay clocks, splits and privacy. Use for robot recording/replay, not arbitrary data processing.
license: LICENSE.txt
---

# 数据采集与回放

## 使用边界

仅处理明确的机器人相关任务。只读取当前问题需要的参考文件；不因普通“导航、地图、跟随、标定”等词触发。路径相对本技能目录，执行脚本时使用已解析的绝对路径，不假定当前工作目录。

## 工作流

1. 定义故障复现所需原始话题、TF、标定、参数、驱动/软件版本和数据权限。
2. 读取 `references/diagnosis.md`，先验证采集完整性、时钟及 storage/serialization，不能只确认 bag 可打开。
3. 对时间戳导出使用 `scripts/audit_timestamps.py`；CSV 格式与限制见参考。
4. 回放先隔离物理执行端，统一仿真时钟，再比较实时和离线结果。
5. 保留不可变原始数据、处理谱系、场景级 train/test split 与脱敏记录。

## 工程约束

区分项目事实、上游事实和待验证假设。记录版本与测量证据；示例和离线检查不构成真机安全验收。先核验现有实现再决定自研；相关检索技能未安装时直接使用可用搜索工具，禁止依赖其他技能必然存在。

## 离线示例

`assets/timestamps.example.csv` 仅演示输入格式，数值不是推荐的真机门限。
