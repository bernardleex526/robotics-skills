---
name: robotics-target-following
description: "Develop robot person/object following: identity association, RGB-D/LiDAR tracking, occlusion recovery, standoff goals and loss-of-target behavior. Not social-media following."
license: LICENSE.txt
---

# 目标跟随

## 使用边界

仅处理明确的机器人相关任务。只读取当前问题需要的参考文件；不因普通“导航、地图、跟随、标定”等词触发。路径相对本技能目录，执行脚本时使用已解析的绝对路径，不假定当前工作目录。

## 工作流

1. 固定目标授权/选择方式、传感器、跟随距离、速度包络和停止语义；人脸或身份数据按隐私约束处理。
2. 按 `references/diagnosis.md` 分开验证检测、身份关联、运动估计、目标生成和控制。
3. 使用 `scripts/check_follow_trace.py` 对声明契约的离线 trace 检查命令门控；此工具不发布控制命令，也不证明真实安全。
4. 测试交叉行人、遮挡、ID switch、目标丢失、过期 TF、网络掉线与急停。
5. 真机测试需独立授权和安全方案；默认先离线/仿真，不自动追随陌生人。

## 工程约束

区分项目事实、上游事实和待验证假设。记录版本与测量证据；示例和离线检查不构成真机安全验收。先核验现有实现再决定自研；相关检索技能未安装时直接使用可用搜索工具，禁止依赖其他技能必然存在。

## 离线示例

`assets/trace.example.json` 仅演示输入格式，数值不是推荐的真机门限。
