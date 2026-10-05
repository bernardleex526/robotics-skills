> 历史基线指南：模块数和安装说明以仓库根 README 为准。保留原始运行示例供查阅。

# robotics-skills

面向 ROS 2 机器人**系统集成、诊断、部署与实验验证**的 Agent Skills 技能包。
当前版本以 **ROS 2 Humble** 为可执行基准，包含十四个可独立安装的技能：

- 六个系统工作流技能，覆盖运动控制、SLAM、Nav2、ROS 2 基础设施、sim-to-real
  和机器人前端；
- 八个工程技能，覆盖视觉/三维感知、MoveIt、手眼标定、力控、腿足 WBC、论文复现
  和 benchmark；
- 十三个可直接运行的主要工程检查脚本、有效/无效夹具，以及统一 JSON 结果契约。

可移植承诺以**单个 Agent Skill 目录**为单位。本仓库不包含 Codex/Claude 插件 manifest；
把十四个技能作为整包启用时需按客户端逐个安装，不能把“符合 Agent Skills”扩写成“原生插件包”。

八个工程技能提供**工程准入、诊断、配置交叉验证、离线评估与可重复实验约束**。
它们不提供生产算法实现，也不代替真实硬件验收、风险评估或功能安全认证。默认检查
离线、确定性且不访问网络；力控和 WBC 工具只读，不发布控制指令。

## 30 秒选择技能

先按症状选择最小技能集合，不需要一次安装全部十四个。

| 任务或症状 | 首选技能 | 首先检查什么 |
|---|---|---|
| 控制器加载失败、关节不动、PID 振荡、轨迹中止 | [robotics-motion-control](../robotics-motion-control/) | hardware interface、controller lifecycle、单位/符号、日志和闭环证据 |
| 地图漂移、回环异常、LIO 发散、定位链不清楚 | [robotics-slam](../robotics-slam/) | 时间戳、TF、外参、观测退化、地图产物和定位模式 |
| Nav2 规划失败、局部控制振荡、AMCL 或 BT 异常 | [robotics-nav2](../robotics-nav2/) | TF 所有权、costmap、planner/controller、lifecycle 和首个失败日志 |
| 丢消息、QoS 不匹配、executor 阻塞、TF 树异常 | [robotics-ros2-infra](../robotics-ros2-infra/) | topic/TF 健康、QoS、DDS/RMW、callback group、lifecycle |
| 仿真有效但真机失效、动力学或观测不一致 | [robotics-sim2real](../robotics-sim2real/) | 观测、动作、时延、动力学、任务分布和策略产物契约 |
| rosbridge 断线、地图/点云显示错误、teleop 风险 | [robotics-frontend](../robotics-frontend/) | 重连后的订阅、消息布局、坐标变换、控制权和停机边界 |
| 图像编码错误、Image/CameraInfo 不一致、2D 结果异常 | [robotics-vision-perception](../robotics-vision-perception/) | stride/data 长度、光学帧、采集时间戳、配对偏差和 2D 匹配 |
| 点云乱码或 NaN、大小端错误、deskew 输入缺失 | [robotics-3d-perception](../robotics-3d-perception/) | PointCloud2 fields/offset/step、大小端、有限值、time/ring 和 TF |
| MoveIt 配置不一致、能规划但不能执行 | [robotics-manipulation](../robotics-manipulation/) | URDF/SRDF、kinematics、limits、pipeline、controller/action/joint 映射 |
| eye-in-hand 或 eye-to-hand 标定偏差 | [robotics-hand-eye-calibration](../robotics-hand-eye-calibration/) | 坐标定义、样本时间配对、运动可观测性、AX=XB fit 和 holdout |
| 六轴力数据漂移、接触振荡、导纳参数风险 | [robotics-force-control](../robotics-force-control/) | 单位/坐标系、偏置/漂移/饱和、payload/重力、时延和 watchdog |
| 腿足 WBC 模型错位、接触异常、QP 超时 | [robotics-legged-wbc](../robotics-legged-wbc/) | 浮动基、关节顺序、惯量、接触约束、估计器、任务和降级状态 |
| 论文只有分支名和数据目录，结果无法复现 | [robotics-research-reproduction](../robotics-research-reproduction/) | 固定提交、环境锁、数据哈希、seed、baseline、ablation 和证据 |
| Benchmark 丢弃失败样本、覆盖结果或命令不安全 | [robotics-benchmarking](../robotics-benchmarking/) | argv、超时/重复、独立输出目录、原始记录、统计和回归门限 |

组合使用时保持所有权清楚。例如：

- 相机检测链路：`robotics-ros2-infra` 检查 ROS 通信，`robotics-vision-perception`
  检查图像和结果契约，`robotics-benchmarking` 负责可重复运行与统计；
- 机械臂视觉抓取：`robotics-manipulation` 检查 MoveIt，`robotics-hand-eye-calibration`
  检查相机到机械臂变换，`robotics-force-control` 检查接触链；
- 腿足策略落地：`robotics-sim2real` 检查策略与动力学差异，`robotics-legged-wbc`
  检查在线模型/状态/接触控制契约。

## 快速开始

### 1. 获取仓库

```bash
git clone https://github.com/bernardleex526/robotics-skills.git
cd robotics-skills
```

只阅读 `SKILL.md` 和 references 不需要完整 ROS 环境。运行 JSON 类离线检查通常只需
Python 3.10+；读取 YAML 的脚本需要 PyYAML：

```bash
python3 -m pip install "PyYAML>=6.0,<7"
```

仓库维护测试的完整依赖见 `requirements-dev.txt`。

### 2. 安装一个完整技能

以 Codex 用户级技能为例：

```bash
mkdir -p ~/.agents/skills
cp -R robotics-vision-perception ~/.agents/skills/
```

必须复制完整目录，不能只复制 `SKILL.md`。否则 references、scripts、assets、夹具、
结果 schema 和 `LICENSE.txt` 都会缺失。部分客户端需要重启或新建会话后才重新发现技能。

### 3. 在对话中触发

不需要背命令名，直接描述真实任务和证据即可，例如：

> 请用 robotics-vision-perception 检查这份 Image/CameraInfo 快照。先验证编码、
> stride、采集时间戳和 optical frame；如果输入不完整，不要猜。

技能的 frontmatter description 负责触发，`SKILL.md` 决定工作流，references 提供详细
领域知识，scripts 只处理适合确定性检查的部分。

