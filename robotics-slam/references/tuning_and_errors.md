# SLAM 调参与报错排查

## 前置检查（任何问题先查这五项）

```bash
ros2 run tf2_tools view_frames        # TF 树无断点，map→odom→base_link→sensor
ros2 topic hz /scan                   # 激光 ≥10 Hz
ros2 topic hz /imu/data               # LIO ≥200 Hz，视觉惯性 ≥100 Hz
ros2 topic echo --no-arr /scan | grep stamp   # 时间戳是采集时间且单调
ros2 bag info <bag>                   # 离线排查时确认话题、频率、时长
```

## 现象 → 原因 → 参数（slam_toolbox）

| 现象 | 原因 | 调整 |
|---|---|---|
| 地图重影/双层墙 | 外参错或匹配失败 | 先查外参；增大 `correlation_search_space_dimension` 与 `sm_search_window` |
| 原地旋转后地图糊 | 角度搜索窗太小 / 扫描匹配发散 | 增大 `correlation_search_space_sm deviation`（角度）；检查 odom 角速度是否可信 |
| 走直线漂移 | 轮速计没接入或权重错 | 检查 `/odom` 协方差；slam_toolbox 本身融合有限，必要时前置 robot_localization |
| 回环不触发 | 回环搜索距离/链太小 | 减小 `loop_search_minimum_distance`；增大 `loop_match_minimum_chain_size` 之外的搜索范围 |
| 误回环拉歪地图 | 相似环境误判 | 增大 `loop_match_minimum_response_fine`（更严格） |
| 建图内存爆炸 | 图节点太多 | 增大 `minimum_travel_distance` / `minimum_travel_heading` 减少节点 |

## 现象 → 原因（LIO 系：LIO-SAM / FAST-LIO）

| 现象 | 原因 | 调整 |
|---|---|---|
| 启动即漂 | 外参/重力方向错；IMU 零偏太大 | 重标激光-IMU 外参；静止初始化时间加长 |
| 快速旋转时发散 | 时间偏差；IMU 噪声参数过小（过度信任） | 标 td；调大 `gyr_noise`/`acc_noise` |
| 走廊里沿走向滑 | 几何退化 | 紧耦合轮速计/GPS；换 ikd-Tree 类（FAST-LIO2）也救不了纯退化，加传感器 |
| z 方向缓慢漂移 | IMU 加速度计零偏；重力估计错 | 重标 IMU；LIO-SAM 加 GPS 或 floor 约束 |
| 点云拖影 | 运动畸变未补偿（deskew 关闭或 odom 频率低） | 开 deskew；提高 IMU 频率 |

## 现象 → 原因（视觉系：ORB-SLAM3）

| 现象 | 原因 | 调整 |
|---|---|---|
| 特征点稀疏跟踪丢失 | 光照差/弱纹理 | 提高 `nFeatures`；补光；换事件相机或加激光 |
| 尺度漂移（单目） | 单目固有问题 | 换双目/RGB-D 或视觉-惯性模式 |
| 初始化失败 | 视差不足 | 初始化时做平移运动而非纯旋转 |
| 频繁重定位 | 地图点太少/动态物体 | 滤动态物体；提高关键帧密度 |

## 常见报错速查

| 报错 | 解法 |
|---|---|
| `Lookup would require extrapolation into the future` | TF 与消息时间戳不同步；开 `use_sim_time` 一致性检查；`tf2` buffer 加大 |
| slam_toolbox `Laser has to be mounted planar` | 激光未水平安装且未做转换；用 `laser_filters` 或将雷达放平 |
| Cartographer 卡在 `Not yet started odometry` | odom 话题名/frame_id 与配置不一致 |
| LIO-SAM 点云全在原地堆叠 | IMU 与激光 frame 约定错（LIO-SAM 要求 lidar 系数据且 IMU 转到 lidar 系） |
| ORB-SLAM3 段错误 | OpenCV/Pangolin 版本冲突；用仓库指定版本重编 |

## 地图质量验收清单

- [ ] 闭环回原点：位置误差 < 场景对角线的 0.5%
- [ ] 墙体无重影、无拉丝
- [ ] 保存的栅格地图边缘整齐，无明显鬼影区域
- [ ] 定位模式 30 min 运行无跳变、无丢失
