# SLAM 调参与报错排查

## 前置检查（任何问题先查这五项）

```bash
ros2 run tf2_tools view_frames                  # TF 树无断点，map→odom→base_link→sensor
ros2 topic hz /scan                             # 与驱动配置和算法最低要求对照
ros2 topic hz /imu/data                         # 与目标算法、运动动态和硬件规格对照
ros2 topic echo /scan --field header.stamp      # 观察非零/单调性；采集来源仍须查驱动契约
ros2 bag info <bag>                             # 离线排查时确认话题、频率、时长
```

> `--field header.stamp` 只显示 stamp，但不能证明它来自硬件采集时刻。需要自动统计频率、
> 单调性和可观测 age 时，可配合 `robotics-ros2-infra` 技能；最终仍要核对驱动和硬件时钟配置。

## 现象 → 原因 → 参数（slam_toolbox）

> 参数名核对自上游 `slam_toolbox` README 的 Parameters 章节（见本文末「参数来源」）。调参前先用
> `ros2 param list /slam_toolbox` 确认你的版本确实有该参数——跨版本偶有增删。

| 现象 | 原因 | 调整 |
|---|---|---|
| 地图重影/双层墙 | 外参、时间/deskew、里程计或扫描匹配异常 | 先用录包与残差区分输入问题；需要扩大平移搜索时再调 `correlation_search_space_dimension`，响应面过尖时才评估 `correlation_search_space_smear_deviation` |
| 原地旋转后地图糊 | 角度搜索范围/分辨率不足，或 odom 角速度不可信 | 增大 `coarse_search_angle_offset` 与 `fine_search_angle_offset`（角度搜索范围，rad）；减小 `coarse_angle_resolution`（角度搜索步长）；同时核对 `/odom` 的角速度符号与量级 |
| 旋转时匹配被 odom 拖走 | 角度先验惩罚过强或 odom 错 | 先修 odom；按 Karto 评分公式，增大 `angle_variance_penalty` 会减弱给定角度差的惩罚，修改后必须用同一录包比较误匹配率 |
| 走直线漂移 | `odom→base` 里程计尺度、漂移、时间或 TF 所有权异常 | slam_toolbox 通过 TF 查询里程计，不读取 `nav_msgs/msg/Odometry` 协方差；检查 TF 尺度/方向/时延与唯一发布者。协方差只会影响另行配置的融合/下游节点 |
| 回环不触发 | 回环搜索半径太小 / 链长门槛太高 / 回环没开 | 确认 `do_loop_closing: true`；**增大** `loop_search_maximum_distance`（搜索半径，m）；减小 `loop_match_minimum_chain_size`（参与匹配的最小节点链长） |
| 误回环拉歪地图 | 相似环境误判 | 增大 `loop_match_minimum_response_fine`（精匹配响应门槛，更严格）；增大 `loop_match_minimum_response_coarse`；减小 `loop_match_maximum_variance_coarse` |
| 建图内存爆炸 | 图节点太多 | 增大 `minimum_travel_distance` / `minimum_travel_heading` 减少关键帧节点；仅在 synchronous mode 中才评估调大 `minimum_time_interval` |
| 地图占据/空闲判定不合预期 | 栅格化证据门槛 | 调 `occupancy_threshold`（占据概率门槛）；`min_pass_through` 是 cell 标成 occupied 或 unoccupied 前需要的 beam passes，会同时影响两类证据累积 |

**易错点**：`loop_search_maximum_distance` 是「最大」搜索距离，想让回环更容易被触发要**增大**它，不是减小。
早期文档里流传的 `loop_search_minimum_distance` 与 `sm_search_window` **在 slam_toolbox 中不存在**，不要照着调。<!-- param-check: allow-mention -->

## 现象 → 原因（LIO 系：LIO-SAM / FAST-LIO2）

> **两者参数命名风格不同，不要混用**：LIO-SAM 用 camelCase（`config/params.yaml`），
> FAST-LIO2 用 snake_case（`config/*.yaml`）。下表给出双方对应名。

| 现象 | 原因 | LIO-SAM 调整 | FAST-LIO2 调整 |
|---|---|---|---|
| 启动即漂 | 外参/IMU 坐标约定错；零偏未收敛 | 重标 `extrinsicRot` / `extrinsicRPY` / `extrinsicTrans`；`imuGravity` 是正的重力大小，重点核对 IMU 轴向、单位与外参约定 | 重标 `extrinsic_R` / `extrinsic_T`；`extrinsic_est_en` 只能在运动可观测时辅助估计，不能替代验收 |
| 快速旋转时发散 | 时间偏差；IMU 噪声设得过小 | 先标时间偏移，再依据数据表/Allan 结果核对 `imuGyrNoise` / `imuAccNoise` | 优先统一硬件时钟并标定 `time_offset_lidar_to_imu`；上游把 `time_sync_en` 标为无更好同步手段时的最后选择；再核对 `gyr_cov` / `acc_cov` |
| 零偏漂移累积 | 零偏随机游走建模过小 | 调大 `imuAccBiasN` / `imuGyrBiasN` | 调大 `b_acc_cov` / `b_gyr_cov` |
| 走廊/隧道沿走向滑 | 当前观测几何退化 | 量化退化方向；可调整运动激励、使用环境先验/地面约束，或融合轮速计/GNSS/其他传感器 | 同左，并验证外接约束的时间、外参与协方差 |
| z 方向缓慢漂移 | 加速度计零偏；重力估计错 | 重标 IMU；若接 GPS，`gpsTopic` 应提供目标移植版契约要求、由 NavSat 转换且协方差可信的 GPS odometry；结合 `gpsCovThreshold` / `poseCovThreshold` 验收，只有高度可靠时才启用 `useGpsElevation`，否则保留 false；也可使用经验证的地面约束 | 重标 IMU；FAST-LIO2 无 GPS 因子，需外接后端 |
| 点云拖影 | 运动畸变补偿或时空标定异常 | 核对目标分支规定的 IMU/点云频率、每点时间、时间戳单调性与外参 | FAST-LIO2 上游没有独立 deskew 开关，去畸变由 IMU 递推完成；依次检查时间单位/偏移、点字段、外参、IMU 饱和和算法输入频率 |
| 回环不生效 | LIO-SAM 回环未开或候选/ICP 门槛不合适 | `loopClosureEnableFlag: true`；按场景调整 `historyKeyframeSearchRadius`；增大 `historyKeyframeFitnessScore` 会接受更差的 ICP 分数并提高误回环风险，必须结合日志和真值验证 | FAST-LIO2 上游不含闭环后端，需接经验证的外部 PGO/回环组件 |