### 4. 不连接硬件运行第一个检查

仓库自带有效和无效夹具。下面的命令验证一份有效相机契约：

```bash
python3 robotics-vision-perception/scripts/check_camera_contract.py \
  robotics-vision-perception/assets/fixtures/camera_valid.json
```

再运行一个已知错误的 stride 夹具，确认 gate 能拒绝错误：

```bash
python3 robotics-vision-perception/scripts/check_camera_contract.py \
  robotics-vision-perception/assets/fixtures/camera_bad_stride.json
```

第二条命令预期以领域失败结束；这正是负例夹具的用途。

### 5. 读懂结果

公共状态是 `pass`、`warn`、`fail`、`skip`：

- `pass`：本次声明的检查项满足门限；
- `warn`：检查完成，没有失败项，但存在需要人工判断的风险；
- `fail`：至少一个领域 gate 或 finding 失败；
- `skip`：显式请求的可选依赖或运行条件不可用，不会伪装成 `pass`。

离线 fixture 的 `pass` 只证明检查器和输入契约成立，**不等于算法效果、实时性、真机安全
或真实硬件验收通过**。

## 十四个技能全景

| 技能 | 主要范围 |
|---|---|
| [robotics-motion-control](../robotics-motion-control/) | ros2_control、控制器接入、PID/轨迹/IK 与控制故障归因 |
| [robotics-slam](../robotics-slam/) | SLAM 选型、时间/外参准入、slam_toolbox 与 LIO/视觉问题归因 |
| [robotics-nav2](../robotics-nav2/) | Nav2 Humble bring-up、costmap、planner/controller、AMCL 与 BT |
| [robotics-ros2-infra](../robotics-ros2-infra/) | QoS、DDS/RMW、lifecycle、composition、executor、测试部署和诊断脚本 |
| [robotics-sim2real](../robotics-sim2real/) | 仿真器版本边界、动力学对齐、SysID/DR 和分阶段真机审查 |
| [robotics-frontend](../robotics-frontend/) | rosbridge/Foxglove、地图/点云/TF、重连、teleop 与 Web 安全边界 |
| [robotics-vision-perception](../robotics-vision-perception/) | Image/CameraInfo 准入、时间/光学帧、2D 检测匹配与部署一致性 |
| [robotics-3d-perception](../robotics-3d-perception/) | PointCloud2 字节布局/大小端、deskew/TF、3D 输出匹配与诊断 |
| [robotics-manipulation](../robotics-manipulation/) | MoveIt 2 URDF/SRDF/kinematics/controller 交叉检查与规划执行隔离 |
| [robotics-hand-eye-calibration](../robotics-hand-eye-calibration/) | eye-in-hand/eye-to-hand、运动可观测性、AX=XB fit/holdout 校验 |
| [robotics-force-control](../robotics-force-control/) | 六轴力传感器、重力补偿、导纳/阻抗、watchdog 与只读安全审查 |
| [robotics-legged-wbc](../robotics-legged-wbc/) | 浮动基模型、状态/接触契约、QP/WBC、求解器门限与失效降级 |
| [robotics-research-reproduction](../robotics-research-reproduction/) | 论文源码/数据/环境溯源、基线、种子、消融和证据完整性 |
| [robotics-benchmarking](../robotics-benchmarking/) | 有界无 shell 执行、原始运行留存、统计聚合和回归门限 |

从系统层次看：

```text
ROS 2 基础设施
├── 运动与执行：motion-control、manipulation、force-control、legged-wbc
├── 状态与导航：slam、nav2、sim2real
├── 数据与感知：vision-perception、3d-perception、hand-eye-calibration
├── 人机接口：frontend
└── 证据与评估：research-reproduction、benchmarking
```

技能之间可以协作，但不存在运行时依赖。安装
`robotics-manipulation` 不要求同时安装 `robotics-motion-control`；
仓库根目录 `tools/` 和 `tests/` 也不属于单个技能的运行依赖。

### 六个系统工作流技能

#### `robotics-motion-control`

- **何时使用**：ros2_control hardware plugin、controller lifecycle、PID、轨迹、IK、
  执行器模式、方向或限位问题。
- **拥有的范围**：通用控制链和执行器诊断；力/位混合与接触控制交给
  `robotics-force-control`。
- **主要入口**：[SKILL.md](../robotics-motion-control/SKILL.md)、
  [ros2_control 参考](../robotics-motion-control/references/ros2_control.md)、
  [PID 整定](../robotics-motion-control/references/pid_tuning.md)。
- **边界**：参数建议必须服从具体硬件、采样率、稳定裕度和安全分析；文档不会授权上电。

#### `robotics-slam`

- **何时使用**：2D/3D LiDAR、视觉或 LIO 建图定位选型，漂移、退化、时间同步、TF、
  外参和地图产物问题。
- **拥有的范围**：SLAM/定位链、传感器标定入口和已知方案的系统级排障。
- **主要入口**：[SKILL.md](../robotics-slam/SKILL.md)、
  [方案选择](../robotics-slam/references/slam_selection.md)、
  [标定](../robotics-slam/references/calibration.md)、
  [调参与错误](../robotics-slam/references/tuning_and_errors.md)。
- **边界**：不实现新的因子图、预积分或回环算法；占据栅格与序列化 pose graph
  被明确区分。

#### `robotics-nav2`

- **何时使用**：Nav2 bring-up、costmap、planner/controller、AMCL、Behavior Tree、
  lifecycle 或 NavigateToPose 失败。
- **拥有的范围**：Humble 导航服务器配置、规划控制职责、定位接入和失败隔离。
- **主要入口**：[SKILL.md](../robotics-nav2/SKILL.md) 及其 `references/`。
- **边界**：规划成功、action server 存在或节点 active 都不是底盘运动成功的证据。

#### `robotics-ros2-infra`

- **何时使用**：QoS、DDS/RMW、domain、executor、callback group、lifecycle、
  composition、launch/testing 或部署问题。
- **拥有的范围**：跨领域 ROS 2 通信和运行基础设施。
- **主要入口**：[SKILL.md](../robotics-ros2-infra/SKILL.md)、
  `scripts/check_tf_tree.py` 和 `scripts/check_topic_health.py`。
- **边界**：脚本报告 TF/话题证据，不替代传感器规格验证、算法精度或 safety case。

#### `robotics-sim2real`

