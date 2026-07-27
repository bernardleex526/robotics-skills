---
name: robotics-slam
description: SLAM（同步定位与建图）开发助手。当用户进行机器人建图、定位、导航前端的开发或调试时使用，涵盖激光/视觉/多传感器 SLAM 方案选型、传感器标定（内外参、时间同步）、slam_toolbox/Cartographer/LIO-SAM/ORB-SLAM3 等主流方案部署与调参、回环与地图优化、定位漂移排查。触发词示例：SLAM、建图、定位漂移、回环检测、激光 SLAM、视觉 SLAM、标定、slam_toolbox、Cartographer、LIO-SAM、map 与 odom 跳变。
agent_created: true
---

# Robotics SLAM

## Overview

Assist with SLAM development and debugging on ROS/ROS 2: choosing a SLAM approach for the robot and environment, calibrating sensors (extrinsics, time sync), deploying and tuning mainstream SLAM stacks, and diagnosing map corruption and localization drift.

## Workflow Decision Tree

- **还没选方案** → Step 1: 方案选型（`references/slam_selection.md`）
- **选了方案但效果差/报错** → Step 3: 调参与排查（`references/tuning_and_errors.md`）
- **多传感器或传感器装调** → Step 2: 标定（`references/calibration.md`）
- **要部署到导航链路**（建图 → 定位 → Nav2）→ Step 4

## Step 1: 方案选型速查

| 场景 | 首选方案 |
|---|---|
| 2D 室内、单线激光、ROS 2 | `slam_toolbox`（在线建图+ lifelong 定位，Nav2 官方集成） |
| 2D 室内、需要子图级优化 | Google Cartographer（调参复杂但效果好） |
| 3D 室外/大场景、多线激光 + IMU | LIO-SAM / FAST-LIO2（紧耦合，配 GPS 用 LIO-SAM） |
| 视觉为主、纹理丰富 | ORB-SLAM3（单/双/RGB-D/鱼眼，视觉-惯性） |
| RGB-D 室内、需要稠密地图 | RTAB-Map |

完整选型维度（传感器配置、算力、场景动态性）见 `references/slam_selection.md`。

## Step 2: 传感器标定

按依赖顺序做，任何一步错了后面全错：

1. **时间同步**：硬件同步（PPS/触发）> 软同步（`message_filters::TimeSynchronizer`）。激光-IMU 时间偏差 >5 ms 时 LIO 必然漂。
2. **IMU 内参**：用 `imu_utils`/`kalibr` 标加速度计与陀螺仪的零偏、尺度因子、噪声密度与随机游走（allan 方差）。
3. **相机内参**：`ros2 camera_calibration` 或 kalibr，重投影误差 <0.5 px。
4. **外参**：激光-IMU 用 LI-Calib；相机-IMU 用 kalibr；激光-相机用 direct_visual_lidar_calibration。
5. **轮速计标定**：直线测轮径、原地旋转测轮距。

详细流程与命令见 `references/calibration.md`。

## Step 3: 部署与调参

通用检查顺序（90% 的 SLAM 问题出在前三项）：

1. **TF 树完整**：`map → odom → base_link → sensor`，`ros2 run tf2_tools view_frames` 确认无断点。
2. **话题频率达标**：`ros2 topic hz`——激光 ≥10 Hz、IMU ≥100 Hz（LIO 需 ≥200 Hz）、图像 ≥15 Hz。
3. **时间戳正确**：消息 header 时间必须是采集时间，不是接收时间；驱动里禁用「用当前时间覆盖」。
4. 再进入算法参数调整：`references/tuning_and_errors.md` 按「现象 → 参数」组织。

## Step 4: 接入导航链路

1. 建图模式跑通后保存地图：`ros2 run nav2_map_server map_saver_cli -f my_map`。
2. 定位模式：slam_toolbox 用 `localization_slam_toolbox_node` + 序列化的 posegraph；AMCL 用静态地图。
3. 验证 `map→odom` 的 TF 由定位节点发布且平滑（跳变 >0.3 m 说明重定位被误触发）。
4. 再接入 Nav2，局部代价地图用 `odom` 系，全局用 `map` 系。

## References

- `references/slam_selection.md` — 各 SLAM 方案对比与选型决策
- `references/calibration.md` — 时间同步与各传感器标定流程
- `references/tuning_and_errors.md` — 现象驱动的调参表与常见报错排查
