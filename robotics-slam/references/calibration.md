# 传感器标定参考

## 0. 时间同步（最先做）

时间不同步是 SLAM 漂移的头号隐形杀手，先排除再谈其他。

- **硬件同步（首选）**：相机/激光用外部触发，IMU 用 PPS 对时；PTP（IEEE 1588）用于激光雷达与主机对时。
- **软同步校验**：让机器人原地快速旋转，看激光点云是否拖影；拖影明显 = 时间偏差大或姿态估计错。
- **测量时间偏差**：kalibr 可估计相机-IMU 时间偏移；LIO 中可用 LI-init 类方法在线标定 td。
- **验收标准**：激光-IMU 偏差 <5 ms；相机-IMU 偏差 <10 ms（视觉惯性紧耦合 <5 ms）。

## 1. IMU 内参

工具：`imu_utils`（需先录静止数据，配合 `allan_variance_ros`）。

1. IMU 静置 ≥2 小时录制原始数据（保持供电稳定、远离振动源）。
2. 用 allan_variance_ros 计算噪声密度与随机游走。
3. 用 imu_utils 标定加速度计/陀螺仪零偏与尺度因子。
4. 结果填入 SLAM 配置：`acc_noise`、`gyr_noise`、`acc_bias`、`gyr_bias`（LIO-SAM/FAST-LIO 参数名不同但对应）。

## 2. 相机内参

```bash
ros2 run camera_calibration cameracalibrator --size 8x6 --square 0.108 \
  image:=/camera/image_raw camera:=/camera
```

- 标定板占画面 1/3 以上，覆盖四角与边缘，各个姿态（倾斜/远近）各 10+ 张。
- 验收：重投影误差 <0.5 px；鱼眼模型 <1.0 px。
- 注意曝光固定、关闭自动对焦。

## 3. 外参

| 组合 | 工具 | 要点 |
|---|---|---|
| 相机-IMU | kalibr |  Aprilgrid 板，激励要充分（六轴都动），结果看重投影误差与估计置信度 |
| 激光-IMU | LI-Calib / FAST-LIO 在线标定 | 充分六自由度激励，避免匀速直线段占比过高 |
| 激光-相机 | direct_visual_lidar_calibration | 无需标定板，靠场景强度-纹理对应 |
| 激光-底盘 | 手工测量 + 建图迭代微调 | 激光到 base_link 的 z 和 yaw 最关键；在平地上正对墙面建图，地图重影最小化即调准 |

外参验收的通用方法：**看地图重影**。机器人绕场一圈回到原点，点云/地图出现双层墙 = 外参（尤其旋转）有错。

## 4. 轮速计标定

1. **轮径**：沿直线推/开 10 m，对比轮速计距离与卷尺距离，等比修正 `wheel_radius`。
2. **轮距**：原地转 10 圈，对比轮速计航向与实测角度（用激光扫描匹配或 Motion Capture 更佳），修正 `wheel_separation`。
3. 差速底盘 odometry 协方差要合理设置（Nav2/robot_localization 融合时权重依据），别用默认值 1e-3 无脑信。

## 5. 标定结果固化

- 外参写入 URDF/xacro（用静态 TF 发布），不要散落在 launch 里手写 `static_transform_publisher` 数字。
- 时间偏移、IMU 噪声参数写入 SLAM 配置文件并加注释标注标定日期。
- 传感器拆装、碰撞后必须重标。