- **何时使用**：仿真策略到真机的观测、动作、动力学、时延和任务分布不一致。
- **拥有的范围**：仿真器版本边界、系统辨识、domain randomization、策略部署契约
  和分阶段审查。
- **主要入口**：[SKILL.md](../robotics-sim2real/SKILL.md)、
  [策略部署契约](../robotics-sim2real/references/policy_deployment_contract.md)。
- **边界**：仿真通过不是实机安全证明；能测量的参数优先辨识，随机化不能掩盖错误接口。

#### `robotics-frontend`

- **何时使用**：rosbridge/Foxglove 接入、TF/地图/点云显示、WebSocket 重连、teleop
  或浏览器控制安全。
- **拥有的范围**：机器人 Web 数据接入、可视化坐标变换、连接生命周期和单一控制权。
- **主要入口**：[SKILL.md](../robotics-frontend/SKILL.md)、
  [rosbridge 集成](../robotics-frontend/references/rosbridge_integration.md)。
- **边界**：浏览器断线后无法保证再发送零指令；急停和通信丢失策略必须由机器人侧实现。

## 适配边界

| 维度 | 当前承诺 |
|---|---|
| ROS | Humble 参数/API 为基线；其他发行版先核对目标版本 |
| 技能格式 | 使用 Agent Skills 的 `SKILL.md` + `references/` + 可选 `scripts/` 结构 |
| 可执行工具 | 每个新增工程技能携带自己的脚本、有效/无效夹具和 `assets/result.schema.json` |
| 可选适配 | 开源 ROS 2 路径优先；NVIDIA/Isaac 等适配器仅作显式版本化可选路径，缺失时报告 `skip` |
| 安全 | 给出工程 gate 和风险入口，不宣称 PL/SIL、整机合规或 safety-rated stop |
| 算法深度 | 支持系统落地、故障归因和确定性小型评估；不提供生产算法实现或论文级通用实现 |

仍不覆盖或不作如下承诺：

- 新网络结构、训练框架、SLAM/规划/控制数学算法的生产实现；
- COCO、KITTI 等权威评测器或完整公开数据集的再分发；
- 可直接下发真机的力控、WBC、步态、抓取或恢复控制器；
- 对特定机器人、传感器、场景的指标保证；
- 真实硬件验收、碰撞/跌倒/接触安全证明、PL/SIL 或整机合规。

新增工具默认离线、确定性、无网络，力控与 WBC 检查器只读。有效夹具通过只说明输入
满足已声明的工程契约；无效夹具用于证明关键错误会被拒绝。重型 ROS、MoveIt、PCL/Open3D、
Pinocchio、GPU/仿真器或硬件检查是条件项，不在普通 CI 中伪装成通过。

## 八个工程技能详解

八个工程技能采用相同结构：领域工作流放在 `SKILL.md`，详细知识放在 `references/`，
确定性检查放在 `scripts/`，可运行样例和 schema 放在 `assets/`。脚本可以从完整仓库运行，
也可以在复制单个技能后从该技能目录运行。

### 1. `robotics-vision-perception`

**适用场景**

- ROS 2 `sensor_msgs/msg/Image` 与 `CameraInfo` 偶发不一致；
- 图像颜色、编码、stride 或 buffer 长度错误；
- 图像使用接收时间而不是采集时间，导致融合/跟踪异常；
- 2D 检测框需要一个小型、确定性的匹配回归检查；
- 部署前需要核对预处理、后处理、坐标缩放和评估泄漏边界。

**需要的输入**

- 相机快照 JSON：Image/CameraInfo 的宽高、encoding、step、data length、frame、
  acquisition stamp、标定矩阵和配对时间；
- 2D 评估 JSON：同一 frame/image 下的 ground truth、prediction、类别、边界框和 IoU
  门限。

**脚本**

```bash
python3 robotics-vision-perception/scripts/check_camera_contract.py \
  robotics-vision-perception/assets/fixtures/camera_valid.json \
  --output /tmp/camera-contract-result.json

python3 robotics-vision-perception/scripts/evaluate_vision_results.py \
  robotics-vision-perception/assets/fixtures/detections_known.json
```

`check_camera_contract.py` 检查尺寸、encoding、step/data 长度、有限标定矩阵、distortion、
frame 一致性、采集时间戳单调性和 Image/CameraInfo 配对偏差。
`evaluate_vision_results.py` 对同类 2D box 做确定性匹配，输出 TP、FP、FN、precision、
recall 和 mean IoU。

**依赖与边界**

离线脚本不依赖 OpenCV、GPU 或 ROS graph。真实图像 transport、QoS、镜头标定精度、
模型精度、吞吐、WCET 和设备热稳定性需要额外证据。内置小型评估器不是 COCO 官方
evaluator，也不支持把其结果扩写成公开数据集成绩。

### 2. `robotics-3d-perception`

**适用场景**

- PointCloud2 解码为乱码、NaN 或 XYZ 错位；
- 驱动输出 big-endian 数据，消费者按 little-endian 读取；
- organized cloud 的 `row_step`、padding 或 `data` 长度不一致；
- deskew、点时间或 ring 字段契约不清楚；
- 需要对有 frame 的 3D object 输出做确定性小型回归。

**需要的输入**

- PointCloud2 布局 JSON：width/height、fields、datatype/count/offset、point_step、
  row_step、大小端、原始 bytes、frame 和 stamp；
- 3D 评估 JSON：类别、中心、尺寸、yaw、frame、距离/尺寸/yaw 门限。

**脚本**

```bash
python3 robotics-3d-perception/scripts/check_pointcloud_contract.py \
  robotics-3d-perception/assets/fixtures/cloud_valid.json

python3 robotics-3d-perception/scripts/evaluate_3d_results.py \
  robotics-3d-perception/assets/fixtures/objects_known.json
```

前者验证字段边界、point/row step、organized indexing、data length、实际大小端 XYZ
解码、有限值比例以及声明的 time/ring 字段。后者按显式中心距离、尺寸和 yaw gate
匹配对象。

**依赖与边界**

评估器不是旋转框 3D IoU 或 KITTI/nuScenes 官方 evaluator。PointCloud2 字节准入通过
不证明 deskew、外参、地面分割、目标检测、跟踪或点云语义正确。PCL/Open3D、GPU 与 ROS
在线订阅属于可选后续阶段。

### 3. `robotics-manipulation`

**适用场景**

