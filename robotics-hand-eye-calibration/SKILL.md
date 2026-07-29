---
name: robotics-hand-eye-calibration
description: Use when collecting, solving, reviewing, or deploying eye-in-hand or eye-to-hand calibration, AX=XB motion pairs, camera-to-tool/base transforms, observability, residuals, holdout validation, or calibration-related TF faults.
license: LICENSE.txt
---

# Robotics Hand-Eye Calibration

## Scope

Use this skill for manipulator-camera extrinsics. It checks sample admission,
motion observability and a candidate AX=XB transform on fit and held-out pairs.
It does not estimate camera intrinsics, detect a target, solve AX=XB, or prove
robot/world accuracy.

## Workflow

1. Identify eye-in-hand versus eye-to-hand and write every transform with
   parent/child frame labels. Read `references/models_and_frames.md`.
2. Admit camera intrinsics, target geometry, robot pose source, clock pairing
   and rigid mounting before collecting motion pairs.
3. Collect translations plus rotations about materially different axes; reserve
   independent holdout poses. Read `references/collection_and_validation.md`.
4. Export the format in `assets/fixtures/handeye_valid.json`.
5. Validate a candidate:

   ```bash
   python3 scripts/validate_handeye.py dataset.json --output result.json
   ```

6. Compare multiple appropriate solvers using holdout and physical validation,
   not training residual alone.
7. Deploy one reviewed static transform with a named rollback artifact; confirm
   there is no second TF publisher for the same edge.

## Admission Gates

- Frame labels and XYZW quaternion order are explicit.
- Quaternions are finite and normalized.
- Pairing skew stays below a declared threshold.
- Samples are unique and include fit plus holdout partitions.
- Translation span and rotation-axis diversity pass explicit gates.
- Fit and holdout AX=XB translation/rotation residuals pass separately.

## Interpretation

A small AX=XB residual shows internal motion-pair consistency. It does not
exclude biased intrinsics, target-pose bias, robot kinematic error, flex,
backlash, time offset, wrong frame semantics, or a degenerate trajectory.
Independent task-space checks remain mandatory.
