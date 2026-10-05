---
name: robotics-manipulation
description: Use when configuring or debugging MoveIt 2 manipulation, URDF/SRDF consistency, kinematics, planning pipelines, PlanningScene, trajectory execution, controller mappings, MoveIt Task Constructor, or planning-versus-control failures.
license: LICENSE.txt
---

# Robotics Manipulation

## Scope

Use this skill to separate robot-model, planning-scene, planning, trajectory,
controller and hardware failures. The bundled checker is read-only and does not
plan, execute, switch controllers, or authorize robot motion.

## Route by Failure

| Symptom | First evidence |
|---|---|
| Group/end effector missing, IK fails immediately | `references/moveit_configuration.md` and offline config check |
| Plan fails or collides unexpectedly | `references/planning_scene_and_execution.md` |
| Plan succeeds but execution aborts | Controller action/joint mapping, current state and execution logs |
| Multi-stage grasp/place task | PlanningScene + MoveIt Task Constructor section |

## Workflow

1. Copy the actual URDF, SRDF, kinematics, joint limits, planning-pipeline and
   controller YAML into one snapshot directory. See
   `assets/fixtures/moveit_valid`.
2. Run:

   ```bash
   python3 scripts/check_moveit_config.py snapshot --output result.json
   ```

3. Fix cross-file names, chains, limits, interfaces and action mappings before
   launching MoveIt.
4. Optionally check installed packages without starting motion:

   ```bash
   python3 scripts/check_moveit_config.py snapshot --ros-check
   ```

5. Follow `references/planning_scene_and_execution.md` for live, staged
   planning and execution evidence.

## Required Separation

- Planning success is not execution success.
- A controller action server is not proof of correct joints, limits or hardware.
- PlanningScene geometry and attached-object state are part of the input.
- Time parameterization cannot repair an invalid geometric path or wrong units.
- Simulation success is not collision, payload, braking or hardware acceptance.

## Result Contract

Exit `0` is an admissible offline config or explicit optional-runtime skip,
exit `1` is a cross-file contract failure, and exit `2` is unreadable/malformed
required input. Results follow `assets/result.schema.json`.

## 按需扩展与复用边界

- 仅在明确相关的机器人任务中使用本技能；通用代码/网页/文案工作不加载机器人参考资料。
- 按当前故障读取单个参考文件，不预读整个知识库。脚本路径相对技能目录，运行时解析成绝对路径。
- 新架构、算法替换或明显重复实现前，使用可用的在线搜索核验论文及作者代码；若已安装可选的 `robotics-research-discovery`，可按需读取。小修复不强制联网。无网明确声明未核验，不能声称最新或无现成实现。
- 本模块的补充检查见 `references/review_addendum.md`，仅在涉及其中问题时读取。