- MoveIt group/end effector 缺失，IK 或规划立即失败；
- URDF、SRDF、kinematics、joint limits 和 controller YAML 名称不一致；
- 规划成功但 FollowJointTrajectory 执行中止；
- 需要在启动 MoveIt 或连接机械臂前审查配置快照。

**需要的输入**

一个快照目录，至少包含 manifest 指向的 URDF、SRDF、`kinematics.yaml`、
`joint_limits.yaml`、planning pipelines 和 MoveIt controllers。有效目录示例：
`robotics-manipulation/assets/fixtures/moveit_valid/`。

**脚本**

```bash
python3 robotics-manipulation/scripts/check_moveit_config.py \
  robotics-manipulation/assets/fixtures/moveit_valid

# 可选：只发现本机包，不启动 MoveIt、不规划、不运动
python3 robotics-manipulation/scripts/check_moveit_config.py \
  robotics-manipulation/assets/fixtures/moveit_valid \
  --ros-check
```

检查器交叉验证 movable/mimic/passive joint、chain group、end effector、kinematics group、
limits、planning pipeline、MoveIt controller joint/action 映射，以及 URDF 中声明的
ros2_control position command interface。

**依赖与 `skip`**

基础配置检查只需要 Python、XML 和 PyYAML。只有显式使用 `--ros-check` 时才调用
`ros2 pkg prefix` 查找 `moveit_ros_move_group` 和 `moveit_msgs`。若这些可选包未安装，
结果为 `skip`、退出码 `0`，并在 `limitations` 命名缺失包。

配置通过不证明 PlanningScene 完整、碰撞模型正确、action server 可用、轨迹能执行、
制动距离安全或真实机械臂已验收。

### 4. `robotics-hand-eye-calibration`

**适用场景**

- eye-in-hand 或 eye-to-hand 标定结果看似残差很小，但实际抓取存在系统偏差；
- 相机、tool、base、target 的父子 frame 或四元数顺序不清楚；
- 数据只有单轴旋转、纯旋转或很小平移，缺少可观测性；
- 采样时间不配对，或者 fit 数据被误当成独立验证。

**需要的输入**

JSON 数据集需要声明模式、frame 语义、候选外参、XY/ZW 四元数、米制平移、A/B 相对运动、
采样时间、fit/holdout 分区和可接受门限。示例：
`robotics-hand-eye-calibration/assets/fixtures/handeye_valid.json`。

**脚本**

```bash
python3 robotics-hand-eye-calibration/scripts/validate_handeye.py \
  robotics-hand-eye-calibration/assets/fixtures/handeye_valid.json
```

检查器执行四元数归一化、变换组合/求逆、时间配对、唯一运动计数、平移跨度、旋转轴分离、
AX=XB closure，以及 fit/holdout 的旋转和平移 RMSE。

**依赖与边界**

脚本用标准库验证候选结果，不求解手眼外参。通过只说明提供的运动对、frame 和候选在已声明
门限下自洽；不证明 target 检测无偏、机器人运动学准确、相机内参有效或真实抓取精度达标。

### 5. `robotics-force-control`

**适用场景**

- F/T 数据存在偏置、漂移、噪声、非单调时间或饱和；
- payload 改变后接触力估计偏移或控制振荡；
- 导纳/阻抗配置的轴顺序、单位、frame、质量/阻尼/刚度不明确；
- watchdog、滤波、限幅或重力加载机构的超时状态需要审查。

**需要的输入**

- wrench YAML manifest 加有界 CSV：六轴顺序、SI 单位、frame、采样率、门限和数据路径；
- force config YAML：frames、kinematics、selected axes、admittance、payload/CoG、
  gravity、filters、timing、limits 和 watchdog。

**脚本**

```bash
python3 robotics-force-control/scripts/analyze_wrench_log.py \
  robotics-force-control/assets/fixtures/wrench_nominal.yaml

python3 robotics-force-control/scripts/check_force_config.py \
  robotics-force-control/assets/fixtures/force_config_valid.yaml
```

日志分析输出样本率、单调性、各轴 bias/RMS/drift、饱和和声明 gate。配置检查要求六轴映射、
正质量/阻尼、非负刚度、payload/CoG/重力、消息年龄、控制率、force/torque/slew limits，
以及重力加载机构的有界 timeout safe state。

**只读安全边界**

两个脚本都只读：不创建 publisher、不切换 controller、不激活 hardware，也不发送任意
进程命令。离线通过不能授权接触或运动；导纳稳定性、结构柔顺性、实时抖动、传感器安装、
碰撞风险和独立保护功能仍需分阶段试验与安全分析。

### 6. `robotics-legged-wbc`

**适用场景**

- URDF 或模型更新后，WBC 的 joint order、nq/nv 或 contact frame 错位；
- 状态估计器与控制器的 frame、四元数、rate 或 message age 不一致；
- friction/normal-force、task dimension/priority、solver gate 或 fallback 不完整；
- 四足、双足或人形控制需要部署前的静态契约审查。

**需要的输入**

WBC YAML 需要固定 URDF、浮动基表示、actuated joint order、总质量门限、接触 frame、
估计器契约、接触参数、任务、solver、command limits 和所有降级状态。

**脚本**

```bash
python3 robotics-legged-wbc/scripts/check_wbc_contract.py \
  robotics-legged-wbc/assets/fixtures/wbc_valid.yaml

# 可选：用 Pinocchio 比较 free-flyer 模型维度和关节顺序
python3 robotics-legged-wbc/scripts/check_wbc_contract.py \
  robotics-legged-wbc/assets/fixtures/wbc_valid.yaml \
  --pinocchio-check
```

基础检查解析 URDF，验证有限且物理可接受的惯量/限位、精确 joint order、浮动基维度、
总质量、contact/friction/normal force、估计器时序、task dimension/weight/priority、
solver time/iteration/residual、command limits 和 fallback。

**依赖与 `skip`**

Pinocchio 是可选模型后端。只有显式使用 `--pinocchio-check` 时才导入；模块缺失会返回
`skip` 而不是 `pass`。脚本不会实现 QP/WBC、状态估计器、步态或 motor command。
通过不证明 real-time、平衡、抗扰、跌倒恢复或硬件安全。

### 7. `robotics-research-reproduction`

**适用场景**

- 论文只给出 `main` 分支、浮动容器 tag 或未哈希数据目录；
- 无法区分环境搭建成功、baseline 复现和论文 claim 复现；
- seed/repeat、失败运行、数据 split、消融变量或偏差记录不完整；
- 需要在长时间实验前做 provenance admission。

