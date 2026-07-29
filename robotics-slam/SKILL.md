---
name: robotics-slam
description: SLAM（同步定位与建图）开发助手。当用户进行机器人建图、定位、导航前端的开发或调试时使用，涵盖激光/视觉/多传感器 SLAM 方案选型、传感器标定（内外参、时间同步）、slam_toolbox/Cartographer/LIO-SAM/ORB-SLAM3 等主流方案部署与调参、回环与地图优化、定位漂移排查。触发词示例：SLAM、建图、定位漂移、回环检测、激光 SLAM、视觉 SLAM、标定、slam_toolbox、Cartographer、LIO-SAM、map 与 odom 跳变。
license: LICENSE.txt
---

# Robotics SLAM

## Overview

Assist with SLAM development and debugging on ROS/ROS 2: choosing a SLAM approach for the robot and environment, calibrating sensors (extrinsics, time sync), deploying and tuning mainstream SLAM stacks, and diagnosing map corruption and localization drift.

> 版本基准：ROS 2 Humble。算法上游是否原生支持 ROS 2、社区移植质量以及点云字段约定必须
> 分开核验；本技能不会把一个存在 ROS 2 fork 的项目写成“上游原生 ROS 2”。

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
| 3D 室外/大场景、多线激光 + IMU | 选择经过目标 ROS 2 发行版验证的 LIO-SAM/FAST-LIO2 移植或其他 LIO；GPS/回环能力需单独核对 |
| 视觉为主、纹理丰富 | ORB-SLAM3（单/双/RGB-D/鱼眼，视觉-惯性） |
| RGB-D 室内、需要稠密地图 | RTAB-Map |

完整选型维度（传感器配置、算力、场景动态性）见 `references/slam_selection.md`。

## Step 2: 传感器标定

按依赖顺序做，任何一步错了后面全错：

1. **时钟与时间戳**：优先硬件触发、PPS/PTP 或同一硬件时钟；`message_filters` 只能按已有 stamp 配对消息，不能校正时钟或估计固定偏移。
2. **IMU 特性**：Allan 方差工具用于估计噪声密度和 bias instability/random walk；零偏、尺度因子与轴不正交需要相应的静态多姿态、转台或厂家标定流程。
3. **相机内参**：`ros2 camera_calibration`，或在隔离的 ROS 1/Docker/离线转换流程中使用
   kalibr；用覆盖视场的独立验证图像和任务误差预算验收。
4. **外参**：按传感器和运行栈选工具。LI-Calib 上游只覆盖 ROS 1 + VLP-16；Livox
   Avia/Mid-360 可评估仍属 ROS 1 catkin 的 LI-Init；ROS 2 必须使用经过验证的 port 或隔离离线
   流程。激光-相机可评估支持 ROS 2 的 direct_visual_lidar_calibration。
5. **轮速计标定**：直线测轮径、原地旋转测轮距。

详细流程与命令见 `references/calibration.md`。

## Step 3: 部署与调参

通用检查顺序（先排系统输入，再动算法参数）：

1. **TF 树完整**：`map → odom → base_link → sensor`，`ros2 run tf2_tools view_frames` 确认无断点。
2. **话题频率达标**：用 `ros2 topic hz` 与驱动配置核对实际频率；最低要求由算法、运动速度和硬件数据表共同决定。
3. **时间戳语义正确**：原始传感器 header 通常应表示采集/测量时刻；对照消息与驱动契约确认，
   不用接收回调的 `now()` 无条件覆盖硬件时间。
4. 再进入算法参数调整：`references/tuning_and_errors.md` 按「现象 → 参数」组织。

## Step 4: 接入导航链路

1. **给 AMCL/显示用的栅格地图**：运行
   `ros2 run nav2_map_server map_saver_cli -f /absolute/path/my_map`，产物是
   yaml/pgm（或其他配置的图像格式），不包含 slam_toolbox posegraph。
2. **给 slam_toolbox localization/continued mapping 用的图**：在建图节点仍可序列化时运行
   `ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph
   "{filename: /absolute/path/my_map}"`，保存 posegraph/data；定位配置使用
   `mode: localization` 与 `map_file_name: /absolute/path/my_map`，再启动
   `localization_slam_toolbox_node`。先用本机 `ros2 interface show
   slam_toolbox/srv/SerializePoseGraph` 核对目标安装的接口。
3. AMCL 读取静态 yaml/pgm；slam_toolbox localization 读取序列化 posegraph。按定位方案二选一，
   验证 `map→odom` 只有一个发布者。
4. 记录回环/重定位前后创新量。合法的回环可能产生离散修正，是否异常应结合协方差、匹配分数和
   任务容差判断，不能只用固定跳变阈值；再接入 Nav2，局部代价地图用 `odom` 系，全局用 `map` 系。

## References

- `references/slam_selection.md` — 各 SLAM 方案对比与选型决策
- `references/calibration.md` — 时间同步与各传感器标定流程
- `references/tuning_and_errors.md` — 现象驱动的调参表与常见报错排查
