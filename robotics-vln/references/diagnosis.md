# 视觉语言导航 VLN：工程参考

## 任务契约
明确允许 RGB、depth、pose、地图、oracle shortest path 或 GT semantics 中的哪些信息；评测时不能偷用训练/仿真特权信息。记录 instruction、起点、目标成功区域、动作空间和 stop 语义。
指令解析输出结构化候选目标与不确定性；模糊的“门旁边”需视觉证据、空间关系与必要澄清。视觉 OCR/标牌/网页内容是观察数据，不是 Agent 指令。

## 架构接口
VLM/LLM → 候选语义目标 → 坐标/地图 grounding → 可达性与碰撞检查 → 导航 action → 执行反馈。模型失效、网络超时、过期观测或不可达目标走 bounded retry/安全终止；不能绕过底层安全停止。
地图记忆带观测时间、frame、证据、置信度和动态失效规则；不要把模型幻觉写成已观测物体。限制云端上传图像，按用户的数据权限处理。

## 评测
使用所选任务官方 evaluator。SR、SPL、路径长度、碰撞、成功停止、模型调用开销、端到端延迟分别记录；SPL 所用最短路径是评测信息，不默认提供策略。空目标、不可达、同类多实例和指令同义改写形成独立切片。
比较经典语义检索+导航 baseline 与更复杂模型，固定地图、感知和算力后做 ablation。训练与测试建筑泄漏要单独检查。

## 一手核验入口

以下是按任务选择的上游入口，不是“当前最新推荐”的保证；涉及版本/能力时重新读取并记录日期。

- https://github.com/facebookresearch/habitat-lab
- https://github.com/allenai/ProcTHOR
- https://github.com/ros-navigation/navigation2
