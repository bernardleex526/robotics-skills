---
name: robotics-vln
description: Develop robot vision-language navigation (VLN), instruction grounding, semantic goals and navigation evaluation. Not website navigation, ordinary chatbots or generic VLM prompting.
license: LICENSE.txt
---

# 视觉语言导航 VLN

## 使用边界

仅处理明确的机器人相关任务。只读取当前问题需要的参考文件；不因普通“导航、地图、跟随、标定”等词触发。路径相对本技能目录，执行脚本时使用已解析的绝对路径，不假定当前工作目录。

## 工作流

1. 明确任务是 VLN、ObjectNav、PointNav 还是开放词汇目标搜索；记录离散图/连续环境与传感器权限。
2. 读取 `references/diagnosis.md`，把语言 grounding、地图记忆、规划与安全执行分层。
3. 新架构或模型选型先联网核验论文/官方代码/权重与许可；无网时明确未检索，不能声称最新。
4. 固定 seen/unseen 场景、指令集、episode 和预算；测试歧义、目标不存在、动态遮挡与停止条件。
5. 交付可回放决策轨迹、几何目标验证、失败分类与部署约束；不得把 VLM 文字直接变成底盘命令。

## 工程约束

区分项目事实、上游事实和待验证假设。记录版本与测量证据；示例和离线检查不构成真机安全验收。先核验现有实现再决定自研；相关检索技能未安装时直接使用可用搜索工具，禁止依赖其他技能必然存在。
