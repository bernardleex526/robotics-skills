# rosbridge / 前端接入实现模式

## 桥接器选择

| | rosbridge_suite + roslibjs | foxglove_bridge |
|---|---|---|
| 协议 | rosbridge protocol (JSON 为主) | Foxglove WebSocket（二进制支持好） |
| 前端库 | `roslibjs`（成熟、示例多） | `@foxglove/ws-protocol` + `@foxglove/rosmsg` + `@foxglove/rosmsg2-serialization` |
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

下面的 TypeScript 以 `roslib >= 2` 为基准。`ROSLIB.Ros` 可以在 close 后再次调用
`connect(url)`。保留同一个 Ros 实例，已创建的
`ROSLIB.Topic` 在显式设置 `reconnect_on_close: true` 时会注册重连回调并恢复订阅/advertise。
若每次重连都新建 Ros，旧 Topic 才会永久绑定在旧连接上。

```typescript
// ros/RosConnection.ts — 复用同一 Ros 对象
import * as ROSLIB from 'roslib';

type Status = 'connecting' | 'connected' | 'closed';
type Handler = (msg: any) => void;

class RosConnection {
  status: Status = 'connecting';

  readonly ros = new ROSLIB.Ros();
  // roslib Topic 内部只有一套 reconnect bookkeeping；发布与订阅不能共用实例。
  private subscriberTopics = new Map<string, ROSLIB.Topic>();
  private publisherTopics = new Map<string, ROSLIB.Topic>();
  private statusListeners = new Set<(s: Status) => void>();
  private retryDelay = 1000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(private url: string) {
    this.ros.on('connection', () => {
      this.retryDelay = 1000;
      this.setStatus('connected');
    });
    this.ros.on('close', () => {
      this.setStatus('closed');
      this.scheduleReconnect();
    });
    this.ros.on('error', (error) => console.warn('[ros] socket error', error));
    this.connect();
  }

  private connect() {
    this.reconnectTimer = null;
    this.setStatus('connecting');
    // 新版 roslibjs 返回 Promise；Promise.resolve 也兼容旧版的 void 返回值。
    void Promise.resolve(this.ros.connect(this.url)).catch((error) => {
      console.warn('[ros] connect failed', error);
      this.setStatus('closed');
      this.scheduleReconnect();
    });
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;          // 防重复定时器
    this.reconnectTimer = setTimeout(() => this.connect(), this.retryDelay);
    this.retryDelay = Math.min(this.retryDelay * 2, 10000);  // 指数退避，上限 10 s
  }

  private topic(
    cache: Map<string, ROSLIB.Topic>,
    name: string,
    messageType: string,
  ): ROSLIB.Topic {
    const key = `${name}|${messageType}`;
    let topic = cache.get(key);
    if (!topic) {
      topic = new ROSLIB.Topic({
        ros: this.ros,
        name,
        messageType,
        reconnect_on_close: true,
      });
      cache.set(key, topic);
    }
    return topic;
  }

  subscribe(name: string, messageType: string, handler: Handler): () => void {
    const topic = this.topic(this.subscriberTopics, name, messageType);
    topic.subscribe(handler);
    return () => topic.unsubscribe(handler);
  }

  publish(name: string, messageType: string, msg: object) {
    if (this.status !== 'connected') return;
    // roslib 2.x 不再导出 Message；Topic.publish() 直接接收普通消息对象。
    this.topic(this.publisherTopics, name, messageType).publish(msg);
  }

  onStatus(fn: (s: Status) => void): () => void {
    this.statusListeners.add(fn);
    fn(this.status);                                  // 立即同步当前状态
    return () => { this.statusListeners.delete(fn); };
  }

  private setStatus(s: Status) {
    this.status = s;
    this.statusListeners.forEach((f) => f(s));
  }
}

function bridgeUrl(): string {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  const raw = new URLSearchParams(location.search).get('ros')
    ?? `${scheme}://${location.hostname}:9090`;
  const parsed = new URL(raw);
  if (parsed.protocol !== 'ws:' && parsed.protocol !== 'wss:') {
    throw new Error(`Unsupported ROS bridge protocol: ${parsed.protocol}`);
  }
  return parsed.toString();
}

export const ros = new RosConnection(bridgeUrl());
```

要点：

- URL 支持 `?ros=ws://ip:9090` 或 `?ros=wss://host/path` 覆盖，别硬编码 IP。HTTPS 页面必须
  通过带 TLS 的 bridge 或反向代理使用 `wss://`，否则浏览器会按 mixed content 拒绝连接。