**需要的输入**

YAML manifest 声明 claim、源码仓库和完整 40 字符 commit、不可变容器 digest 或锁定环境
inventory、数据来源/license/split/SHA-256、seeds/repeats、baseline argv/config hash、
metric unit/direction、单变量 ablation、evidence 和 deviations。

**脚本**

```bash
python3 robotics-research-reproduction/scripts/validate_reproduction_manifest.py \
  robotics-research-reproduction/assets/fixtures/reproduction_valid.yaml
```

验证器拒绝浮动 revision、未哈希数据、含糊 metric、缺 seed/repeat、混合变量消融和缺失证据。
它不下载代码、数据或模型，也不运行训练。

**边界**

manifest 通过只说明实验身份和设计可审查，不证明代码能构建、训练能收敛、指标与论文一致，
也不代替许可证和研究诚信审查。

### 8. `robotics-benchmarking`

**适用场景**

- benchmark 把命令写成 shell 字符串，存在注入或环境歧义；
- 输出目录被重复覆盖，原始运行、失败或 skip 被丢弃；
- repeat、warmup、timeout、seed、metric direction 或 regression threshold 未声明；
- 需要统一运行、聚合和保留证据，但不需要一个大型实验平台。

**需要的输入**

YAML manifest 使用 argv 数组声明 command、working/output directory、timeout、repeats、
warmups、seed policy，以及 metric 的 source/field/unit/direction/percentiles/threshold。

**先验证，再 dry-run**

```bash
python3 robotics-benchmarking/scripts/validate_benchmark_manifest.py \
  robotics-benchmarking/assets/fixtures/benchmark_echo.yaml

python3 robotics-benchmarking/scripts/run_benchmark.py \
  robotics-benchmarking/assets/fixtures/benchmark_echo.yaml
```

未提供 `--execute` 时，runner 返回可见的 `skip`，不会执行 manifest command。

**显式执行无害夹具**

```bash
benchmark_run_root="$(mktemp -d)"
python3 robotics-benchmarking/scripts/run_benchmark.py \
  robotics-benchmarking/assets/fixtures/benchmark_echo.yaml \
  --execute \
  --output-dir "${benchmark_run_root}/result"

python3 robotics-benchmarking/scripts/aggregate_results.py \
  "${benchmark_run_root}/result"
```

runner 使用 `subprocess.run(..., shell=False, timeout=...)`，要求显式 `--execute`，
拒绝非空输出目录，并为每次 run 保留记录。aggregator 保留失败和 skip 在分母中，输出
mean、median、population standard deviation 和 nearest-rank percentiles，再按 metric
direction 评估 threshold。

**边界**

该工具不提供集群调度、GPU 隔离、能耗仪器同步或权威领域 evaluator。命令内容仍需人工审查；
argv-only 和 `shell=False` 降低 shell 注入风险，但不把任意程序变成可信程序。

## 公共工程结果

八个新增技能复制同一份 `assets/result.schema.json` 和本地
`scripts/result_contract.py`，单技能安装不依赖仓库根目录或其他技能。公共状态为
`pass`、`warn`、`fail`、`skip`。

所有确定性脚本都可以用 `--output <path>` 写出符合
[result.schema.json](../tools/result.schema.json) 的 JSON：

```json
{
  "schema_version": "1.0.0",
  "skill": "robotics-example",
  "check": "check_name",
  "status": "pass",
  "summary": "human-readable summary",
  "inputs": [],
  "environment": {},
  "metrics": {},
  "gates": [],
  "findings": [],
  "evidence": [],
  "limitations": []
}
```

### 状态语义

| 状态 | 含义 | 自动化应如何处理 |
|---|---|---|
| `pass` | 所有已执行 gate 满足，且不存在 fail finding | 可以进入下一证据等级，但不能扩大为未检查能力 |
| `warn` | 检查完成且无 fail，但存在需人工判断的风险 | 保留报告并审查 warning，不能静默丢弃 |
| `fail` | 至少一个领域 gate 或 finding 失败 | 停止该工作流，修复输入或配置后重跑 |
| `skip` | 可选依赖或运行条件不可用 | 记录 limitation；补齐条件后再做该项，绝不改写为 `pass` |

### 退出码

- 退出码 `0`：脚本完成且没有 fail finding，覆盖 `pass`、`warn` 和有意设计的可选
  runtime `skip`；
- 退出码 `1`：领域准入或配置 gate 失败；
- 退出码 `2`：CLI 输入无效、必需文件不可读、配置无法解析或公共结果契约内部错误。

退出码和状态表达不同维度：`skip` 使用退出码 `0` 是为了让“可选依赖缺失”不破坏普通
CI，但调用方必须读取 JSON 的 `status`，不能只看 shell 退出码。

### 字段约定

- `inputs`：本次实际读取的文件或对象，不写推测路径；
- `environment`：发现的版本、包、维度和运行条件；
- `metrics`：数值、单位和用于 gate 时的方向；
- `gates`：明确门限及其结果；
- `findings`：可操作的 pass/warn/fail 事实；
- `evidence`：相对结果目录的文件、显式 URI 或带 SHA-256 的证据；
- `limitations`：本次没有证明的事项，尤其是标定、力控、WBC 和硬件就绪。

`tools/check_engineering_skills.py` 会验证 manifest 声明的脚本/夹具、schema/helper
字节一致性，以及运行时无跨技能路径依赖。

## 工程脚本索引

下表覆盖 [engineering_skills_manifest.yaml](../tools/engineering_skills_manifest.yaml)
声明的十三个主要脚本。

