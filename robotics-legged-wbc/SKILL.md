---
name: robotics-legged-wbc
description: Use when designing or reviewing quadruped, biped, or humanoid whole-body control, floating-base models, state/contact estimation, centroidal or full dynamics, QP tasks and constraints, solver health, contact transitions, or WBC fallback behavior.
license: LICENSE.txt
---

# Robotics Legged WBC

## Safety Boundary

This skill validates an offline model/control contract. It does not implement a
toy controller, publish commands, activate motors, or declare hardware
readiness. Fall protection, stored energy and contact hazards require a system
hazard analysis and independent protective measures.

## Route by Problem

| Problem | Read / run |
|---|---|
| State, quaternion, joint order or contact inconsistency | `references/state_and_contact_estimation.md` |
| Dynamics/QP/task/solver issue | `references/dynamics_tasks_and_safety.md` |
| Audit one deployment contract | `scripts/check_wbc_contract.py` |

## Workflow

1. Freeze the exact URDF, base representation, position/velocity dimensions,
   quaternion order and actuated joint order.
2. Declare estimator frames/rates/age, contact evidence, model mass/inertia,
   contact frames/friction/force bounds, task dimensions/priorities, command
   limits, solver gates and every degraded state.
3. Copy `assets/fixtures/wbc_valid.yaml`, then run:

   ```bash
   python3 scripts/check_wbc_contract.py wbc.yaml --output result.json
   ```

4. If Pinocchio is installed and version-pinned, add `--pinocchio-check` to
   compare free-flyer model dimensions and joint order. Missing Pinocchio is a
   visible `skip`.
5. Fix offline contract failures before simulation.
6. Validate estimator loss, contact transitions, solver overruns, command
   timeout and fall/degraded behavior in controlled stages before hardware.

## Hard Gates

- URDF inertial and joint-limit data are finite and physically admissible.
- Actuated joint order matches the model exactly.
- Floating-base dimensions and XYZW quaternion order are explicit.
- Contact frames, friction and normal-force bounds agree.
- Estimator/controller rate and message-age contracts are declared.
- Tasks have dimensions, weights and priorities; solver time/iteration/residual
  gates are bounded.
- Timeout, estimator-invalid, solver-failure and degraded states all exist.

## Result Boundary

Exit `0` is offline admission or an explicit optional Pinocchio skip, exit `1`
is a model/control gate failure, and exit `2` is malformed input. A pass is not
evidence of real-time execution, balance, recovery, or safe hardware motion.

## 按需扩展与复用边界

- 仅在明确相关的机器人任务中使用本技能；通用代码/网页/文案工作不加载机器人参考资料。
- 按当前故障读取单个参考文件，不预读整个知识库。脚本路径相对技能目录，运行时解析成绝对路径。
- 新架构、算法替换或明显重复实现前，使用可用的在线搜索核验论文及作者代码；若已安装可选的 `robotics-research-discovery`，可按需读取。小修复不强制联网。无网明确声明未核验，不能声称最新或无现成实现。
- 本模块的补充检查见 `references/review_addendum.md`，仅在涉及其中问题时读取。
