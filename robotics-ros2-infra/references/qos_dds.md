# QoS、DDS 与多机诊断

## 先保存 endpoint 证据

```bash
ros2 topic info /scan --verbose
ros2 doctor --report
env | sort | grep -E '^(ROS|RMW|FASTRTPS|CYCLONEDDS)_'
```

记录两端 ROS 发行版、RMW 实现/版本、domain、发现范围、QoS 和网络路径。只看到 topic 名不代表
目标 publisher/subscriber 已匹配；`ros2 topic echo` 能收到也不证明应用订阅者使用相同 QoS。

## QoS 兼容不等于策略合适

- BEST_EFFORT subscriber 可以从 RELIABLE publisher 接收，但是否允许丢样本取决于数据语义。
- TRANSIENT_LOCAL publisher 只有在历史缓存仍保留、subscriber 请求兼容 durability 时才提供历史样本。
- 增大 depth 可能隐藏处理不足，并增加旧命令/旧图像排队延迟。
- Deadline/liveliness 事件用于观测契约，不会自动把机器人带入安全态。

## 多 vendor 与跨 domain

DDS vendor 间存在互操作标准，但 ROS 2 官方不保证所有 vendor/版本/特性组合。生产部署优先同构；
需要混用时至少覆盖：

1. discovery 重启与网络抖动；
2. 各 QoS 组合和大消息分片；
3. service/action 双向调用；
4. rosbag、参数事件、TF 与 lifecycle；
5. 长时间运行后的资源和恢复行为。

不同 `ROS_DOMAIN_ID` 默认不会直接发现。需要跨 domain 时使用经过配置和威胁建模的 DDS Router/
domain bridge，并明确 topic/service/action 白名单。

## 网络诊断顺序

1. 同机、同 RMW、同 domain 建立最小 pub/sub。
2. 同网段两机验证单播/多播和防火墙。
3. 再加入容器、Wi-Fi、VLAN、VPN 或静态 peer。
4. 最后恢复点云/图像等大流量，测丢包、P99 延迟和恢复时间。

不要一开始同时改 QoS、RMW、内核缓冲和网络拓扑，否则无法归因。