| 技能 | 脚本与输入 | 主要输出 |
|---|---|---|
| 视觉感知 | `check_camera_contract.py <snapshot.json>` | Image/CameraInfo 布局、frame、stamp、pairing gates |
| 视觉感知 | `evaluate_vision_results.py <record.json>` | TP/FP/FN、precision、recall、mean IoU |
| 3D 感知 | `check_pointcloud_contract.py <cloud.json>` | PointCloud2 布局、大小端 XYZ、有限值与字段 gates |
| 3D 感知 | `evaluate_3d_results.py <record.json>` | 按类别、frame、中心/尺寸/yaw gate 的匹配结果 |
| MoveIt | `check_moveit_config.py <snapshot-dir>` | URDF/SRDF/YAML/controller 跨文件一致性 |
| 手眼标定 | `validate_handeye.py <dataset.json>` | 配对、可观测性、AX=XB fit/holdout RMSE |
| 力控 | `analyze_wrench_log.py <manifest.yaml>` | 采样率、bias、RMS、drift、饱和和时序 |
| 力控 | `check_force_config.py <config.yaml>` | frame/axis、admittance、重力、时序、限幅和 watchdog |
| 腿足 WBC | `check_wbc_contract.py <contract.yaml>` | URDF/关节/接触/估计器/task/solver/fallback gates |
| 论文复现 | `validate_reproduction_manifest.py <manifest.yaml>` | 源码、环境、数据、seed、baseline、ablation 和 evidence |
| Benchmark | `validate_benchmark_manifest.py <manifest.yaml>` | argv、目录、timeout/repeat/seed、metric 和 threshold |
| Benchmark | `run_benchmark.py <manifest.yaml>` | dry-run `skip` 或显式执行后的逐 run 原始记录 |
| Benchmark | `aggregate_results.py <result-directory>` | 完整分母、统计量、percentile 和 regression gate |

全部脚本默认离线且拒绝含糊输入。领域脚本中，只有
`run_benchmark.py --execute` 会执行 benchmark manifest 声明的 argv 命令；
`check_moveit_config.py --ros-check` 只调用 `ros2 pkg prefix` 做包发现，不启动 MoveIt
或机器人。

## 依赖与 `skip`

### 依赖分层

| 层级 | 典型依赖 | 是否所有技能必需 |
|---|---|---|
| 文档使用 | 能读取 Markdown 的 Agent Skills 客户端 | 否，可直接阅读仓库 |
| JSON 离线检查 | Python 3.10+ 标准库 | 仅对应脚本 |
| YAML 离线检查 | Python 3.10+、PyYAML | MoveIt、力控、WBC、复现、benchmark 等 |
| 仓库维护 | PyYAML、jsonschema、Python 3.11+ 的可选 `skills-ref` | 仅维护/CI |
| ROS 接口检查 | ROS 2 Humble、对应 message/package、正确 sourced environment | 条件项 |
| MoveIt 发现 | `moveit_ros_move_group`、`moveit_msgs` | 仅显式 `--ros-check` |
| 力控运行链 | controller manager、F/T broadcaster、admittance 或项目控制器 | 离线配置审查不需要 |
| WBC 模型后端 | Pinocchio Python module | 仅显式 `--pinocchio-check` |
| 加速与仿真 | OpenCV、PCL/Open3D、CUDA/TensorRT、Gazebo/Isaac/MuJoCo | 依任务和版本选择 |
| 实机验收 | 驱动、hardware interface、传感器、机器人、安全设施 | 不能由仓库自动补齐 |

### 为什么重型依赖不作为核心依赖

- 单个技能应能独立安装，普通 CI 不应因为没有机械臂、GPU 或腿足平台而不可运行；
- MoveIt、ros2_control、Pinocchio、NVIDIA/Isaac 等版本必须与目标发行版和机器人栈匹配；
- 安装软件包不会自动提供 URDF/SRDF、硬件驱动、传感器标定或 safety procedure；
- 无法执行的条件项必须可见，故使用 `skip` 而不是删除检查或假装通过。

如果可选检查返回 `skip`：

1. 阅读 `limitations` 中的准确缺失项；
2. 判断该检查是否属于当前交付要求；
3. 若需要，在目标环境安装并锁定对应版本；
4. source 正确 ROS/工作区后重跑同一命令；
5. 不要把依赖安装成功扩写为算法或硬件通过。

本机某次验证快照见
[engineering-expansion-verification.md](../docs/engineering-expansion-verification.md)。
该文件只描述记录时的环境，不是所有用户都必须复制的安装状态。

## 证据等级与实机边界

使用以下等级避免“脚本通过”被误写成“机器人可交付”：

| 等级 | 证据 | 能证明什么 |
|---|---|---|
| E0 文档审查 | SKILL、reference、版本和接口所有权 | 工作流与已知边界明确 |
| E1 内置 fixture | 有效/无效样例和自动测试 | 检查器能接受已知有效输入并拒绝已知错误 |
| E2 项目离线证据 | 实际 bag 导出、日志、URDF/SRDF/YAML、数据/环境哈希 | 当前项目输入满足已声明静态或离线 gate |
| E3 Live ROS smoke | 实际 topics/actions/packages/TF、频率和时间戳 | 运行图中相应接口在观察窗口存在并满足 smoke 条件 |
| E4 仿真或 HIL | 固定场景、故障注入、原始运行和统计 | 被测闭环在指定仿真/台架条件下工作 |
| E5 受控真机试验 | 风险评估、保护措施、分阶段动作和记录 | 特定硬件、配置和工况通过批准的试验 |
| E6 整机验收 | 需求追踪、独立安全功能、覆盖矩阵和签署 | 仅对定义的产品、版本和运行域形成交付证据 |

低等级证据不能替代高等级证据：

- E1 `pass` 不证明实际相机、点云或 F/T 传感器正确；
- E2 配置自洽不证明 MoveIt trajectory 能在控制器和硬件上执行；
- E3 topic 有数据不证明内容时间语义、精度、WCET 或安全；
- E4 仿真稳定不证明摩擦、柔顺、通信丢失和碰撞风险已覆盖；
- E5 单次成功不等于 E6 的完整需求、回归与功能安全证据。

尤其要注意：

- 手眼标定需要独立 holdout、重复采集和任务空间验证；
- 力控需要 payload/CoG、重力补偿、接触环境、passivity/稳定性和独立保护措施；
- WBC 需要真实估计器、实时求解、接触切换、跌落保护和退化/恢复验证；
- 浏览器、普通 ROS watchdog 或“发送零速度”不是 safety-rated stop；
- PL、SIL、ISO 10218、ISO 13849 等合规结论必须由项目安全流程建立。

## 典型工程工作流

### 感知链路上线

1. 用 `robotics-ros2-infra` 检查 topic type、QoS、publisher 数、TF 和时间；
2. 用 vision 或 3D checker 准入实际消息快照；
3. 单独验证内参/外参、deskew、pre/post-processing 和模型输出；
4. 用 `robotics-benchmarking` 固定 command、seed、重复、原始运行和统计；
5. 在目标算力上测 latency distribution、资源占用、丢帧和热稳定性；
6. 再进入场景覆盖和真机任务验收。

### MoveIt 规划成功但执行失败

