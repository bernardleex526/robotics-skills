# rosbridge / 前端接入实现模式

## 桥接器选择

| | rosbridge_suite + roslibjs | foxglove_bridge |
|---|---|---|
| 协议 | rosbridge protocol (JSON 为主) | Foxglove WebSocket（二进制支持好） |
| 前端库 | `roslibjs`（成熟、示例多） | `@foxglove/ws-protocol` + `@foxglove/rosmsg` |
| 带宽效率 | 一般（JSON/base64） | 高（CDR 二进制、压缩） |
| 推荐场景 | 快速原型、资料多 | 点云/图像等大数据、生产环境 |

启动命令：

```bash
# 经典 rosbridge
ros2 launch rosbridge_server rosbridge_websocket_launch.xml   # ws://0.0.0.0:9090

# foxglove bridge（推荐）
ros2 launch foxglove_bridge foxglove_bridge_launch.xml        # 默认 8765
```

## React 连接单例模式

```typescript
// ros/RosConnection.ts — 模块级单例，自动重连
import * as ROSLIB from 'roslib';

class RosConnection {
  ros: ROSLIB.Ros;
  status: 'connecting' | 'connected' | 'closed' = 'connecting';
  private listeners = new Set<(s: string) => void>();
  private retryDelay = 1000;

  constructor(private url: string) { this.connect(); }

  private connect() {
    this.ros = new ROSLIB.Ros({ url: this.url });
    this.ros.on('connection', () => { this.setStatus('connected'); this.retryDelay = 1000; });
    this.ros.on('close', () => {
      this.setStatus('closed');
      setTimeout(() => this.connect(), this.retryDelay);
      this.retryDelay = Math.min(this.retryDelay * 2, 10000); // 指数退避
    });
    this.ros.on('error', () => {});
  }

  onStatus(fn: (s: string) => void) { this.listeners.add(fn); }
  private setStatus(s: any) { this.status = s; this.listeners.forEach(f => f(s)); }
}

export const ros = new RosConnection(
  new URLSearchParams(location.search).get('ros') ?? `ws://${location.hostname}:9090`
);
```

要点：URL 支持 `?ros=ws://ip:9090` 参数覆盖；重连后要重建所有 Topic 订阅（封装 subscribe 方法，内部在 connection 事件后自动重订阅）。

## 高频数据节流 hook

```typescript
// 不要直接 setState(message) —— 30Hz 的 odom 会拖垮 React
function useThrottledTopic<T>(name: string, type: string, hz = 10): T | null {
  const [data, setData] = useState<T | null>(null);
  useEffect(() => {
    let last = 0;
    const topic = new ROSLIB.Topic({ ros: ros.ros, name, messageType: type });
    topic.subscribe((msg: any) => {
      const now = performance.now();
      if (now - last > 1000 / hz) { last = now; setData(msg); }
    });
    return () => topic.unsubscribe();
  }, [name, type, hz]);
  return data;
}
```

3D 渲染场景更进一步：把最新消息存进 ref/zustand store，在 `useFrame` 渲染循环里读，完全绕开 React 状态。

## OccupancyGrid 地图渲染

```typescript
// 关键点：origin 应用 + y 轴翻转 + 值域映射
function drawGrid(ctx: CanvasRenderingContext2D, map: OccupancyGrid) {
  const { width, height } = map.info;
  const img = ctx.createImageData(width, height);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const v = map.data[y * width + x];          // -1 未知, 0-100 占据概率
      const row = height - 1 - y;                  // ROS 原点在左下，canvas 在左上
      const i = (row * width + x) * 4;
      if (v === -1)      { img.data.set([205, 205, 205, 255], i); } // 未知灰
      else if (v > 65)   { img.data.set([0, 0, 0, 255], i); }       // 占据黑
      else               { img.data.set([255, 255, 255, 255], i); } // 空闲白
    }
  }
  ctx.putImageData(img, 0, 0);
  // 世界坐标 → 像素：(wx - origin.x) / resolution，机器人位姿箭头用同一变换
}
```

## 点云渲染（PointCloud2）

- 用 `foxglove_bridge` 时消息可以是二进制，直接 `new Float32Array(buffer)` 解析 x/y/z（按 point_step/fields 偏移）。
- 用 roslibjs 收到的是 base64 → 解码后同上。
- Three.js：`THREE.Points` + `BufferGeometry`，**复用 attribute 数组**，每帧只更新 `position` attribute 并设 `needsUpdate`，绝不每帧 new。
- 点数 >50 万时做体素降采样或按距离抽稀。

## Teleop（cmd_vel 摇杆）

```typescript
// 安全要点：持续定时发送、松开归零、断开即停
function useCmdVel(topicName = '/cmd_vel') {
  const target = useRef({ linear: 0, angular: 0 });
  useEffect(() => {
    const topic = new ROSLIB.Topic({ ros: ros.ros, name: topicName, messageType: 'geometry_msgs/Twist' });
    const timer = setInterval(() => {
      if (ros.status !== 'connected') return;
      topic.publish(new ROSLIB.Message({
        linear:  { x: target.current.linear, y: 0, z: 0 },
        angular: { x: 0, y: 0, z: target.current.angular },
      }));
    }, 100);  // 10 Hz 心跳式发送
    return () => { clearInterval(timer); topic.unadvertise(); };
  }, [topicName]);
  return target; // UI 层：摇杆移动时更新 target.current，松开时归零
}
```

前端配套（机器人端也要做，双保险）：
- 速度上限在前端钳制（如 linear ≤ 0.5 m/s）。
- 连接状态变 `closed` → 立即 `target.current = {linear: 0, angular: 0}` 并弹失联遮罩。
- 页面失焦（visibilitychange）→ 归零。
- 机器人端配 `twist_mux` + velocity timeout，500 ms 无新指令自动停车。

## 图像传输

- 原型：`sensor_msgs/CompressedImage` 直接转 Blob URL 显示。
- 生产：`web_video_server`（HTTP MJPEG，`<img>` 直接用）或 WebRTC（低延迟）；别用 rosbridge 传 raw image。

## TF 在浏览器端

- 订阅 `/tf` 和 `/tf_static`（`tf2_web_republisher` 已过时，直接用 rosbridge 订）。
- 维护一棵 TF 树：静态变换持久缓存，动态变换保留最新值 + 时间戳过期清理。
- 查询变换时沿树向上组合四元数/平移；注意右手系，Three.js 与 ROS 同为右手系但 ROS 的 z-up 与 Three.js 默认 y-up 需要统一（通常把 ROS 数据整体挂到一个 `rotation.x = -Math.PI/2` 的父节点下）。