**易错点**：FAST-LIO 上游 Velodyne/Ouster 的 PointCloud2 配置带 `timestamp_unit`；填错
（s / ms / us / ns）会破坏去畸变。Livox/avia 输入走自己的每点时间字段且示例配置没有这个
参数。先按目标传感器、驱动消息类型和所用分支核对字段/单位，不能把 `timestamp_unit`
当成所有 FAST-LIO2 输入的通用参数。

## 现象 → 原因（视觉系：ORB-SLAM3）

| 现象 | 原因 | 调整 |
|---|---|---|
| 特征点稀疏跟踪丢失 | 光照差/弱纹理或曝光/标定问题 | 先看目标配置中的 `ORBextractor.nFeatures`、`ORBextractor.iniThFAST`、`ORBextractor.minThFAST` 与实际特征分布；再小步调参并检查算力、误匹配与补光方案 |
| 尺度漂移（单目） | 单目固有问题 | 换双目/RGB-D 或视觉-惯性模式 |
| 初始化失败 | 传感器模式对应的初始化条件未满足 | 单目需要足够视差，视觉惯性还需满足目标实现的运动激励；双目/RGB-D 条件不同。对照目标模式日志、标定和初始化器检查，不泛化成固定动作 |
| 频繁重定位 | 跟踪特征/标定/曝光、动态场景或地图质量异常 | 先看跟踪状态、特征分布、标定与动态遮挡；只有目标 fork 明确提供相关控制时才调建图策略，并同时检查算力与冗余 |

## 常见报错速查

| 报错/现象 | 可能原因 | 处理 |
|---|---|---|
| `Lookup would require extrapolation into the future` | TF 与消息时钟/时间戳不一致，或所请求 transform 尚未到达 | 先核对 `use_sim_time`、/clock、主机对时和 stamp；只有确认是网络/调度抖动后才调整 buffer/tolerance |
| slam_toolbox `Laser has to be mounted planar` | 输入扫描无法转换到平面假设所需姿态 | 核对 sensor TF 与输入类型；需要投影时使用有明确误差边界的转换，不要靠改参数掩盖安装姿态 |
| Cartographer 一直等 odometry | `use_odometry = true` 但无 odom，或 frame 配置不一致 | 补齐 odom，或在算法设计允许时置 false；核对 `tracking_frame`、`odom_frame` 与 `published_frame` |
| LIO-SAM 点云原地堆叠 | IMU/激光 frame、外参或每点时间约定错 | 对照目标分支 README 核对 `extrinsicRot` / `extrinsicRPY` / `extrinsicTrans`、点字段与时间单位 |
| ORB-SLAM3 构建/运行崩溃 | 依赖 ABI/API 不匹配或输入配置错误 | 使用目标 fork 锁定的依赖版本并保留完整 backtrace；不要只凭“段错误”断定 OpenCV/Pangolin |
| `Failed to find match for field 'time'`（LIO 系） | 实际点云字段与所用移植版期望不符 | `ros2 interface show` 只显示类型 schema；用 `ros2 topic echo <topic> --once --field fields`、rosbag 或小脚本检查运行时 `PointCloud2.fields[]` 和点数据单位，再按目标分支适配 |

## 地图质量验收清单

- [ ] 用有真值或可重复基准的录包报告 ATE/RPE、闭环误差和失败率，并与任务门槛比较
- [ ] 墙体无重影、无拉丝
- [ ] 保存的栅格地图边缘整齐，无明显鬼影区域
- [ ] 覆盖项目规定的时长、速度、退化区与重定位场景，记录跳变、丢失和恢复时间

## 参数来源

本文参数名核对自以下上游（核对日期 2026-07-29）：

| 项目 | 来源 |
|---|---|
| slam_toolbox | [Humble 上游仓库](https://github.com/SteveMacenski/slam_toolbox/tree/humble) |
| Cartographer | [`cartographer_ros` Configuration](https://google-cartographer-ros.readthedocs.io/en/latest/configuration.html) |
| LIO-SAM | [上游 `config/params.yaml`](https://github.com/TixiaoShan/LIO-SAM/blob/master/config/params.yaml) |
| FAST-LIO2 | [上游 `config/velodyne.yaml`](https://github.com/hku-mars/FAST_LIO/blob/main/config/velodyne.yaml) 与 [`avia.yaml`](https://github.com/hku-mars/FAST_LIO/blob/main/config/avia.yaml) |
| ORB-SLAM3 | [上游示例 YAML](https://github.com/UZ-SLAMLab/ORB_SLAM3/tree/master/Examples) |

完整仓库维护者可从**仓库根目录**运行 `python3 tools/check_doc_params.py`，对照核验日期固定的
人工清单做回归检查；单独安装的 `robotics-slam` 技能不包含仓库级 `tools/`。该工具不会联网
拉取上游，也不能替代目标版本的 `ros2 param list` 和源码核对。