1. 冻结实际 URDF、SRDF 和全部 YAML 到一个快照；
2. 运行 `check_moveit_config.py`，先排除 group/joint/controller 映射错误；
3. 用 `--ros-check` 只确认包存在，不能据此宣称 action 可用；
4. 在 live 环境分别检查 current state、PlanningScene、plan、time parameterization、
   FollowJointTrajectory action 和 controller/hardware 日志；
5. 在无碰撞风险的受控阶段验证速度、加速度、限位、制动和取消行为。

### 接触力振荡

1. 先保存原始 wrench、stamp、frame、pose、velocity、command 和 controller state；
2. 用 `analyze_wrench_log.py` 排除 bias、drift、saturation 和时序问题；
3. 用 `check_force_config.py` 审查轴、单位、payload、重力、滤波、rate、limits 和 timeout；
4. 再分析环境刚度、控制时延、离散化、passivity 和 gain；
5. 从仿真、非接触、柔顺接触到有界任务逐级验证，不直接在生产工件上试参。

### 论文复现与 benchmark

1. 先用 reproduction manifest 固定源码、环境、数据、seed、baseline 和 claim；
2. 把“环境搭建”“baseline 复现”“论文 claim 复现”分开记录；
3. 用 benchmark validator 审查 argv 和运行预算；
4. dry-run 确认不会执行错误命令；
5. 显式执行到新空目录，保留每次 run，包括 fail 和 skip；
6. 聚合后报告完整分母、统计量、偏差和未满足门限，不只展示最好一次。

## 安装

每个 `robotics-*` 目录都是独立技能。复制需要的完整目录，不要只复制 `SKILL.md`，否则会丢失
references/scripts/assets 和随技能分发的 `LICENSE.txt`。

先决定作用域：

- **项目级**：只在当前机器人仓库使用，便于把技能版本和项目代码一起审查；
- **用户级**：多个项目共用，升级前要检查是否影响旧项目；
- **全部安装**：适合系统集成角色，但不是自动触发所必需；只安装任务相关技能通常更清晰。

安装单个技能后，可以检查目录完整性。以 Codex 用户级目录为例：

```bash
test -f ~/.agents/skills/robotics-vision-perception/SKILL.md
test -d ~/.agents/skills/robotics-vision-perception/references
test -d ~/.agents/skills/robotics-vision-perception/scripts
test -d ~/.agents/skills/robotics-vision-perception/assets
```

### Codex

当前 Codex 按作用域发现 `.agents/skills`：

```bash
# 项目级
mkdir -p .agents/skills
cp -R /path/to/robotics-skills/robotics-ros2-infra .agents/skills/

# 用户级
mkdir -p ~/.agents/skills
cp -R /path/to/robotics-skills/robotics-ros2-infra ~/.agents/skills/
```

整包复制时仍然是逐技能目录安装：

```bash
mkdir -p ~/.agents/skills
for skill in robotics-*; do
  cp -R "$skill" ~/.agents/skills/
done
```

