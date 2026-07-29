# Hand-eye models and frame semantics

## Transform notation

Use `T_parent_child` for the transform that expresses coordinates from `child`
in `parent`. Record translation in metres and quaternion in XYZW order. Do not
publish a matrix until its direction and frame names are explicit.

For motion pairs, the classic equation is:

```text
A_i X = X B_i
```

`A_i` and `B_i` are relative motions derived consistently from robot and camera
poses; `X` is the fixed unknown transform. Whether relative motions use
pose-0-to-pose-i or consecutive poses changes signs/order. Preserve the exact
derivation with the dataset.

## Eye in hand

The camera is rigidly attached to the end effector. A common unknown is
`T_tool_camera`. Robot motion supplies end-effector relative motion and target
observations supply camera relative motion. The calibration target is fixed in
the robot/world frame during collection.

## Eye to hand

The camera is fixed in the workspace. A common desired output is
`T_base_camera` (or its inverse). The target is attached to the moving tool.
The algebra/order differs from eye-in-hand even when a library exposes the same
solver family. Derive it from named frames rather than swapping matrices until
residuals look small.

## Intrinsic and target admission

Hand-eye calibration assumes camera intrinsics and target geometry are already
admissible. Record image resolution, focus/lens state, distortion model,
rectification choice, target dimensions and detector version. A biased target
pose can produce a repeatable but wrong extrinsic.

## Robot pose source

Record whether poses come from encoder forward kinematics, a controller state,
external tracking or another estimator. Include units, joint order, base/tool
frames, timestamp semantics and kinematic model identity. Backlash, compliance,
payload and thermal effects can violate the rigid-pose assumption.

## Deployment direction

Before publishing TF, transform a known point both ways and verify composition
to identity. Store the candidate, solver, source hashes, frames and validation
evidence. Ensure exactly one publisher owns the TF edge. Keep the previous
transform as a rollback artifact.

The bundled JSON uses abstract motion labels plus concrete candidate
parent/child frames. The numerical validator cannot prove that upstream poses
used the claimed physical frames.

## Primary upstream reference

- [MoveIt 2 Humble hand-eye calibration tutorial](https://moveit.picknik.ai/humble/doc/examples/hand_eye_calibration/hand_eye_calibration_tutorial.html)
