---
name: robotics-map-management
description: "Manage robotic dense RGB-D, occupancy, semantic and multi-session maps: representation, serialization, relocalization, versioning and navigation export. Not web maps."
license: LICENSE.txt
---

# 地图表示与长期管理

## 使用边界

仅处理明确的机器人相关任务。只读取当前问题需要的参考文件；不因普通“导航、地图、跟随、标定”等词触发。路径相对本技能目录，执行脚本时使用已解析的绝对路径，不假定当前工作目录。

## 工作流

1. 定义消费者：定位、碰撞检查、可视化、语义检索分别需要什么地图。
2. 读取 `references/diagnosis.md`，选择表示并建立坐标、尺度、时间和版本契约。
3. 将重建、优化、可导航地图生成与发布解耦；验证动态物体、未知区域与自由空间语义。
4. 保存带 hash、参数、标定、数据范围的不可变地图产物；新版本用 held-out 路线测试重定位和导航。
5. 灰度切换、原子更新和回滚由部署端实现；不要让未审核地图直接控制机器人。

## 工程约束

区分项目事实、上游事实和待验证假设。记录版本与测量证据；示例和离线检查不构成真机安全验收。先核验现有实现再决定自研；相关检索技能未安装时直接使用可用搜索工具，禁止依赖其他技能必然存在。
