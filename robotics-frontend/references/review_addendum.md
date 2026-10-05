# 过期数据和控制权

浏览器显示 receipt time 与 acquisition time/数据年龄；图像、TF 和地图来自不同时间时明确提示，不把最新 TF 无条件应用于旧图像。
单一控制权、deadman、服务端 watchdog 与底层急停独立设计。页面隐藏、lost pointer、WebSocket reconnect 后不得自动恢复旧速度；UI 零指令并不能证明机器人已停止。
桥接端做认证/权限与消息大小限制，避免向非可信网络暴露控制接口。普通仪表盘改动不自动启用 teleop。

## 上游核验入口

https://github.com/RobotWebTools/rosbridge_suite

此补充是工程审查建议；涉及具体版本、参数或安全要求时核对目标实现与项目契约。
