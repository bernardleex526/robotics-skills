#!/usr/bin/env python3
"""Check portable skill structure, local references, and known regressions."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

from check_engineering_skills import check as check_engineering_skills


REPO = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {
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
FRONTMATTER_KEYS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
LOCAL_RESOURCE = re.compile(
    r"(?<![A-Za-z0-9_./-])((?:references|scripts|assets)/"
    r"[A-Za-z0-9_.\-/]+\.(?:md|py|yaml|yml|json))"
)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ROS2_SHORT_TYPE = re.compile(
    r"\b[a-z][a-z0-9_]*_msgs/(?!msg/)[A-Z][A-Za-z0-9_]*\b"
)
KNOWN_BAD = {
    "@foxglove/web-sdk": "use the official Foxglove extension package",
    "geometry_msgs/Twist": "use geometry_msgs/msg/Twist",
    "trajectory_msgs/JointTrajectory": "use trajectory_msgs/msg/JointTrajectory",
    "correlation_search_space_sm deviation": "broken parameter name",
    "ros2 param set /controller_manager <ctrl>.<param>": (
        "controller parameters are not generically owned by controller_manager"
    ),
    "ROSLIB.Ros` 对象在断线后**不可复用**": "Ros.connect supports reuse",
    "硬限位必须能承受最大速度": "unsafe generic commissioning advice",
    "首次上电串联限流电阻": "unsafe generic commissioning advice",
    "IMU 频率 ≥200 Hz": "sensor admission rate is algorithm dependent",
    "推理耗时实测 < 控制周期的 50%": "fixed scheduling margin",
    ">500 Hz 的闭环": "fixed control-rate boundary",
    "`ros2 topic hz /scan` ≥ 10 Hz": "fixed scan-rate boundary",
    "10–15 Hz 足够显示": "fixed frontend update budget",
    "换算法救不了纯退化，必须加传感器约束": "overstated degeneracy remedy",
    "深度图/分割图的 sim2real 远好于 RGB": "overstated modality ranking",
    "没有它必然超调爆炸": "absolute PID safety claim",
    "Kp 降 20–30%": "fixed post-ZN adjustment",
    "Gazebo (Harmonic)": "unscoped ROS/Gazebo version pairing",
    "new ROSLIB.Message": "roslib 2.x publishes plain message objects",
    "只在 global costmap 用": "static layers may be used in local costmaps",
    "`nav2_smac_planner/SmacPlanner2D` 或 `SmacPlannerHybrid`": (
        "Smac 2D does not enforce SE2 curvature"
    ),
    'Foxy 及更早是 `"differential"`': "legacy AMCL spelling applies through Galactic",
    "检查 `/odom` 协方差；slam_toolbox": "slam_toolbox consumes odometry through TF",
    "初始化时做平移运动而非纯旋转": "initialization depends on sensor mode",
    "滤动态物体；提高关键帧密度": "no generic ORB-SLAM3 keyframe-density control",
    "换 905 nm 之外的雷达无效": "glass performance is not wavelength-only",
    "on_deactivate()/on_cleanup()/on_shutdown()/on_error()": (
        "hardware lifecycle callbacks have distinct semantics"
    ),
    "激活时 command≠state；目标从 0 突变": "activation is interface-specific",
    "用 `ros2 topic hz /joint_states` 验证实际频率": (
        "joint-state arrivals are not controller-loop WCET evidence"
    ),
    "要么把服务客户端放进独立的 `MutuallyExclusive` 组": (
        "callback groups require an executor that can run them concurrently"
    ),
    "**inactive 状态下 publisher 存在但不发数据**": (
        "ordinary publishers and timers are not lifecycle-managed"
    ),
    "| 节点 active 但无数据 | lifecycle 停在 inactive |": (
        "contradictory lifecycle symptom"
    ),
    "controller 配置 YAML（`controller_manager` 节点参数）": (
        "controller type and runtime parameters have different owners"
    ),
    "无输出或状态 `inactive` → hardware 插件未加载成功": (
        "inactive is not proof of hardware-load failure"
    ),
    "放宽 `constraints.goal_time`；查机械阻力": "unsafe stalled-mechanism order",
    "截止频率取环带宽的 5–10 倍": "unscoped derivative-filter rule",
    "路径跟随优先、少绕路": "RPP is not a local obstacle-avoidance planner",
    "`min_pass_through`（判定为空闲所需穿透次数）": (
        "pass count applies before occupied or unoccupied marking"
    ),
    "原地转 10 圈": "wheel calibration must be bidirectional and evidence-based",
    "y: height - 1 - gy": "continuous grid overlay has a one-pixel offset",
    "const xyz: number[] = []": "point-cloud example must reuse its buffer",
    "断开即停": "a closed browser transport cannot deliver a zero command",
    "`ros2 interface show`/小样本检查字段和单位": (
        "interface show exposes schema, not runtime PointCloud2 fields"
    ),
    "| 到点了不算到 | `xy_goal_tolerance` / `yaw_goal_tolerance` 太严 | 放宽；": (
        "goal tolerance must not hide tracking or localization faults"
    ),
    "后续版本可能使用 `progress_checker_plugins`": (
        "the progress-checker list has a known Iron boundary"
    ),
    "| 原地反复抖动不前进 | local costmap 里有幽灵障碍 |": (
        "oscillation has multiple possible causes"
    ),
    "| 绕远路 / 不走明显捷径 | global costmap 有残留障碍未被清除 |": (
        "route choice also depends on planner and map semantics"
    ),
    "| 频繁触发 recovery（原地转圈） | 规划持续失败 |": (
        "recovery can follow several BT failure branches"
    ),
    "每 episode 重采样": "randomization timing depends on parameter semantics",
    "任务空间均匀采样": "reset states must be feasible",
    "指令延迟 1~2 个控制周期": "latency must be measured end to end",
    "质量/质心在线辨识": "the described least-squares workflow is batch",
    "超温自动去使能": "de-energizing may drop gravity-loaded mechanisms",
    "| 物理引擎 | PhysX 5 | DART/Bullet 可选 |": (
        "simulator engines and versions must be scoped"
    ),
    "建图模式跑通后保存地图：`ros2 run nav2_map_server map_saver_cli -f my_map`": (
        "occupancy maps and slam_toolbox pose graphs are distinct"
    ),
    "标准整定流程（临界比例度法、继电器法、手动经验法）": (
        "the reference has no relay-feedback workflow"
    ),
    "手动经验法（推荐首选）": "manual tuning is not universally first",
    "加速度限幅与低通滤波": (
        "velocity smoothing and low-pass filtering are different contracts"
    ),
    "controller 未 active 或 joint 名与 URDF 不一致": (
        "the quoted controller log specifically means not running"
    ),
    "三者只改一处": "direction conventions must be verified as a chain",
    "轨迹类控制器\n   （`joint_trajectory_controller` 或 "
    "`forward_command_controller`）": (
        "forward_command_controller does not execute trajectories"
    ),
    "整条链停在 `unconfigured`": "lifecycle failures can leave mixed states",
    "看 NavigateToPose result 与 planner 日志": (
        "Humble NavigateToPose has an Empty result"
    ),
    "读取 action result、BT error code": (
        "Nav2 error-code propagation was added after Humble"
    ),
    "改 BT 前先用 action result": (
        "Humble needs terminal status and server logs"
    ),
    "| `Behavior tree threw exception` | BT 自定义节点未注册进 "
    "`plugin_lib_names` |": "BT exceptions have multiple possible causes",
    "加 GPS（`gpsTopic` + `useGpsElevation`）": (
        "LIO-SAM GPS elevation is conditional"
    ),
    "时间不同步是 SLAM 漂移的头号隐形杀手": (
        "time synchronization has no universal root-cause rank"
    ),
    "相机/激光用外部触发，IMU 用 PPS 对时": (
        "clock and trigger capabilities are sensor-specific"
    ),
    "各个姿态（倾斜/远近）各 10+ 张": (
        "camera-calibration admission is evidence-based"
    ),
    "丢一帧无所谓": "sensor-loss tolerance is contract-specific",
    "| 订阅不到 `/map` | 没用 TRANSIENT_LOCAL | 同上 |": (
        "late-join map failures have multiple lifecycle and QoS causes"
    ),
    "**控制/安全相关的节点单独进程**": (
        "process boundaries follow fault and hazard analysis"
    ),
    "这是 sim2real 差距最大来源": "visual-gap ranking is task-specific",
    "LIO 紧耦合 + 轮速计；或加反光柱": (
        "corridor mitigation follows measured observability"
    ),
    "换激光方案或视觉-惯性紧耦合": (
        "an IMU does not restore missing visual information"
    ),
}


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---(?:\n|\Z)", text, re.DOTALL)
    if not match:
        raise ValueError("missing YAML frontmatter")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a mapping")
    return data


def check() -> list[str]:
    problems: list[str] = []
    markdown: list[Path] = []
    root_license_path = REPO / "LICENSE"
    root_license = (
        root_license_path.read_bytes() if root_license_path.is_file() else None
    )

    actual_skills = set(SKILLS)
    missing_expected = EXPECTED_SKILLS - actual_skills
    unexpected = actual_skills - EXPECTED_SKILLS
    if missing_expected:
        problems.append(f"missing expected skills: {sorted(missing_expected)}")
    if unexpected:
        problems.append(f"unexpected skills: {sorted(unexpected)}")

    for skill in SKILLS:
        root = REPO / skill
        entry = root / "SKILL.md"
        if not entry.is_file():
            problems.append(f"{skill}: missing SKILL.md")
            continue
        try:
            metadata = frontmatter(entry)
        except ValueError as exc:
            problems.append(f"{entry.relative_to(REPO).as_posix()}: {exc}")
            continue
        if metadata.get("name") != skill:
            problems.append(f"{entry.relative_to(REPO).as_posix()}: name must match directory")
        description = metadata.get("description")
        if not isinstance(description, str) or not 40 <= len(description) <= 1024:
            problems.append(
                f"{entry.relative_to(REPO).as_posix()}: description must be 40..1024 characters"
            )
        extra = set(metadata) - FRONTMATTER_KEYS
        if extra:
            problems.append(
                f"{entry.relative_to(REPO).as_posix()}: non-portable frontmatter keys {sorted(extra)}"
            )
        if metadata.get("license") != "LICENSE.txt":
            problems.append(
                f"{entry.relative_to(REPO).as_posix()}: license must be LICENSE.txt"
            )
        skill_license = root / "LICENSE.txt"
        if not skill_license.is_file():
            problems.append(f"{skill}: missing LICENSE.txt")
        elif root_license is not None and skill_license.read_bytes() != root_license:
            problems.append(f"{skill}: LICENSE.txt differs from root LICENSE")

        skill_markdown = sorted(root.rglob("*.md"))
        markdown.extend(skill_markdown)
        for path in skill_markdown:
            text = path.read_text(encoding="utf-8")
            for resource in LOCAL_RESOURCE.findall(text):
                if not (root / resource).is_file():
                    problems.append(
                        f"{path.relative_to(REPO).as_posix()}: missing local resource {resource}"
                    )

    for path in markdown:
        text = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            relative = target.split("#", 1)[0]
            if relative and not (path.parent / relative).exists():
                problems.append(
                    f"{path.relative_to(REPO).as_posix()}: missing relative link {target}"
                )
        for bad, reason in KNOWN_BAD.items():
            if bad in text:
                problems.append(f"{path.relative_to(REPO).as_posix()}: {bad!r}: {reason}")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in ROS2_SHORT_TYPE.finditer(line):
                problems.append(
                    f"{path.relative_to(REPO).as_posix()}:{line_number}: "
                    f"non-canonical ROS 2 type {match.group(0)}"
                )
        lines = text.splitlines()
        fence_lines = [
            line_number
            for line_number, line in enumerate(lines, start=1)
            if line.strip().startswith("```")
        ]
        if len(fence_lines) % 2:
            problems.append(
                f"{path.relative_to(REPO).as_posix()}: unbalanced code fences {fence_lines}"
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
                problems.append(
                    f"{path.relative_to(REPO).as_posix()}:{start + 1}: "
                    f"inconsistent table pipe counts {counts}"
                )

    required = (
        "LICENSE",
        "README.md",
        ".gitignore",
        "requirements-dev.txt",
        ".github/workflows/quality.yml",
        "tools/check_doc_params.py",
        "tools/param_manifest.yaml",
        "robotics-ros2-infra/scripts/check_tf_tree.py",
        "robotics-ros2-infra/scripts/check_topic_health.py",
        "robotics-ros2-infra/SKILL.md",
        "robotics-frontend/references/rosbridge_integration.md",
        "robotics-sim2real/SKILL.md",
        "robotics-sim2real/references/policy_deployment_contract.md",
        "robotics-sim2real/assets/policy_deployment_contract.yaml",
    )
    for relative in required:
        if not (REPO / relative).is_file():
            problems.append(f"missing release file: {relative}")

    if (REPO / "scripts").exists():
        problems.append(
            "root scripts/ must not mix runtime skill helpers with maintainer tooling"
        )

    def existing_text(relative: str) -> str:
        path = REPO / relative
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    readme = existing_text("README.md")
    for target in MARKDOWN_LINK.findall(readme):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        relative = target.split("#", 1)[0]
        if relative and not (REPO / relative).exists():
            problems.append(f"README.md: missing relative link {target}")
    for skill in SKILLS:
        if skill not in readme:
            problems.append(f"README does not list {skill}")
    if "ROS 2 Humble" not in readme or "不覆盖" not in readme:
        problems.append("README must state baseline and coverage boundary")
    if "不包含 Codex/Claude 插件 manifest" not in readme:
        problems.append("README must state the plugin-manifest boundary")

    reconnect = existing_text(
        "robotics-frontend/references/rosbridge_integration.md"
    )
    for required_reconnect_pattern in (
        "readonly ros = new ROSLIB.Ros();",
        "this.ros.connect(this.url)",
        "reconnect_on_close: true",
    ):
        if required_reconnect_pattern not in reconnect:
            problems.append(
                "roslib reconnect example missing "
                f"{required_reconnect_pattern!r}"
            )
    if "new ROSLIB.Ros({ url:" in reconnect:
        problems.append("roslib reconnect example replaces the Ros instance")
    if (
        "return { setTarget, stop };" not in reconnect
        or "publishTwist(0, 0)" not in reconnect
    ):
        problems.append(
            "teleop example must expose stop() and immediately publish zero"
        )
    frontend_contracts = (
        ".publish(msg);",
        "location.protocol === 'https:' ? 'wss' : 'ws'",
        "new URL(raw)",
        "@foxglove/rosmsg2-serialization",
        "roslib >= 2",
        "return { x: gx, y: height - gy };",
        "msg.header.frame_id",
        "msg.header.stamp",
        "Float32Array",
        "lostpointercapture",
        "单一控制权",
        "TRANSIENT_LOCAL",
        "controlEnabled = false",
        "if (!controlEnabled)",
        "return { setTarget, stop };",
    )
    for contract in frontend_contracts:
        if contract not in reconnect:
            problems.append(f"frontend reference missing contract {contract!r}")

    infra = existing_text("robotics-ros2-infra/SKILL.md")
    if "<skill-root>" not in infra:
        problems.append("infra skill must use a standalone-install root placeholder")

    workflow = existing_text(".github/workflows/quality.yml")
    for command in ("agentskills validate", "git diff --check"):
        if command not in workflow:
            problems.append(f"CI workflow missing {command!r}")

    sim_skill = existing_text("robotics-sim2real/SKILL.md")
    sim_contract = existing_text(
        "robotics-sim2real/references/policy_deployment_contract.md"
    )
    template_path = (
        REPO / "robotics-sim2real/assets/policy_deployment_contract.yaml"
    )
    if "references/policy_deployment_contract.md" not in sim_skill:
        problems.append("sim2real skill does not route to the policy contract")
    if "assets/policy_deployment_contract.yaml" not in sim_contract:
        problems.append("policy reference does not route to its template")
    if template_path.is_file():
        try:
            template = yaml.safe_load(template_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            problems.append(f"invalid policy contract YAML: {exc}")
        else:
            if not isinstance(template, dict):
                problems.append("policy contract YAML must be a mapping")
    problems.extend(
        f"engineering contract: {problem}"
        for problem in check_engineering_skills(REPO)
    )
    return problems


def main() -> int:
    problems = check()
    if problems:
        print(f"repository quality check failed ({len(problems)} findings):")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"repository quality check passed ({len(SKILLS)} skills)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
