# 时间和命令所有权

分别量测 read/update/write 和总循环 jitter，joint_states 发布频率不是控制循环的完整证据。记录调度、锁、I/O 超时、page fault 与超限策略。
只允许经过授权的命令源；模式切换与重新激活不得沿用过期 command。根据接口语义处理积分器、目标和测量的无突变接续。
软件限位不是独立安全防护；不为调参绕过急停、硬限位或厂商保护。

## 上游核验入口

https://control.ros.org/humble/doc/ros2_control/controller_manager/doc/userdoc.html

此补充是工程审查建议；涉及具体版本、参数或安全要求时核对目标实现与项目契约。
