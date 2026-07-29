# Force-control laws and staged commissioning

## Choose the control objective

- Admittance maps measured wrench error to motion; it is useful when the
  underlying robot accepts position/velocity commands.
- Impedance maps motion error to commanded wrench/torque; it requires an
  appropriate torque/control interface and dynamics contract.
- Hybrid force-motion control selects constrained force axes and complementary
  motion axes in a declared task frame.

Do not use the terms interchangeably. State input/output units, frames, selected
axes, sign, saturation and inner-loop assumptions.

## Admittance parameters

For each ordered axis, virtual mass and damping must be positive; stiffness is
nonnegative. Stability depends on robot dynamics, sampling, delay, filtering,
environment stiffness and the inner controller—not just positive numbers.
Kinematics/Jacobian frame and singularity handling are required.

ROS 2 Humble `admittance_controller` parameters and interfaces are
version-specific. Verify the installed documentation and controller parameter
library rather than copying a later-distribution YAML.

## Contact transitions

Separate free-space approach, contact detection/admission, force regulation,
loss of contact, retreat and fault. Bound approach speed, command slew, force,
torque, displacement and energy as appropriate. Debounce/state estimation must
account for noise and gravity; one threshold is not a universal contact model.

## Passivity and latency

Measure end-to-end sensor-to-command age and jitter. Delays, stiff environment,
high virtual stiffness and filters can inject energy. Use passivity/energy-tank
or stability analysis appropriate to the controller and plant; do not assume a
nominal update rate proves stability.

## Timeout and degraded behavior

Declare sensor-age watchdog, command timeout and a gravity-aware state. A
gravity-loaded robot may need braking, support hold, controlled lowering or
another hazard-derived response; de-energizing can drop the mechanism.
Protective functions require the system risk assessment and suitable hardware.

## Staged commissioning

1. Static offline config and log admission.
2. Simulation with bounded environment stiffness/delay variation.
3. Hardware powered but non-contact, validating frames, gravity and limits.
4. Low-energy compliant target under independent protective measures.
5. Bounded operational cases and declared fault injection.
6. Formal hardware acceptance against the system safety requirements.

At every stage retain commanded/measured pose, velocity, wrench, controller
state, timing, saturation, watchdog and protective events. Stop on unexplained
sign, frame, drift, clipping, oscillation or loss of contact.

## Primary upstream references

- [ros2_control Humble admittance controller](https://control.ros.org/humble/doc/ros2_controllers/admittance_controller/doc/userdoc.html)
- [ros2_control Humble force-torque broadcaster](https://control.ros.org/humble/doc/ros2_controllers/force_torque_sensor_broadcaster/doc/userdoc.html)