- `onStatus` 注册时立即回调一次当前状态，避免组件挂载晚于 `connection` 事件而永远显示「连接中」。
- 不要在 connection 回调里手工重复 subscribe，否则会产生重复回调；组件卸载时必须 unsubscribe。
- 若目标 roslibjs 版本没有 `reconnect_on_close`，先核对该版本 API，再由包装层显式维护重订阅。
- 自建 Foxglove WebSocket 客户端时，`@foxglove/rosmsg` 只负责解析消息定义；ROS 2 的
  `cdr` payload 还要用 `@foxglove/rosmsg2-serialization` 反序列化，并按 channel encoding
  分派，不能把 binary frame 直接强转成 ROS 消息。

## 高频数据节流 hook

两个坑：不要让消息频率直接决定 React render 频率，以及不要丢尾帧。具体性能取决于组件树、
消息大小和设备；先 profiling，再选择 throttle/debounce/store 策略。

```typescript
import { useCallback, useEffect, useRef, useState } from 'react';
import { ros } from './ros/RosConnection';

// 前沿立即出，尾帧用定时器补齐
function useThrottledTopic<T>(name: string, type: string, hz = 10): T | null {
  const [data, setData] = useState<T | null>(null);

  useEffect(() => {
    const interval = 1000 / hz;
    let last = 0;
    let pending: T | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const flush = () => {
      timer = null;
      if (pending !== null) { last = performance.now(); setData(pending); pending = null; }
    };

    // 同一个 Ros/Topic 会在重连后恢复订阅
    const unsubscribe = ros.subscribe(name, type, (msg: T) => {
      const now = performance.now();
      const wait = interval - (now - last);
      if (wait <= 0) { last = now; setData(msg); pending = null; }
      else { pending = msg; if (!timer) timer = setTimeout(flush, wait); }  // 尾帧补齐
    });

    return () => { unsubscribe(); if (timer) clearTimeout(timer); };
  }, [name, type, hz]);

  return data;
}
```

订阅走 `ros.subscribe()` 后，effect 的依赖数组保持 `[name, type, hz]`；重连复用原 Ros/Topic，
组件层不需要因连接状态变化重复注册。

**连接状态**单独用一个 hook 取，用于显示失联遮罩：

```typescript
function useRosStatus() {
  const [status, setStatus] = useState(ros.status);
  useEffect(() => ros.onStatus(setStatus), []);   // onStatus 返回注销函数
  return status;
}
```

3D 渲染场景更进一步：把最新消息存进 ref/zustand store，在 `useFrame` 渲染循环里读，完全绕开 React 状态。

## OccupancyGrid 地图渲染

```typescript
// 第一步只生成 grid-local 像素：值域映射 + canvas y 轴翻转
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
}

// 第二步把世界坐标逆变换到 OccupancyGrid 局部坐标。
// origin.orientation 不能省略；下面针对平面地图取 yaw。
function worldToPixel(wx: number, wy: number, map: OccupancyGrid) {
  const { origin, resolution, height } = map.info;
  const q = origin.orientation;
  const yaw = Math.atan2(
    2 * (q.w * q.z + q.x * q.y),
    1 - 2 * (q.y * q.y + q.z * q.z),
  );
  const dx = wx - origin.position.x;
  const dy = wy - origin.position.y;
  const gx = ( Math.cos(yaw) * dx + Math.sin(yaw) * dy) / resolution;
  const gy = (-Math.sin(yaw) * dx + Math.cos(yaw) * dy) / resolution;
  // origin 是 cell(0,0) 的左下边界；连续 overlay 的原点映到 canvas 下边界 height。
  return { x: gx, y: height - gy };
}
```

若把地图作为 Three.js 平面放进世界坐标，还要把 origin 的完整 pose 应用到平面节点；不要既变换
平面又对 overlay 重复应用 origin。

## 点云渲染（PointCloud2）

- 先按桥接协议反序列化成 `sensor_msgs/msg/PointCloud2`；Foxglove WebSocket binary frame 不是可直接当点数组使用的裸 payload。
- 根据 `fields` 找 x/y/z 的 offset 和 datatype；按 `height`、`row_step`、`width`、`point_step` 遍历，用 `DataView` 按 `is_bigendian` 解码。字段可能交错、未对齐，也可能不是 FLOAT32。
- roslibjs/base64 路径也要先取得消息 `data` 的字节，再走同一字段驱动解码；过滤 NaN/Inf，并尊重 organized cloud 的 row padding。
- Three.js：`THREE.Points` + `BufferGeometry`，**复用 attribute 数组**，每帧只更新 `position` attribute 并设 `needsUpdate`，绝不每帧 new。
- 渲染到固定 frame 前，按 `msg.header.frame_id` 和 `msg.header.stamp` 查询对应时刻的 TF；移动平台
  上用 latest transform 会把旧点云投到新姿态。查不到该时刻变换时按有界队列策略等待或丢帧。
