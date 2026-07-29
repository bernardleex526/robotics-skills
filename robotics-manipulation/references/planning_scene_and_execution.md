# PlanningScene, task construction and execution

## PlanningScene input

The planning problem includes current robot state, world collision objects,
attached bodies, allowed-collision matrix, transforms and padding/scaling.
Inspect the scene used by the failing request, not only RViz appearance.
Timestamp and frame errors can produce a coherent-looking but stale scene.

For perception-driven objects, preserve source timestamp/frame, transform
evidence, geometry approximation and update/removal lifecycle. An attached
object must move from world to robot ownership exactly once.

## Failure isolation

Use this order:

1. CurrentStateMonitor has recent, bounded joint values for all group joints.
2. Start and goal satisfy bounds and constraints.
3. PlanningScene and TF are current.
4. Planner plugin and request are valid.
5. Geometric path is valid.
6. Time parameterization produces finite monotonic trajectory times.
7. The configured controller action exists with the expected type/joints.
8. Execution monitoring observes progress and reports the first failure.

Do not widen goal/path tolerances to hide a stalled joint, collision, wrong
state or controller mismatch.

## Time parameterization

Retiming uses joint velocity/acceleration limits and scaling factors. Check
strictly increasing `time_from_start`, finite positions/velocities/
accelerations and consistent joint order. Retiming does not make a colliding or
kinematically invalid path safe.

## MoveIt Task Constructor

For grasp/place or assembly, model stages and interfaces explicitly:
current state, approach, grasp generation, IK, collision allowances, attach,
lift, connect, place, detach and retreat. Preserve which stage failed and its
solutions. A pipeline that finds one stage solution has not solved the full
task.

## Execution commissioning

Progress from offline config to fake hardware/simulation, then a controlled
integration environment, then separately approved real hardware. Before motion,
verify E-stop/protective functions, workspace, payload, brakes/gravity behavior,
speed/acceleration limits, command timeout, controller ownership and rollback.
MoveIt software stop/trajectory cancellation is not safety-rated.

Start with conservative bounded trajectories away from singularities,
collisions and joint limits. Record commanded and measured joint order,
tracking error, action result, controller logs and safety events. A successful
launch or action connection is not motion proof.
