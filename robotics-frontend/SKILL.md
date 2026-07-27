---
name: robotics-frontend
description: 机器人 Web 前端开发助手。当用户开发机器人相关的 Web 界面时使用，涵盖通过 rosbridge/WebSocket 接入 ROS/ROS 2 数据、Foxglove Studio 及其 web-sdk 自定义面板、地图/点云/TF/轨迹可视化、实时状态监控仪表盘、远程操控（teleop）界面开发。触发词示例：机器人前端、机器人仪表盘、rosbridge、roslibjs、Foxglove、webviz、点云可视化、机器人监控页面、远程操控界面、teleop web、robot dashboard。
agent_created: true
---

# Robotics Frontend

## Overview

Assist with building web frontends for robots: connecting to ROS/ROS 2 over rosbridge/WebSocket, visualizing robot state (TF, map, point cloud, trajectory), building real-time monitoring dashboards, and creating teleoperation UIs. Default stack: React + TypeScript + roslibjs (or @foxglove/rosmsg + WebSocket), Vite for tooling.

## Workflow Decision Tree

- **只要可视化/调试，不写代码** → Path A: Foxglove Studio 现成工具
- **要定制界面（监控页/操控台/交付给客户）** → Path B: 自研 Web 前端（本技能主体）
- **在现有网页里嵌 3D 机器人视图** → Path C: 只集成可视化组件（ros3djs 或 Foxglove web-sdk 面板）

## Path A: Foxglove Studio（零代码）

1. 机器人端启动 rosbridge：`ros2 launch rosbridge_server rosbridge_websocket_launch.xml`（默认端口 9090）。
2. Foxglove Studio（桌面版或 app.foxglove.dev）→ Open connection → `ws://<robot-ip>:9090`。
3. 需要原生高性能（点云大、bag 回放）用 Foxglove 桌面版 + `foxglove_bridge`（比 rosbridge 带宽效率高，支持压缩）。

## Path B: 自研前端标准流程

### 1. 连接层

- 优先 `foxglove_bridge`（WebSocket，协议更高效，支持 schema 自省）；兼容性优先时用经典 `rosbridge_suite` + `roslibjs`。
- 封装单例 `RosConnection`：自动重连（指数退避）、连接状态事件、topic 订阅管理。参考 `references/rosbridge_integration.md`。
- **必须处理断线**：机器人 WiFi 环境必断线；UI 要显示连接状态并在恢复后重新订阅。

### 2. 数据流设计

- 高频 topic（`/odom` 30 Hz、`/joint_states` 50+ Hz）：**节流**（10–15 Hz 足够显示）+ 在渲染循环外用 ref/zustand transient 更新，避免 React 高频重渲染。
- 大消息（点云、图像、地图）：点云用 `sensor_msgs/PointCloud2` 二进制解析 + Three.js Points；图像优先走独立 WebRTC/web_video_server，别用 rosbridge 传 raw image（带宽爆炸）。
- 地图 `/map`（OccupancyGrid）：只在更新时重绘到 canvas，做 PNG 缓存层。

### 3. 可视化选型

| 内容 | 方案 |
|---|---|
| 完整 rviz 式视图 | `@foxglove/web-sdk` + Foxglove 自定义面板，或直接嵌 `ros3djs` |
| 自定义 3D 场景 | Three.js / react-three-fiber 自建（TF 树驱动模型位姿） |
| 2D 地图 + 路径 + 机器人位姿 | canvas/SVG 自绘（OccupancyGrid 渲染 + 箭头），轻量可控 |
| 状态仪表盘 | ECharts/Recharts + MUI/Tailwind |
| URDF 模型展示 | `urdf-loader`（Three.js）+ TF 驱动关节 |

### 4. 操控（teleop）界面

- 虚拟摇杆发 `/cmd_vel`：10–20 Hz 定时发（Twist 协议要求持续发送），**松开即停发**，机器人端配 velocity timeout。
- **安全规则（前端必须做）**：连接断开 → 立即显示失联遮罩并通知后端停车；控制指令做前端限幅；急停按钮做成最显眼元素，点击直接 publish 到急停 topic 并本地停止一切运动指令。
- 键盘控制：keydown/keyup 状态机，防止按键卡死导致持续运动。

### 5. 部署

- 前端打包成静态文件放机器人上（nginx/Caddy 或直接 `python3 -m http.server` 原型期）。
- 机器人多机/多网段：WebSocket 地址做成可配置（URL 参数或配置文件），别硬编码 IP。
- 跨域：rosbridge WebSocket 无 CORS 问题；HTTP API（如 map server REST）需要后端配 CORS。

详细代码模式（连接单例、节流 hook、OccupancyGrid 渲染、cmd_vel 摇杆）见 `references/rosbridge_integration.md`。

## Path C: 嵌入现成组件

- **Foxglove 自定义面板**：在 Foxglove 里写 React 面板（`@foxglove/extension`），适合「90% 现成 + 10% 定制」。
- **ros3djs**：老牌 Three.js 封装，直接给 `OccupancyGridClient`、`UrdfClient`，维护一般但够用。
- **robot-web-tools 全家桶**：roslibjs + ros2djs + ros3djs，示例多，适合快速原型。

## 常见坑速查

| 问题 | 解法 |
|---|---|
| rosbridge 连不上 | 确认 9090 端口开放；`ros2 node list` 看 rosbridge 在不在；容器部署要映射端口 |
| 页面卡死 | 高频 topic 未节流直接 setState；点云每帧新建 Float32Array |
| 图像黑屏/延迟大 | rosbridge 传 raw image 带宽不够；换 `compressed` 传输或 web_video_server/WebRTC |
| TF 变换报错 | 浏览器端 TF 树缺静态变换；确保订阅 `/tf_static` 且用 `is_static` 区分 |
| 地图显示偏移 | OccupancyGrid 的 origin 没应用；注意 canvas y 轴翻转 |
| 多页面状态不一致 | RosConnection 做成模块级单例，别每个组件各连一份 |

## References

- `references/rosbridge_integration.md` — rosbridge/foxglove_bridge 接入、订阅节流、地图/点云渲染、teleop 实现模式与代码骨架
