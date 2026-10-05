# 目标跟随：工程参考

## 状态机
建议显式区分 IDLE、ACQUIRING、TRACKING、LOST、STOPPED；每个转换记录证据与时间。重获目标要求一致性与身份门控，禁止“最近的人就是原目标”。状态机的全部转移应由项目定义，不由本示例工具代替。
TRACKING 的输出依赖 fresh observation、有效 TF、target_id 和 safety_ok；LOST 状态的搜索行为由风险评估决定，默认不产生追随运动。急停后的恢复应显式确认，不能由新的检测自动解除。

## 感知到运动
测量和目标 pose 在同一时间/坐标下变换；距离可以来自有效深度、点云关联或经验证模型，单目框大小不可直接当精确米制距离。检测 confidence 不是身份置信度。
跟随 goal 不等于目标当前位置：考虑 standoff、footprint、可行路径和目标朝向。明确更新 action 的抢占/取消策略，避免重复提交旧 goal 或积累队列。目标丢失后停止命令还需底层 watchdog 验证。

## 评测
身份切换、误跟随、重获时间、跟随距离误差、急停/丢失响应、碰撞近失、舒适度、尾延迟分开报告。数据切片含相似穿着、逆光、楼梯/坡面、门口和遮挡；离线 tracking 通过不代表闭环安全。

## 离线工具契约
输入 JSON 包含 max_age_s、max_speed_mps、max_abs_yaw_rate_rps 与 samples。
每帧必须给 t、state、target_id（无目标用 null）、observation_t（无观测用 null）、safety_ok、vx、wz；时间单位秒，速度 m/s 与 rad/s。该保守契约仅允许 TRACKING 且安全、目标非空、观测新鲜时非零运动。

## 一手核验入口

以下是按任务选择的上游入口，不是“当前最新推荐”的保证；涉及版本/能力时重新读取并记录日期。

- https://github.com/ros-navigation/navigation2
- https://github.com/ifzhang/ByteTrack

## 退出码与边界

退出 0 为已声明离线检查通过（status=pass），1 为检测到违反契约（fail），2 为无效输入或读取错误（invalid，输出 stderr）。单样本/短片段不能证明长期或实机行为；输入记录真实性由采集流程保证。