- 当点数、更新率或 GPU 上传超过渲染预算时，在机器人端/桥接端降采样或按可视范围抽稀；阈值用目标设备 profiling 决定。

FLOAT32 xyz 的最小骨架：

```typescript
const offset = (msg: PointCloud2, name: string) => {
  const field = msg.fields.find((item) => item.name === name);
  if (!field || field.datatype !== 7) throw new Error(`${name} is not FLOAT32`);
  if (!Number.isSafeInteger(field.offset) || field.offset < 0
      || field.offset + 4 > msg.point_step) {
    throw new Error(`${name} offset exceeds point_step`);
  }
  return field.offset;
};

// xyz 是调用方持有并复用的 Float32Array；容量至少 width*height*3。
function readXYZ(msg: PointCloud2, bytes: Uint8Array, xyz: Float32Array): number {
  for (const [name, value] of Object.entries({
    width: msg.width, height: msg.height,
    point_step: msg.point_step, row_step: msg.row_step,
  })) {
    if (!Number.isSafeInteger(value) || value < 0) throw new Error(`invalid ${name}`);
  }
  if (msg.width * msg.height > 0 && msg.point_step <= 0) {
    throw new Error('point_step must be positive for a non-empty cloud');
  }
  if (msg.row_step < msg.width * msg.point_step) throw new Error('row_step too small');
  if (!Number.isSafeInteger(msg.row_step * msg.height)
      || bytes.byteLength < msg.row_step * msg.height) {
    throw new Error('PointCloud2 data is truncated');
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const littleEndian = !msg.is_bigendian;
  const ox = offset(msg, 'x'), oy = offset(msg, 'y'), oz = offset(msg, 'z');
  if (xyz.length < msg.width * msg.height * 3) throw new Error('xyz buffer too small');
  let used = 0;
  for (let row = 0; row < msg.height; row++) {
    for (let col = 0; col < msg.width; col++) {
      const base = row * msg.row_step + col * msg.point_step;
      const x = view.getFloat32(base + ox, littleEndian);
      const y = view.getFloat32(base + oy, littleEndian);
      const z = view.getFloat32(base + oz, littleEndian);
      if (Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)) {
        xyz[used++] = x; xyz[used++] = y; xyz[used++] = z;
      }
    }
  }
  return used / 3; // geometry.setDrawRange(0, pointCount)，并标记 attribute.needsUpdate
}
```

尺寸变化时可在消息处理循环外扩容 buffer/attribute；稳定尺寸下每帧复用。上面的解析只得到
传感器 frame 内的点，仍须用该消息时刻的 TF 变换后再显示。

## Teleop（cmd_vel 摇杆）

```typescript
// 安全要点：持续定时发送；松开/取消/失焦时清目标并在连接仍在时立即发零
// 注意 messageType 用 ROS 2 规范写法 geometry_msgs/msg/Twist（带 /msg/）
const clamp = (v: number, lim: number) => Math.max(-lim, Math.min(lim, v));

function useCmdVel(
  limits: { linear: number; angular: number },
  controlEnabled = false,
  topicName = '/cmd_vel',
  hz = 10,
) {
  if (!Number.isFinite(hz) || hz <= 0) throw new Error('hz must be positive');
  if (limits.linear < 0 || limits.angular < 0) throw new Error('limits must be non-negative');
  const target = useRef({ linear: 0, angular: 0 });

  const publishTwist = useCallback((linear: number, angular: number) => {
    ros.publish(topicName, 'geometry_msgs/msg/Twist', {
      linear:  { x: clamp(linear, limits.linear), y: 0, z: 0 },
      angular: { x: 0, y: 0, z: clamp(angular, limits.angular) },
    });
  }, [limits.linear, limits.angular, topicName]);

  // UI 的 pointerup/pointercancel/lostpointercapture/keyup 必须直接调用 stop()。
  const stop = useCallback(() => {
    target.current = { linear: 0, angular: 0 };
    // 只由当前控制会话发送 stop；空闲监控页不能持续用零值抢占别的控制源。
    if (controlEnabled) publishTwist(0, 0);
  }, [controlEnabled, publishTwist]);

  const setTarget = useCallback((linear: number, angular: number) => {
    if (!controlEnabled) {
      target.current = { linear: 0, angular: 0 };
      return;
    }
    target.current = {
      linear: clamp(linear, limits.linear),
      angular: clamp(angular, limits.angular),
    };
  }, [controlEnabled, limits.linear, limits.angular]);

  useEffect(() => {
    // 只有机器人端 session lease / mux 明确授予控制权后才启动心跳。
    if (!controlEnabled) {
      target.current = { linear: 0, angular: 0 };
      return;
    }

    // 连接已断时零值无法送达；这里只清本地目标，实体停车依赖机器人端命令超时。
    const offStatus = ros.onStatus((s) => { if (s !== 'connected') stop(); });

    // 页面失焦/切后台 → 归零（否则手指离开屏幕但指令还在发）
    const onVis = () => { if (document.hidden) stop(); };
    document.addEventListener('visibilitychange', onVis);
    window.addEventListener('blur', stop);

    const timer = setInterval(() => {
      // Topic 绑定在可复用 Ros 上，重连后恢复发布
      publishTwist(target.current.linear, target.current.angular);
    }, 1000 / hz);  // 10 Hz 心跳式发送

    return () => {
      clearInterval(timer);
      stop();
      offStatus();
      document.removeEventListener('visibilitychange', onVis);
      window.removeEventListener('blur', stop);
    };
  }, [controlEnabled, hz, publishTwist, stop]);

  return { setTarget, stop };
}
```

