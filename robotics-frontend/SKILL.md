---
name: robotics-frontend
description: 机器人 Web 前端开发助手。当用户开发机器人相关的 Web 界面时使用，涵盖通过 rosbridge/WebSocket 接入 ROS/ROS 2 数据、Foxglove Studio 与自定义 extension、地图/点云/TF/轨迹可视化、实时状态监控仪表盘、远程操控（teleop）界面开发。触发词示例：机器人前端、机器人仪表盘、rosbridge、roslibjs、Foxglove、webviz、点云可视化、机器人监控页面、远程操控界面、teleop web、robot dashboard。
license: LICENSE.txt
---

# Robotics Frontend

## Overview

Assist with building web frontends for robots: connecting to ROS/ROS 2 over rosbridge/WebSocket, visualizing robot state (TF, map, point cloud, trajectory), building real-time monitoring dashboards, and creating teleoperation UIs. Default stack: React + TypeScript + roslibjs (or @foxglove/rosmsg + WebSocket), Vite for tooling.

## Workflow Decision Tree

- **只要可视化/调试，不写代码** → Path A: Foxglove Studio 现成工具
- **要定制界面（监控页/操控台/交付给客户）** → Path B: 自研 Web 前端（本技能主体）
- **在现有网页里嵌 3D 机器人视图** → Path C: 只集成可视化组件（ros3djs 或自建 Three.js 视图）

## Path A: Foxglove Studio（零代码）

1. 机器人端启动 rosbridge：`ros2 launch rosbridge_server rosbridge_websocket_launch.xml`（默认端口 9090）。
2. Foxglove Studio（桌面版或 app.foxglove.dev）→ Open connection → `ws://<robot-ip>:9090`。
3. 需要原生高性能（点云大、bag 回放）用 Foxglove 桌面版 + `foxglove_bridge`（比 rosbridge 带宽效率高，支持压缩）。

## Path B: 自研前端标准流程

### 1. 连接层

- 优先 `foxglove_bridge`（WebSocket，协议更高效，支持 schema 自省）；兼容性优先时用经典 `rosbridge_suite` + `roslibjs`。
- 封装单例 `RosConnection`：自动重连（指数退避）、连接状态事件、topic 订阅管理。参考 `references/rosbridge_integration.md`。
- **必须处理断线**：移动机器人和无线网络存在可预期的断连；UI 要显示连接状态，并验证恢复后的订阅/发布行为。

### 2. 数据流设计

- 高频 topic：按视图刷新率、设备性能和交互延迟预算做**节流/采样**，并在渲染循环外用 ref/zustand transient 更新，避免无意义的 React 高频重渲染。
- 大消息（点云、图像、地图）：点云按 `sensor_msgs/msg/PointCloud2` 的 fields/step/endianness 解析后送 Three.js；图像优先走经过鉴权的 WebRTC/视频服务，避免 rosbridge 传 raw image。
- 地图 `/map`（OccupancyGrid）：只在更新时重绘到 canvas，做 PNG 缓存层。

### 3. 可视化选型

| 内容 | 方案 |
|---|---|
| 完整 rviz 式视图 | 直接用 Foxglove（桌面/网页）而非自研；必须内嵌时用 `ros3djs`，或用 react-three-fiber 自建 |
| 自定义 3D 场景 | Three.js / react-three-fiber 自建（TF 树驱动模型位姿） |
| 2D 地图 + 路径 + 机器人位姿 | canvas/SVG 自绘（OccupancyGrid 渲染 + 箭头），轻量可控 |
| 状态仪表盘 | ECharts/Recharts + MUI/Tailwind |
| URDF 模型展示 | `urdf-loader`（Three.js）+ TF 驱动关节 |

### 4. 操控（teleop）界面

- 虚拟摇杆发 `/cmd_vel`：频率与底盘 watchdog 契约一致；松开时立即发布零值，并在控制会话存续期间按契约发送安全心跳。机器人端必须有有界 command timeout。
- **安全边界**：连接断开/失焦时清零本地目标并显示失联，机器人端负责超时进入安全状态。浏览器按钮只能称“软件停止请求”，不能作为安全额定急停；硬件安全链路、驱动限幅和状态机不得依赖网页。
- 键盘控制：keydown/keyup 状态机，防止按键卡死导致持续运动。

### 5. 部署

- 前端打包后用受维护的 HTTPS/WSS 反向代理部署；`python3 -m http.server` 只用于隔离网络中的短时开发预览。
- 机器人多机/多网段：WebSocket 地址做成可配置（URL 参数或配置文件），别硬编码 IP。
- WebSocket 不使用普通 fetch CORS 流程，但仍要校验 Origin、认证/授权、TLS、网络 ACL 和 topic 白名单；HTTP API 另行配置最小 CORS 策略。

详细代码模式（连接单例、节流 hook、OccupancyGrid 渲染、cmd_vel 摇杆）见 `references/rosbridge_integration.md`。

## Path C: 嵌入现成组件

- **Foxglove 自定义面板**：在 Foxglove 里写 React 面板（`@foxglove/extension`），适合复用现有可视化并补充项目专用交互。
- **ros3djs**：老牌 Three.js 封装，直接给 `OccupancyGridClient`、`UrdfClient`，维护一般但够用。
- **robot-web-tools 全家桶**：roslibjs + ros2djs + ros3djs，示例多，适合快速原型。

## 常见坑速查

| 问题 | 解法 |
|---|---|
| rosbridge 连不上 | 确认 9090 端口开放；`ros2 node list` 看 rosbridge 在不在；容器部署要映射端口 |
| 页面卡死 | 高频 topic 未节流直接 setState；点云每帧新建 Float32Array |
| 图像黑屏/延迟大 | rosbridge 传 raw image 带宽不够；换 `compressed` 传输或 web_video_server/WebRTC |
| TF 变换报错 | 浏览器端 TF 树缺静态变换；按 `/tf` 与 `/tf_static` 的来源分别处理，`tf2_msgs/msg/TFMessage` 没有 `is_static` 字段 |
| 地图显示偏移 | OccupancyGrid 的 origin 没应用；注意 canvas y 轴翻转 |
| 多页面状态不一致 | RosConnection 做成模块级单例，别每个组件各连一份 |

> roslibjs 同时服务 ROS 1/ROS 2 生态，message type 字符串兼容性受 rosbridge 版本影响。
> 本技能示例使用 ROS 2 规范名；接入前用目标桥接器做一次订阅/发布契约测试。

## References

- `references/rosbridge_integration.md` — rosbridge/foxglove_bridge 接入、订阅节流、地图/点云渲染、teleop 实现模式与代码骨架

## 按需扩展与复用边界

- 仅在明确相关的机器人任务中使用本技能；通用代码/网页/文案工作不加载机器人参考资料。
- 按当前故障读取单个参考文件，不预读整个知识库。脚本路径相对技能目录，运行时解析成绝对路径。
- 新架构、算法替换或明显重复实现前，使用可用的在线搜索核验论文及作者代码；若已安装可选的 `robotics-research-discovery`，可按需读取。小修复不强制联网。无网明确声明未核验，不能声称最新或无现成实现。
- 本模块的补充检查见 `references/review_addendum.md`，仅在涉及其中问题时读取。
