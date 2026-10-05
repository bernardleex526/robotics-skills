from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {
    "robotics-calibration-sync",
    "robotics-data-replay",
    "robotics-edge-deployment",
    "robotics-lidar-odometry",
    "robotics-localization-fusion",
    "robotics-map-management",
    "robotics-research-discovery",
    "robotics-target-following",
    "robotics-visual-slam",
    "robotics-vln",

    "robotics-3d-perception",
    "robotics-benchmarking",
    "robotics-force-control",
    "robotics-motion-control",
    "robotics-frontend",
    "robotics-hand-eye-calibration",
    "robotics-legged-wbc",
    "robotics-manipulation",
    "robotics-nav2",
    "robotics-research-reproduction",
    "robotics-ros2-infra",
    "robotics-sim2real",
    "robotics-slam",
    "robotics-vision-perception",
}
SKILLS = tuple(
    sorted(
        path.parent.name
        for path in REPO.glob("robotics-*/SKILL.md")
        if path.is_file()
    )
)

STANDARD_FRONTMATTER_KEYS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}

KNOWN_BAD_PATTERNS = {
    "@foxglove/web-sdk": "Foxglove custom panels use @foxglove/extension",
    "geometry_msgs/Twist": "ROS 2 canonical name is geometry_msgs/msg/Twist",
    "trajectory_msgs/JointTrajectory": (
        "ROS 2 canonical name is trajectory_msgs/msg/JointTrajectory"
    ),
    "correlation_search_space_sm deviation": "broken slam_toolbox parameter",
    "ros2 param set /controller_manager <ctrl>.<param>": (
        "controller parameters are not generically owned by controller_manager"
    ),
    "ROSLIB.Ros` 对象在断线后**不可复用**": "ROSLIB.Ros.connect() supports reuse",
    "硬限位必须能承受最大速度": "unsafe generic commissioning advice",
    "首次上电串联限流电阻": "unsafe generic commissioning advice",
    "IMU 频率 ≥200 Hz": "sensor admission rate is algorithm and motion dependent",
    "推理耗时实测 < 控制周期的 50%": "scheduling margin needs WCET analysis",
    ">500 Hz 的闭环": "fixed control-rate boundary is hardware dependent",
    "`ros2 topic hz /scan` ≥ 10 Hz": "fixed scan-rate boundary is task dependent",
    "10–15 Hz 足够显示": "frontend update budget is view and device dependent",
    "换算法救不了纯退化，必须加传感器约束": (
        "degeneracy mitigation is not limited to adding a sensor"
    ),
    "深度图/分割图的 sim2real 远好于 RGB": (
        "modality transfer quality is task and sensor dependent"
    ),
    "没有它必然超调爆炸": "unsafe absolute PID claim",
    "Kp 降 20–30%": "fixed post-ZN adjustment is not portable",
    "Gazebo (Harmonic)": "simulator table must not hide the ROS/Gazebo version pair",
    "new ROSLIB.Message": "roslib 2.x Topic.publish accepts the message object directly",
    "只在 global costmap 用": "a local costmap may intentionally include a static layer",
    "`nav2_smac_planner/SmacPlanner2D` 或 `SmacPlannerHybrid`": (
        "Smac 2D does not search SE2 or enforce turning curvature"
    ),
    'Foxy 及更早是 `"differential"`': (
        "the legacy AMCL model spelling applies through Galactic"
    ),
    "检查 `/odom` 协方差；slam_toolbox": (
        "slam_toolbox consumes odom to base through TF, not Odometry covariance"
    ),
    "初始化时做平移运动而非纯旋转": (
        "the initialization motion requirement is sensor-mode dependent"
    ),
    "滤动态物体；提高关键帧密度": (
        "ORB-SLAM3 does not expose a generic keyframe-density YAML control"
    ),
    "换 905 nm 之外的雷达无效": (
        "glass returns depend on the complete sensor and scene, not wavelength alone"
    ),
    "on_deactivate()/on_cleanup()/on_shutdown()/on_error()": (
        "ros2_control lifecycle callbacks have different resource semantics"
    ),
    "激活时 command≠state；目标从 0 突变": (
        "safe activation depends on command-interface semantics"
    ),
    "用 `ros2 topic hz /joint_states` 验证实际频率": (
        "joint-state publication is not controller loop WCET evidence"
    ),
    "要么把服务客户端放进独立的 `MutuallyExclusive` 组": (
        "a callback group alone cannot unblock a single-threaded executor"
    ),
    "**inactive 状态下 publisher 存在但不发数据**": (
        "ordinary publishers and timers are not lifecycle-managed automatically"
    ),
    "| 节点 active 但无数据 | lifecycle 停在 inactive |": (
        "the stated symptom contradicts the proposed lifecycle state"
    ),
    "controller 配置 YAML（`controller_manager` 节点参数）": (
        "controller type and controller-owned parameters have different nodes"
    ),
    "无输出或状态 `inactive` → hardware 插件未加载成功": (
        "an inactive controller is not proof of a hardware load failure"
    ),
    "放宽 `constraints.goal_time`；查机械阻力": (
        "increasing fault dwell before checking a stalled mechanism is unsafe"
    ),
    "截止频率取环带宽的 5–10 倍": (
        "derivative filter placement is sampling/noise/margin dependent"
    ),
    "路径跟随优先、少绕路": (
        "RPP follows a supplied path and is not a local obstacle-avoidance planner"
    ),
    "`min_pass_through`（判定为空闲所需穿透次数）": (
        "slam_toolbox uses the pass count before occupied or unoccupied marking"
    ),
    "原地转 10 圈": "wheel-separation calibration needs bidirectional repeated trials",
    "y: height - 1 - gy": (
        "continuous world coordinates must map the grid origin to the canvas boundary"
    ),
    "const xyz: number[] = []": (
        "the PointCloud2 example promises buffer reuse but allocates per message"
    ),
    "断开即停": (
        "a browser cannot deliver a zero command after its transport is already closed"
    ),
    "`ros2 interface show`/小样本检查字段和单位": (
        "interface show exposes the schema, not runtime PointCloud2 fields"
    ),
    "| 到点了不算到 | `xy_goal_tolerance` / `yaw_goal_tolerance` 太严 | 放宽；": (
        "goal-checker tolerance must not hide tracking or localization faults"
    ),
    "后续版本可能使用 `progress_checker_plugins`": (
        "the plural progress-checker list has a known Iron version boundary"
    ),
    "| 原地反复抖动不前进 | local costmap 里有幽灵障碍 |": (
        "oscillation has controller, odometry, and deadband causes too"
    ),
    "| 绕远路 / 不走明显捷径 | global costmap 有残留障碍未被清除 |": (
        "route choice also depends on planner, costs, unknown space, and topology"
    ),
    "| 频繁触发 recovery（原地转圈） | 规划持续失败 |": (
        "default behavior trees recover from controller, TF, and costmap failures too"
    ),
    "每 episode 重采样": (
        "domain-randomization timing depends on parameter semantics"
    ),
    "任务空间均匀采样": (
        "reset states must be physically feasible and match deployment support"
    ),
    "指令延迟 1~2 个控制周期": (
        "latency must come from an end-to-end measured distribution"
    ),
    "质量/质心在线辨识": (
        "the documented batch least-squares workflow is not online identification"
    ),
    "超温自动去使能": (
        "de-energizing can drop gravity-loaded mechanisms"
    ),
    "| 物理引擎 | PhysX 5 | DART/Bullet 可选 |": (
        "Gazebo Sim defaults to DART and alternative plugins are version-scoped"
    ),
    "建图模式跑通后保存地图：`ros2 run nav2_map_server map_saver_cli -f my_map`": (
        "an occupancy map is not the serialized pose graph required by "
        "slam_toolbox localization"
    ),
    "标准整定流程（临界比例度法、继电器法、手动经验法）": (
        "the referenced PID document does not define a relay-feedback workflow"
    ),
    "手动经验法（推荐首选）": (
        "manual tuning is not the universal first choice for high-risk plants"
    ),
    "加速度限幅与低通滤波": (
        "Nav2 velocity_smoother constrains and interpolates velocity commands; "
        "a separate low-pass filter has different phase-delay implications"
    ),
    "controller 未 active 或 joint 名与 URDF 不一致": (
        "the quoted joint_trajectory_controller log specifically reports "
        "a non-running controller"
    ),
    "三者只改一处": (
        "joint-axis, encoder, and drive conventions must be verified as a chain"
    ),
    "轨迹类控制器\n   （`joint_trajectory_controller` 或 "
    "`forward_command_controller`）": (
        "forward_command_controller forwards interface values and is not a "
        "trajectory controller"
    ),
    "整条链停在 `unconfigured`": (
        "a lifecycle-manager transition failure can leave managed nodes in "
        "mixed states"
    ),
    "看 NavigateToPose result 与 planner 日志": (
        "Humble NavigateToPose returns an Empty result without an error code"
    ),
    "读取 action result、BT error code": (
        "Nav2 error-code propagation was added after Humble"
    ),
    "改 BT 前先用 action result": (
        "Humble requires terminal status and the first server or BT failure log"
    ),
    "| `Behavior tree threw exception` | BT 自定义节点未注册进 "
    "`plugin_lib_names` |": (
        "BT exceptions also cover XML, ports, blackboard, tick, and service "
        "failures"
    ),
    "加 GPS（`gpsTopic` + `useGpsElevation`）": (
        "LIO-SAM expects covariance-qualified GPS odometry and elevation is "
        "conditional"
    ),
    "时间不同步是 SLAM 漂移的头号隐形杀手": (
        "time synchronization is important but cannot be given a universal rank"
    ),
    "相机/激光用外部触发，IMU 用 PPS 对时": (
        "clock and trigger capabilities are sensor-specific"
    ),
    "各个姿态（倾斜/远近）各 10+ 张": (
        "camera calibration admission depends on coverage and observability"
    ),
    "丢一帧无所谓": (
        "sensor-loss tolerance depends on the estimator and safety contract"
    ),
    "| 订阅不到 `/map` | 没用 TRANSIENT_LOCAL | 同上 |": (
        "late-join map failures also include publisher lifecycle and cache state"
    ),
    "**控制/安全相关的节点单独进程**": (
        "process fault containment must follow the system hazard analysis"
    ),
    "这是 sim2real 差距最大来源": (
        "visual gap ranking is task and deployment-data dependent"
    ),
    "LIO 紧耦合 + 轮速计；或加反光柱": (
        "corridor mitigation must follow measured observability and constraints"
    ),
    "换激光方案或视觉-惯性紧耦合": (
        "an IMU does not automatically restore visual observability"
    ),
}