参考：[Codex Skills 文档](https://developers.openai.com/codex/skills)。

### Claude Code

项目级使用 `.claude/skills/`，用户级使用 `~/.claude/skills/`：

```bash
mkdir -p .claude/skills
cp -R /path/to/robotics-skills/robotics-slam .claude/skills/
```

用户级目录为 `~/.claude/skills/`。复制后如当前会话没有重新发现技能，重启或新建会话。

参考：[Claude Code Skills](https://code.claude.com/docs/en/skills)。

### CodeBuddy

项目级使用 `.codebuddy/skills/`，用户级使用 `~/.codebuddy/skills/`：

```bash
mkdir -p .codebuddy/skills
cp -R /path/to/robotics-skills/robotics-nav2 .codebuddy/skills/
```

用户级目录为 `~/.codebuddy/skills/`。以当前客户端文档为准确认是否需要重新加载。

参考：[CodeBuddy Skills](https://www.codebuddy.ai/docs/cli/skills)。

### WorkBuddy

使用当前客户端版本提供的本地技能包导入或 SkillHub 流程，并按其 UI/包格式说明操作。官方页面没有把
`~/.workbuddy/skills/` 定义为跨版本通用安装路径，因此本仓库不再把该目录写成固定契约。

参考：[WorkBuddy Skills Market](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。

## 目录约定

```text
<skill-name>/
├── SKILL.md                 # 触发描述、路由、工作流和硬边界
├── LICENSE.txt              # 单技能分发许可证
├── agents/
│   └── openai.yaml          # 可选客户端 UI 元数据
├── references/              # 领域参考，按任务加载
├── scripts/                 # 技能自己的只读/离线工具
│   └── result_contract.py   # 工程技能的本地公共结果 helper
└── assets/
    ├── fixtures/            # 有效与无效的确定性输入
    ├── result.schema.json   # 工程技能的公共 JSON Schema 副本
    └── run_manifest.example.yaml

docs/                        # 设计、实施计划和验证记录
tools/                       # 仓库维护检查，不属于单技能运行依赖
tests/                       # 结构、参数、契约和纯逻辑回归测试
requirements-dev.txt         # 仓库维护依赖
```

并非六个原有系统技能都需要 `agents/`、`scripts/` 或 `assets/`；以目录实际内容为准。
八个工程技能拥有完整的脚本、夹具、schema 和 example manifest。

## 质量检查

维护检查依赖 Python 3.10+ 与 PyYAML：

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
python3 tools/check_repository.py
python3 tools/check_engineering_skills.py
python3 tools/check_doc_params.py
python3 tools/check_doc_params.py --selftest
python3 -m compileall -q robotics-*/scripts tools tests
git diff --check

# Python 3.11+；官方 Agent Skills reference validator
for entry in robotics-*/SKILL.md; do agentskills validate "$(dirname "$entry")"; done
```

`tools/check_doc_params.py` 使用带核验日期的人工参数快照做回归检查，不联网同步上游。
运行时仍应在目标 ROS 发行版上用实际参数列表、启动解析、录包或硬件测试确认。

各命令的职责：

- `unittest discover`：运行技能契约、正反例、算法小逻辑和仓库质量测试；其中
  `test_engineering_skill_contract` 用当前解释器（`sys.executable`）实际执行 manifest
  声明的十三个脚本的全部有效/无效夹具路径，并按 Draft 2020-12 schema 校验公共结果；
- `check_repository.py`：检查准确的十四技能集合、结构、链接、许可证和已知错误模式；
- `check_engineering_skills.py`：只做静态校验，不执行技能脚本——验证 manifest 声明、
  必需文件、schema/helper 字节一致性，以及运行时无跨技能路径依赖；
- `check_doc_params.py`：把版本敏感参数与带日期、带发行版的维护快照比较；
- `compileall`：发现 Python 语法和导入阶段错误；
- `git diff --check`：发现空白和 patch 格式问题；
- `agentskills validate`：使用官方 reference validator 检查 Agent Skills 结构。

普通测试通过只覆盖仓库声明的纯逻辑和离线契约。条件 ROS 检查应在目标环境单独执行并记录
`pass`、`fail` 或 `skip`，不能因为普通 CI 通过而省略。

## 版本策略

- **可执行基线**：Ubuntu 22.04 / ROS 2 Humble / Python 3.10 语义；
- **文档参数**：每个版本敏感参数必须标出目标发行版，并优先链接上游官方文档或源码；
- **其他 ROS 发行版**：Jazzy、Rolling 或 vendor fork 先检查 package version、参数声明、
  message/action type、plugin name 和 launch API，再移植示例；
- **可选 vendor 栈**：NVIDIA Isaac ROS、Isaac Sim/Lab、TensorRT 等只能作为明确版本的
  adapter，不能悄悄替换开源基线；
- **单技能升级**：保留完整目录和许可证，升级前运行该技能有效/无效夹具；
- **结果契约升级**：改变公共字段或语义必须提升 `schema_version`，同步八份 schema/helper
  和 root manifest，并补迁移说明。

本仓库不会用“最新”“通用”“所有机器人都适用”替代版本证据。目标系统的上游包可能在
README 发布后更新，因此部署前仍要对实际安装版本复核。

## 贡献指南

新增或修改技能时遵守以下规则：

1. **保持职责单一**：description 只描述触发条件，`SKILL.md` 放决策工作流，重参考放
   `references/`，确定性工具放 `scripts/`。
2. **以版本为单位写事实**：ROS 参数、plugin、message/action 或第三方 API 要写明
   Humble/具体版本，并附上游 primary source。
3. **先证明错误会被拒绝**：新增确定性 gate 时同时提供有效与无效 fixture，并让测试实际
   运行两条路径。
4. **保持独立安装**：运行时不能 import 另一个技能或仓库根 `tools/`；公共 helper/schema
   通过机械复制和 root checker 保持一致。
5. **不扩大证据**：offline、live ROS、simulation、hardware 和 safety acceptance
   分开陈述；在 `limitations` 写清没检查什么。
6. **安全默认只读**：涉及运动、力、WBC、teleop 或 benchmark 外部命令时，显式标注授权点、
   timeout、限幅、输出目录和失败行为。
7. **保护失败样本**：benchmark 和实验报告不得从分母删除 fail/skip，也不得只保留最好一次。
8. **验证后提交**：运行质量检查，检查 README/本地链接和 `git diff --check`，不要把无关
   工作区改动混入提交。

提交前建议在 PR 或变更说明中列出：

- 目标 skill 和触发场景；
- 目标 ROS/依赖版本；
- 新增或改变的 gate；
- 有效/无效 fixture；
- 实际运行的验证命令；
- 仍为 `skip` 或尚未做硬件验证的部分。

## 常见问题

### 必须安装全部十四个技能吗？

不需要。每个 `robotics-*` 目录独立安装。按任务安装最小集合通常更容易触发和维护。
系统集成负责人可以全部安装，但仍应由问题描述选择最相关技能。

### 为什么结果是 `skip`，进程却返回退出码 `0`？

`skip` 表示被请求的可选条件不可用，例如本机没有 MoveIt 或 Pinocchio。它不是领域失败，
也不是 `pass`。退出码 `0` 让普通、轻量 CI 可以完成；自动化必须继续读取 JSON `status`
和 `limitations`。如果该条件属于交付要求，就必须补齐依赖并重跑。

### 为什么仓库不自动安装 MoveIt、ros2_control 力控插件或 Pinocchio？

这些依赖较重、版本敏感且与机器人类型相关。一个面向 Nav2/感知的环境不一定需要机械臂
或腿足控制栈；擅自安装也可能改变现有 ROS 依赖图。更重要的是，安装软件包不会自动获得
URDF/SRDF、hardware interface、F/T 标定、实时控制和安全设施。技能保持 portable core，
在真正需要时再由项目锁定并安装 optional adapter。

### 有效 fixture 通过，是否说明我的算法也正确？

否。有效 fixture 是检查器自身的回归证据。要证明项目算法，需要换成真实数据/配置，定义
任务指标、数据 split、baseline、seed/repeat，保存原始 evidence，再在目标算力和场景上
验证。权威数据集应使用其官方 evaluator。

### 配置检查通过，是否可以直接上真机？

不可以。配置通过不等于实机验收。MoveIt、力控、WBC、teleop 和 sim-to-real 都必须经过
风险评估、仿真/台架、受控低能量试验、故障注入、独立保护措施和整机需求追踪。技能不会
替代急停、安全 PLC、限位、跌落保护或认证流程。

### 我使用 Jazzy、Rolling 或厂商 fork，能直接照抄 Humble 参数吗？

不能。先用目标安装的 `ros2 pkg prefix`、`ros2 param describe`、interface/action 定义、
plugin XML、launch `--show-args` 和上游源码确认差异。然后复制并版本化一份目标配置，不要
在同一段文档里混写不同发行版参数。

### 为什么不把所有知识都写进 README？

README 负责选择、安装、公共契约和工程边界。每个技能的决策树在其 `SKILL.md`，详细参数、
现象归因和领域说明在 `references/`。这样 Agent 只在相关任务加载对应内容，也避免同一事实
在多个文件漂移。

### 能否帮助算法工程师改算法？

它主要帮助算法工程师排除时间、TF、外参、数据布局、配置、执行和实验设计问题，并建立可重复
benchmark。它不会直接实现新的检测器、SLAM 后端、MPC/WBC solver 或训练方法。算法创新仍需
论文、数学、实现和领域 evaluator；本仓库负责让这些工作进入可验证的工程链。

### 如何报告问题？

请附上最小可复现证据：目标 skill、ROS/依赖版本、精确命令和退出码、脱敏后的输入 fixture
或配置、JSON result、预期行为，以及是否涉及真机。不要只写“不能用”或只贴最终异常截图。

## License

[MIT](../LICENSE)
