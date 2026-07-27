# robotics-skills

机器人开发方向的 [WorkBuddy](https://www.codebuddy.cn) 技能包（Skill Pack），覆盖运动控制、SLAM、Sim-to-Real 与机器人 Web 前端四个方向。每个技能都是一个独立目录，包含 `SKILL.md`（工作流指引）与 `references/`（按需加载的详细参考）。

## 技能列表

| 技能 | 说明 |
|---|---|
| [robotics-motion-control](robotics-motion-control/) | ros2_control 控制栈搭建、PID 整定、轨迹规划、逆运动学、常见控制报错排查 |
| [robotics-slam](robotics-slam/) | 激光/视觉 SLAM 方案选型（slam_toolbox / Cartographer / LIO-SAM / FAST-LIO2 / ORB-SLAM3）、传感器标定、调参与漂移排查 |
| [robotics-sim2real](robotics-sim2real/) | 仿真器选型（Isaac Lab / Gazebo / MuJoCo）、动力学对齐与系统辨识、域随机化、分阶段真机部署安全清单 |
| [robotics-frontend](robotics-frontend/) | rosbridge / foxglove_bridge 接入、TF/地图/点云可视化、实时监控仪表盘、teleop 远程操控界面 |

## 安装

将需要的技能目录复制到 WorkBuddy 用户技能目录即可（所有项目生效）：

```bash
# Windows
xcopy /E /I robotics-motion-control "%USERPROFILE%\.workbuddy\skills\robotics-motion-control"

# Linux / macOS
cp -r robotics-motion-control ~/.workbuddy/skills/
```

之后在对话中提到相关话题（如「整定 PID」「LIO-SAM 漂移」「域随机化」「rosbridge 接入」）即会自动触发对应技能。

## 目录结构约定

```
<skill-name>/
├── SKILL.md          # 触发描述 + 工作流（主入口）
└── references/       # 详细参考文档，按需加载
```

## License

MIT