LOCAL_RESOURCE = re.compile(
    r"(?<![A-Za-z0-9_./-])((?:references|scripts|assets)/"
    r"[A-Za-z0-9_.\-/]+\.(?:md|py|yaml|yml|json))"
)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def skill_markdown_files() -> list[Path]:
    files: list[Path] = []
    for skill in SKILLS:
        files.extend(sorted((REPO / skill).rglob("*.md")))
    return files


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---(?:\n|\Z)", text, re.DOTALL)
    if not match:
        raise AssertionError(f"{path.relative_to(REPO)} has no YAML frontmatter")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise AssertionError(f"{path.relative_to(REPO)} frontmatter is not a mapping")
    return data


class RepositoryQualityTests(unittest.TestCase):
    def test_expected_skill_set_exists(self) -> None:
        self.assertEqual(set(SKILLS), EXPECTED_SKILLS)

    def test_frontmatter_is_portable_agent_skills_core(self) -> None:
        root_license = (REPO / "LICENSE").read_bytes()
        for skill in SKILLS:
            path = REPO / skill / "SKILL.md"
            data = parse_frontmatter(path)
            self.assertEqual(data.get("name"), skill)
            self.assertIsInstance(data.get("description"), str)
            self.assertGreaterEqual(len(data["description"].strip()), 40)
            self.assertLessEqual(len(data["description"]), 1024)
            self.assertFalse(
                set(data) - STANDARD_FRONTMATTER_KEYS,
                f"{skill}: non-portable keys {set(data) - STANDARD_FRONTMATTER_KEYS}",
            )
            self.assertEqual(data.get("license"), "LICENSE.txt")
            skill_license = REPO / skill / "LICENSE.txt"
            self.assertTrue(skill_license.is_file())
            self.assertEqual(skill_license.read_bytes(), root_license)

    def test_all_local_skill_references_resolve_from_skill_root(self) -> None:
        missing: list[str] = []
        for skill in SKILLS:
            root = REPO / skill
            for path in sorted(root.rglob("*.md")):
                text = path.read_text(encoding="utf-8")
                for resource in LOCAL_RESOURCE.findall(text):
                    if not (root / resource).is_file():
                        missing.append(
                            f"{path.relative_to(REPO)} -> {resource}"
                        )
        self.assertEqual(missing, [], "broken local references:\n" + "\n".join(missing))

    def test_relative_markdown_links_resolve(self) -> None:
        failures: list[str] = []
        files = skill_markdown_files() + [REPO / "README.md"]
        for path in files:
            text = path.read_text(encoding="utf-8")
            for target in MARKDOWN_LINK.findall(text):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                relative = target.split("#", 1)[0]
                if relative and not (path.parent / relative).exists():
                    failures.append(
                        f"{path.relative_to(REPO)} -> {target}"
                    )
        self.assertEqual(failures, [], "\n".join(failures))

    def test_known_bad_content_is_absent(self) -> None:
        failures: list[str] = []
        for path in skill_markdown_files():
            text = path.read_text(encoding="utf-8")
            for bad, reason in KNOWN_BAD_PATTERNS.items():
                if bad in text:
                    failures.append(f"{path.relative_to(REPO)}: {bad!r}: {reason}")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_ros2_message_type_names_are_canonical(self) -> None:
        bad = re.compile(r"\b[a-z][a-z0-9_]*_msgs/(?!msg/)[A-Z][A-Za-z0-9_]*\b")
        failures: list[str] = []
        for path in skill_markdown_files():
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                for match in bad.finditer(line):
                    failures.append(
                        f"{path.relative_to(REPO)}:{lineno}: {match.group(0)}"
                    )
        self.assertEqual(failures, [], "\n".join(failures))

    def test_markdown_fences_and_tables_are_well_formed(self) -> None:
        failures: list[str] = []
        for path in skill_markdown_files() + [REPO / "README.md"]:
            lines = path.read_text(encoding="utf-8").splitlines()
            fence_lines = [
                index for index, line in enumerate(lines, start=1)
                if line.strip().startswith("```")
            ]
            if len(fence_lines) % 2:
                failures.append(
                    f"{path.relative_to(REPO)}: unbalanced code fences {fence_lines}"
                )

            index = 0
            while index < len(lines):
                if not lines[index].lstrip().startswith("|"):
                    index += 1
                    continue
                start = index
                counts: list[int] = []
                while index < len(lines) and lines[index].lstrip().startswith("|"):
                    counts.append(lines[index].count("|"))
                    index += 1
                if len(counts) >= 2 and len(set(counts)) != 1:
                    failures.append(
                        f"{path.relative_to(REPO)}:{start + 1}: "
                        f"inconsistent table pipe counts {counts}"
                    )
        self.assertEqual(failures, [], "\n".join(failures))

    def test_readme_lists_scope_and_all_skills(self) -> None:
        text = (REPO / "README.md").read_text(encoding="utf-8")
        for skill in SKILLS:
            self.assertIn(skill, text)
        self.assertIn("ROS 2 Humble", text)
        self.assertIn("不覆盖", text)

    def test_readme_states_engineering_expansion_contract(self) -> None:
        text = (REPO / "README.md").read_text(encoding="utf-8") + "\n" + (REPO / "docs/legacy-guide.md").read_text(encoding="utf-8")
        for phrase in (
            "十四个可独立安装的技能",
            "工程准入",
            "不提供生产算法实现",
            "真实硬件验收",
            "NVIDIA",
            "result.schema.json",
            "tools/check_engineering_skills.py",
        ):
            self.assertIn(phrase, text)
        for skill in (
            "robotics-vision-perception",
            "robotics-3d-perception",
            "robotics-manipulation",
            "robotics-hand-eye-calibration",
            "robotics-force-control",
            "robotics-legged-wbc",
            "robotics-research-reproduction",
            "robotics-benchmarking",
        ):
            self.assertIn(skill, text)

    def test_readme_is_a_detailed_user_and_engineering_guide(self) -> None:
        text = (REPO / "README.md").read_text(encoding="utf-8") + "\n" + (REPO / "docs/legacy-guide.md").read_text(encoding="utf-8")
        for heading in (
            "## 30 秒选择技能",
            "## 快速开始",
            "## 十四个技能全景",
            "## 八个工程技能详解",
            "## 工程脚本索引",
            "## 依赖与 `skip`",
            "## 证据等级与实机边界",
            "## 常见问题",
        ):
            self.assertIn(heading, text)
        for script in (
            "check_camera_contract.py",
            "evaluate_vision_results.py",
            "check_pointcloud_contract.py",
            "evaluate_3d_results.py",
            "check_moveit_config.py",
            "validate_handeye.py",
            "analyze_wrench_log.py",
            "check_force_config.py",
            "check_wbc_contract.py",
            "validate_reproduction_manifest.py",
            "validate_benchmark_manifest.py",
            "run_benchmark.py",
            "aggregate_results.py",
        ):
            self.assertIn(script, text)
        for phrase in (
            "`pass`、`warn`、`fail`、`skip`",
            "退出码 `0`",
            "退出码 `1`",
            "退出码 `2`",
            "MoveIt",
            "Pinocchio",
            "只读",
            "不等于实机验收",
        ):
            self.assertIn(phrase, text)

    def test_ci_runs_engineering_contract_and_all_skill_scripts(self) -> None:
        workflow = (REPO / ".github/workflows/quality.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("python tools/check_engineering_skills.py", workflow)
        self.assertIn("robotics-*/scripts", workflow)

    def test_engineering_skills_link_primary_upstream_references(self) -> None:
        expected = {
            "robotics-vision-perception": (
                "https://docs.ros.org/en/humble/p/sensor_msgs/msg/Image.html"
            ),
            "robotics-3d-perception": (
                "https://docs.ros.org/en/ros2_packages/humble/api/sensor_msgs/"
            ),
            "robotics-manipulation": "https://moveit.picknik.ai/humble/index.html",
            "robotics-hand-eye-calibration": (
                "https://moveit.picknik.ai/humble/doc/examples/"
                "hand_eye_calibration/hand_eye_calibration_tutorial.html"
            ),
            "robotics-force-control": (
                "https://control.ros.org/humble/doc/ros2_controllers/"
                "admittance_controller/doc/userdoc.html"
            ),
            "robotics-legged-wbc": (
                "https://stack-of-tasks.github.io/pinocchio/index.html"
            ),
            "robotics-research-reproduction": (
                "https://www.acm.org/publications/policies/artifact-review-badging"
            ),
            "robotics-benchmarking": (
                "https://docs.python.org/3/library/subprocess.html"
            ),
        }
        for skill, url in expected.items():
            text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted((REPO / skill).rglob("*.md"))
            )
            self.assertIn(url, text, skill)

    def test_roslib_reconnect_example_reuses_one_connection(self) -> None:
        path = REPO / "robotics-frontend/references/rosbridge_integration.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("readonly ros = new ROSLIB.Ros();", text)
        self.assertIn("this.ros.connect(this.url)", text)
        self.assertIn("reconnect_on_close: true", text)
        self.assertNotIn("new ROSLIB.Ros({ url:", text)

    def test_frontend_example_matches_current_roslib_and_secure_pages(self) -> None:
        path = REPO / "robotics-frontend/references/rosbridge_integration.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn(".publish(msg);", text)
        self.assertNotIn("ROSLIB.Message", text)
        self.assertIn("location.protocol === 'https:' ? 'wss' : 'ws'", text)
        self.assertIn("new URL(raw)", text)
        self.assertIn("@foxglove/rosmsg2-serialization", text)
        self.assertIn("roslib >= 2", text)
        self.assertIn("return { x: gx, y: height - gy };", text)
        self.assertIn("msg.header.frame_id", text)
        self.assertIn("msg.header.stamp", text)
        self.assertIn("Float32Array", text)
        self.assertIn("lostpointercapture", text)
        self.assertIn("单一控制权", text)
        self.assertIn("TRANSIENT_LOCAL", text)
        self.assertIn("controlEnabled = false", text)
        self.assertIn("if (!controlEnabled)", text)
        self.assertIn("return { setTarget, stop };", text)
        self.assertIn("subscriberTopics", text)
        self.assertIn("publisherTopics", text)
        self.assertIn("field.offset + 4 > msg.point_step", text)
        self.assertIn("msg.row_step < msg.width * msg.point_step", text)
        self.assertIn("bytes.byteLength < msg.row_step * msg.height", text)

    def test_executor_and_lifecycle_examples_state_the_real_contract(self) -> None:
        text = (REPO / "robotics-ros2-infra/SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "`MultiThreadedExecutor` **并且**把等待方与完成回调放入可并行的不同回调组",
            text,
        )
        self.assertIn("普通 publisher/timer 不会因节点进入 `inactive` 自动停", text)
        self.assertIn("LifecyclePublisher", text)
        self.assertIn("编排契约，不是硬件就绪证明", text)
        self.assertIn("/en/humble/Concepts/Intermediate/About-Domain-ID.html", text)

    def test_nav2_planner_and_version_boundaries_are_explicit(self) -> None:
        text = (REPO / "robotics-nav2/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("SmacPlanner2D", text)
        self.assertIn("只在 x/y 栅格搜索，不施加朝向或转弯曲率约束", text)
        self.assertIn("nav2_smac_planner/SmacPlannerHybrid", text)
        self.assertIn("Galactic 及更早", text)
        self.assertIn("标准静态地图 + AMCL 导航", text)
        self.assertNotIn("Nav2 全部节点是 lifecycle", text)
        self.assertIn("仅启动 navigation servers", text)
        self.assertIn("Iron 起使用 `progress_checker_plugins`", text)
        self.assertIn("autostart:=false", text)
        self.assertIn("ros2 pkg prefix nav2_mppi_controller", text)
        self.assertIn("混合状态", text)
        self.assertIn("Humble 的 `NavigateToPose` result 是 `std_msgs/msg/Empty`", text)

    def test_slam_map_artifacts_and_localization_chain_are_distinct(self) -> None:
        text = (REPO / "robotics-slam/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("/slam_toolbox/serialize_map", text)
        self.assertIn("slam_toolbox/srv/SerializePoseGraph", text)
        self.assertIn("map_file_name", text)
        self.assertIn("AMCL", text)
        self.assertIn("yaml/pgm", text)

    def test_humble_ros2_control_plugin_contract_is_complete(self) -> None:
        skill = (REPO / "robotics-motion-control/SKILL.md").read_text(
            encoding="utf-8"
        )
        reference = (
            REPO / "robotics-motion-control/references/ros2_control.md"
        ).read_text(encoding="utf-8")
        for contract in (
            "export_state_interfaces()",
            "export_command_interfaces()",
            "PLUGINLIB_EXPORT_CLASS",
            "plugin XML",
            "~/robot_description",
            "/robot_description",
        ):
            self.assertIn(contract, reference)
        self.assertIn("硬件接口导出", skill)
        self.assertIn("std_msgs/msg/Float64MultiArray", skill)

    def test_calibration_tools_state_ros_and_sensor_boundaries(self) -> None:
        text = (REPO / "robotics-slam/references/calibration.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("LI-Calib", text)
        self.assertIn("ROS 1 catkin", text)
        self.assertIn("VLP-16", text)
        self.assertIn("LI-Init", text)
        self.assertIn("Avia/Mid-360", text)
        self.assertIn("经过验证的 ROS 2 port", text)
        self.assertIn("双向重复", text)

    def test_motion_docs_keep_parameter_and_safety_ownership_explicit(self) -> None:
        skill = (REPO / "robotics-motion-control/SKILL.md").read_text(
            encoding="utf-8"
        )
        pid = (REPO / "robotics-motion-control/references/pid_tuning.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("`<controller>.type`", skill)
        self.assertIn("controller 自身节点", skill)
        self.assertIn("classical parallel PID", pid)
        self.assertIn("Nyquist", pid)

    def test_teleop_example_exposes_immediate_zero_command(self) -> None:
        path = REPO / "robotics-frontend/references/rosbridge_integration.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("return { setTarget, stop };", text)
        self.assertIn("publishTwist(0, 0)", text)
        self.assertNotIn("return { target, stop };", text)
        self.assertNotIn("return target; // UI", text)

    def test_runtime_and_maintainer_scripts_are_separated(self) -> None:
        self.assertFalse(
            (REPO / "scripts").exists(),
            "repository scripts/ mixes runtime diagnostics with maintainer tooling",
        )
        self.assertTrue(
            (REPO / "robotics-ros2-infra/scripts/check_tf_tree.py").is_file()
        )
        self.assertTrue(
            (REPO / "robotics-ros2-infra/scripts/check_topic_health.py").is_file()
        )
        self.assertTrue((REPO / "tools/check_doc_params.py").is_file())

    def test_release_support_files_exist(self) -> None:
        self.assertTrue((REPO / "LICENSE").is_file())
        self.assertTrue((REPO / ".gitignore").is_file())
        self.assertTrue((REPO / "requirements-dev.txt").is_file())
        self.assertTrue((REPO / ".github/workflows/quality.yml").is_file())

    def test_sim2real_has_a_reproducible_policy_contract(self) -> None:
        skill = (REPO / "robotics-sim2real/SKILL.md").read_text(encoding="utf-8")
        contract = (
            REPO / "robotics-sim2real/references/policy_deployment_contract.md"
        ).read_text(encoding="utf-8")
        template = (
            REPO / "robotics-sim2real/assets/policy_deployment_contract.yaml"
        ).read_text(encoding="utf-8")
        self.assertIsInstance(yaml.safe_load(template), dict)
        self.assertIn("references/policy_deployment_contract.md", skill)
        self.assertIn("assets/policy_deployment_contract.yaml", contract)
        for term in (
            "observation",
            "action",
            "normalization",
            "history",
            "recurrent",
            "reset",
            "sha256",
        ):
            self.assertIn(term, template)
        self.assertIn("SDF", skill)
        self.assertIn("startup / reset / interval", skill)

    def test_ci_and_standalone_install_contract_are_explicit(self) -> None:
        workflow = (REPO / ".github/workflows/quality.yml").read_text(
            encoding="utf-8"
        )
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        infra = (REPO / "robotics-ros2-infra/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("agentskills validate", workflow)
        self.assertIn("git diff --check", workflow)
        self.assertIn("不包含 Codex/Claude 插件 manifest", readme)
        self.assertIn("<skill-root>", infra)

    def test_repository_owner_identifier_is_canonical(self) -> None:
        owner = "bernardleex526"
        schema = json.loads(
            (REPO / "tools/result.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            schema["$id"],
            f"https://github.com/{owner}/robotics-skills/"
            "blob/main/tools/result.schema.json",
        )
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            f"https://github.com/{owner}/robotics-skills.git", readme
        )
        sources = [
            path
            for pattern in ("**/*.json", "**/*.md", "**/*.py")
            for path in REPO.glob(pattern)
        ]
        self.assertTrue(sources)
        for path in sources:
            self.assertNotIn(
                f"{owner}-png",
                path.read_text(encoding="utf-8"),
                str(path),
            )


if __name__ == "__main__":
    unittest.main()
