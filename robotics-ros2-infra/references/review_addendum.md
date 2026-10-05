# 回放、TF 与故障诊断

核对每个节点 use_sim_time 与 /clock 来源；seek、暂停、时钟倒退可能需要重建 estimator/TF buffer。时间同步不能由 QoS 配置解决。
为关键 frame 边指定唯一 authority，定位循环或多发布者后再分析算法。消息到达间隔、header 间隔和实际控制周期分开记录。
测试节点重启、网络分区、late joiner 与 stale data；普通 publisher 不自动受 lifecycle 状态管理。

## 上游核验入口

https://docs.ros.org/en/humble/Concepts/Intermediate/About-Quality-of-Service-Settings.html

此补充是工程审查建议；涉及具体版本、参数或安全要求时核对目标实现与项目契约。
