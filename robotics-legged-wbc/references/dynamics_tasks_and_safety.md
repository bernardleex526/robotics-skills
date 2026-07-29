# Dynamics, task hierarchy, solver health and safety

## Model admission

Validate URDF link/joint topology, units, joint axes/limits, positive masses,
centers of mass and physically admissible inertia matrices. Compare total mass
and key CoM/inertia properties with measured or authoritative CAD evidence.
Massless fixed frames may be intentional; dynamic links cannot silently lack
inertia.

Pinocchio is a strong open-source baseline for rigid-body algorithms and model
dimensions. Record its exact version. Optional NVIDIA/Isaac adapters are
version-scoped and do not replace the model/joint-order contract.

## Dynamics choice

Centroidal models reduce the problem to momentum/CoM/contact wrench behavior;
full rigid-body dynamics include joint accelerations and torques. State which
variables and equations are solved. Do not present a simplified centroidal
controller as a drop-in whole-body torque controller.

## Constraints

Typical QP constraints include equations of motion, stance acceleration,
friction pyramid/cone, unilateral normal force, center of pressure, torque,
joint position/velocity/acceleration and collision limits. Record units,
linearization, relaxation/slack and priority. Infeasible constraints must not be
silently dropped.

## Tasks and hierarchy

Every task declares frame, dimension, target, error convention, weight/gain and
priority. Numeric weights do not guarantee strict priority; hierarchical QP,
null-space projection and weighted least squares have different semantics.
Inspect scaling/conditioning across units.

Contact transitions need planned ramping of forces/tasks/constraints and
consistent estimator state. Abrupt activation can generate wrench or torque
steps even when each static phase solves.

## Solver health

Measure solve time distribution against the controller deadline, iteration
count, primal/dual residuals, status, regularization and constraint violation.
A nominal average below the period is not worst-case evidence. Predeclare
overrun and infeasibility handling.

## Command boundary

Validate joint order, units, torque/position/velocity limits, rate/slew limits,
command age and the lower-level actuator mode. Saturation can invalidate the
assumed dynamics and task hierarchy. Preserve requested versus applied command.

## Fault and fall behavior

Test stale estimator, contact disagreement, solver timeout/infeasibility,
actuator saturation, communication loss, terrain slip and power/protective
events. Each has a named bounded degraded state and transition rule.

Software fallback is not safety-rated. Legged/humanoid hardware requires
fall-zone control, support/restraint appropriate to testing, energy/power
limits, emergency/protective functions and acceptance against the system risk
assessment.

## Primary upstream reference

- [Pinocchio rigid multi-body dynamics documentation](https://stack-of-tasks.github.io/pinocchio/index.html)
