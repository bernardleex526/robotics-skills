# Nav2 Humble Costmap 与插件参考

> 基准：ROS 2 Humble / Nav2 humble 分支。以下是结构示例，不是可直接套用的整车参数。
> footprint、传感器范围、速度和代价梯度必须用目标机器人测量值替换。

## Layered Costmap

```yaml
global_costmap:
  global_costmap:
    ros__parameters:
      global_frame: map
      robot_base_frame: base_link
      resolution: 0.05
      track_unknown_space: true
      footprint: "[[0.30, 0.20], [0.30, -0.20], [-0.30, -0.20], [-0.30, 0.20]]"
      plugins: [static_layer, obstacle_layer, inflation_layer]

      static_layer:
        plugin: "nav2_costmap_2d::StaticLayer"
        map_subscribe_transient_local: true

      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        observation_sources: scan
        scan:
          topic: /scan
          data_type: LaserScan
          marking: true
          clearing: true
          obstacle_max_range: 2.5
          raytrace_max_range: 3.0

      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        inflation_radius: 0.55
        cost_scaling_factor: 3.0
```

这些数字仅展示字段位置。设计时分别计算：

1. footprint：实体包络、常驻载荷和允许的制造误差；
2. obstacle/raytrace range：传感器可靠范围和清除模型；
3. inflation：定位误差、跟踪误差、制动距离与期望间隙；
4. local window：至少覆盖停止/绕障所需的前视范围。

层按照列表顺序更新，但每层的 combination method/实现决定具体合并方式。inflation 通常放在
产生障碍代价的层之后。若同时使用 obstacle 与 voxel layer，要明确它们是否服务不同传感器，
避免对同一数据重复标记而无法正确清除。

## Planner 参数归属

```yaml
planner_server:
  ros__parameters:
    planner_plugins: [GridBased]
    GridBased:
      plugin: "nav2_navfn_planner/NavfnPlanner"
      tolerance: 0.5
      use_astar: false
      allow_unknown: true
```

`tolerance` 和 `allow_unknown` 属于这里的 NavFn planner 实例，不属于 global costmap。
是否允许未知区域由任务决定；已知环境运行时通常需要更保守的地图语义。

## Controller 选择门槛

同为 Humble 的安装也可能缺少后续加入或回补的 controller 包。使用 MPPI 前先运行
`ros2 pkg prefix nav2_mppi_controller`；找不到包就不能仅凭下面的 plugin 字符串假定可用。

| Controller | Humble plugin 字符串 | 先验证 |
|---|---|---|
| DWB | `dwb_core::DWBLocalPlanner` | velocity samples、critics、最坏计算时间 |
| RPP | `nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController` | 曲率、lookahead、碰撞检测时域 |
| MPPI | `nav2_mppi_controller::MPPIController` | 模型、采样批量、critics、CPU 余量 |

不能只凭“动态障碍”选 MPPI：局部 costmap 的观测语义、预测模型、更新率与控制器计算预算共同决定效果。

## 版本检查

Humble 常见 pluginlib 字符串同时存在 `/` 与 `::` 风格，取决于插件和当时的导出名；后续 Nav2
版本逐步统一。复制配置前用目标发行版的
[`nav2_params.yaml`](https://github.com/ros-navigation/navigation2/blob/humble/nav2_bringup/params/nav2_params.yaml)
和插件文档核对，不要跨发行版拼接。

参考：

- [Costmap 2D 配置](https://docs.nav2.org/configuration/packages/configuring-costmaps.html)
- [Inflation layer](https://docs.nav2.org/configuration/packages/costmap-plugins/inflation.html)
