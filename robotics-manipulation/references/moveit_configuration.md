# MoveIt 2 Humble configuration contract

## Robot model

Start from the robot description actually loaded by the system. URDF defines
links, joints, axes, limits, mimic relationships, transmissions and
ros2_control interfaces. SRDF adds planning groups, disabled collisions,
virtual/passive joints, group states and end effectors.

Names must agree byte-for-byte across URDF, SRDF, kinematics, joint-limit and
controller files. Do not repair a mismatch by silently renaming only one layer.

## Planning groups and chains

A chain group needs an existing base and tip connected through the URDF tree.
Joint groups need existing movable joints. Exclude mimic/passive joints from
independent command lists unless the hardware contract explicitly exposes them.
An end effector references an existing group and parent link.

The kinematics YAML key is the SRDF group name. Record solver plugin, resolution,
timeout and attempts as version-scoped parameters; do not assume one solver is
best for all geometry.

## Limits

URDF limits are the physical/model source. MoveIt joint-limit overrides may
tighten velocity and acceleration for planning but must not contradict units or
invent unknown joints. ros2_control and drive limits remain separate
enforcement layers. A planned trajectory within MoveIt limits can still exceed
hardware constraints after scaling or controller conversion.

## Planning pipelines

Declare the available pipelines and one valid default. ROS 2 Humble commonly
uses OMPL and can be configured with Pilz industrial motion planners; CHOMP and
other plugins are installation/version dependent. Preserve exact plugin and
request-adapter configuration.

Planner ID, group, constraints, allowed planning time, attempts and start state
belong in the evidence. Do not attribute every `PLANNING_FAILED` result to the
planner before checking scene, state bounds, TF and request validity.

## Controller mapping

MoveIt controller YAML maps a controller name to type, action namespace and an
ordered joint list. For a FollowJointTrajectory controller, verify the combined
action path and the controller's actual joint set. Every commanded joint must
exist in URDF and expose the required ros2_control command interface.

`scripts/check_moveit_config.py` performs static consistency checks. It does not
confirm live action types, controller lifecycle, state freshness, trajectory
tolerances or hardware behavior.

## Version boundary

Examples target MoveIt 2 on ROS 2 Humble. Later distributions change tutorials,
plugins and parameter surfaces. Confirm installed package documentation before
copying a Jazzy/Rolling configuration into Humble.

## Primary upstream references

- [MoveIt 2 Humble documentation](https://moveit.picknik.ai/humble/index.html)
- [MoveIt 2 Humble controller configuration](https://moveit.picknik.ai/humble/doc/examples/controller_configuration/controller_configuration_tutorial.html)
