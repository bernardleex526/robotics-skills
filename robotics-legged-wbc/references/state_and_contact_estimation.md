# Floating-base state and contact estimation

## State contract

Define one ordered state vector and use it across estimator, dynamics, WBC,
logger and actuator interface. Record:

- world/odom, base and IMU frames;
- base position/orientation representation;
- quaternion order and normalization policy;
- base twist expression frame;
- actuated joint position/velocity order and units;
- covariance/validity, acquisition stamp and maximum age.

For a free-flyer model with `n` actuated one-DoF joints, a common Pinocchio
layout is `nq = 7 + n` and `nv = 6 + n`, but verify the actual model and joint
types. Quaternion XYZW versus WXYZ mismatch can look plausible while corrupting
gravity and dynamics.

## Joint order

Never sort joint names implicitly or trust message arrival order. Preserve the
model order and build an explicit name-to-index mapping at every boundary.
Mimic, fixed and passive joints are not independently actuated. Validate signs,
zeros and units along with order.

## Estimator timing

Controller frequency alone is not freshness evidence. Check acquisition stamps,
message age, monotonicity, jitter, dropped samples and estimator validity.
Declare the minimum estimator-to-controller update ratio or another explicit
sample/hold contract. Test clock resets and communication loss.

## Contact state

Contact can combine planned phase, foot force/torque, kinematic residual,
velocity/slip, terrain and estimator confidence. State the frame, threshold,
hysteresis/debounce, covariance and maximum age. A binary schedule is not proof
of physical contact; one force threshold is not universal.

False positive contact can inject infeasible constraints. False negative contact
can remove support and destabilize the solution. Preserve transitions and
confidence in evidence.

## Terrain and support

Declare contact point/patch geometry, surface normal, friction model and
reference frame. Flat-ground assumptions must be explicit. Validate support
polygon/centroidal constraints against the active contacts and robot geometry.

## Failure behavior

Define estimator-invalid, stale-state and contact-inconsistent states before
deployment. Depending on the robot and hazard analysis, behavior may include
damping, support hold, controlled lowering or sit-down. Generic motor disable
can cause a fall and is not a universal safe response.

## Acceptance

Use recorded/bounded replay first, then simulation with estimator/contact
faults, then supported or restrained hardware under an approved procedure.
Passing static dimensions cannot prove estimator observability, terrain
adaptation, impact handling or fall safety.