要点：先由机器人端 session lease/mux 授予唯一控制权，再把 `controlEnabled` 设为 true；
空闲监控页不启动 `/cmd_vel` 心跳。摇杆通过 `setTarget()` 更新目标，不能直接持有可绕过 gate
的 ref。失去控制权时 effect cleanup 在原会话仍有效时发一次零值，随后停止发布。Topic 和 Ros
实例保持稳定；断线期间 `publish()` 丢弃运动命令，恢复后只会发送已经被清零的目标。UI 在
`pointerup`、`pointercancel`、`lostpointercapture`、`keyup` 时调用 `stop()`；组件卸载也调用它。
若 WebSocket 已关闭，这个零值无法到达机器人，因此周期心跳只能与机器人端 watchdog 配套使用。

前端配套（机器人端也要做，双保险）：
- 速度上限在前端钳制（上面 `clamp`），**但不能只靠前端** —— 前端代码可被绕过。
- 连接状态变 `closed` → 归零 + 弹失联遮罩（上面 `onStatus`）。
- 页面失焦（`visibilitychange` / `blur`）→ 归零（上面 `onVis`）。
- 机器人端配 `twist_mux`/控制器 timeout；具体超时由最大速度、制动距离、网络抖动和任务风险决定。
- 多浏览器/多操作者场景必须在机器人端建立 session lease 或命令仲裁，定义单一控制权；多个
  publisher 在普通 ROS topic 上只会交错消息，ACL 和 watchdog 不会自动选出控制者。
- 网页软件停止请求不能称为或替代安全额定 emergency stop。

## 图像传输

- 原型：`sensor_msgs/msg/CompressedImage` 解码后转 Blob URL 显示，并及时 revoke 旧 URL。
- 生产：`web_video_server`（HTTP MJPEG，`<img>` 直接用）或 WebRTC（低延迟）；别用 rosbridge 传 raw image。

## TF 在浏览器端

- 若只需要少量 frame，可用 roslibjs `TFClient` 配合 `tf2_web_republisher` 做选择性转发；它仍是该 API 的工作方式。自建完整视图时可直接订阅 `/tf` 与 `/tf_static`，但要评估带宽，并
  验证桥接器/客户端对 `/tf_static` 的 TRANSIENT_LOCAL late-join 语义；否则页面后打开会缺静态
  变换，此时优先使用已验证的 republisher 路径或显式快照服务。
- 根据**接收 topic**区分静态/动态：`tf2_msgs/msg/TFMessage` 只有 transforms 数组，没有 `is_static` 字段。静态变换持久缓存，动态变换按 stamp/缓存策略更新。
- 查询变换时沿树向上组合四元数/平移；注意右手系，Three.js 与 ROS 同为右手系但 ROS 的 z-up 与 Three.js 默认 y-up 需要统一（通常把 ROS 数据整体挂到一个 `rotation.x = -Math.PI/2` 的父节点下）。

参考：

- [roslibjs Ros](https://robotwebtools.github.io/roslibjs/classes/Ros.html)
- [roslibjs Topic](https://robotwebtools.github.io/roslibjs/classes/Topic.html)
- [roslibjs TFClient](https://robotwebtools.github.io/roslibjs/TFClient.html)
- [Foxglove 自定义面板](https://docs.foxglove.dev/docs/extensions/guides/create-custom-panel)
