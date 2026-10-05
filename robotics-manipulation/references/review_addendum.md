# 感知到抓取执行

抓取目标要携带 frame、stamp 和不确定性；规划场景中碰撞物体、attached object 与实际夹持状态一致。场景更新完成的证据不是只调用了 publisher。
规划成功、时间参数化成功、控制器接受和实际完成是四个阶段。检查起始状态新鲜度、轨迹容差、控制器映射与中途取消。
学习抓取模型的 score 不是执行成功概率；用真实夹具、载荷和目标分布做验证，禁用碰撞检查不能作为普通修复。

## 上游核验入口

https://moveit.picknik.ai/humble/doc/examples/planning_scene/planning_scene_tutorial.html

此补充是工程审查建议；涉及具体版本、参数或安全要求时核对目标实现与项目契约。
