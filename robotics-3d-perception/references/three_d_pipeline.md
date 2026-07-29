# 3D perception pipeline and evaluation

## Admission order

1. Byte layout, field semantics and units.
2. Acquisition timing, per-point timing and deskew.
3. Sensor-to-base/map TF and extrinsic evidence.
4. Range, finite-value and self-filter behavior.
5. Registration or temporal fusion observability.
6. Segmentation/clustering/model pre- and post-processing.
7. Output frames, uncertainty and benchmark metrics.

Changing an algorithm before the first three contracts pass confounds the
diagnosis.

## Filtering

Declare the frame and order for range, voxel, crop, ground, statistical and
robot-self filters. Voxel size changes geometric detail and compute; it is not
a universal denoising setting. Preserve organized structure when downstream
code relies on pixels/scanlines. Measure which points each stage removes.

## Registration

Record source/target frames, initial transform, correspondence rule, robust
loss, stopping criteria and fitness definition. Low residual can occur at a
wrong alignment in repetitive or degenerate geometry. Validate against held-out
transforms/landmarks and inspect conditioning or observable directions.

Corridors, planar scenes, glass, dynamics, rain/dust and sparse range are
environment-specific limitations. Mitigations may involve motion, priors,
masking, sensing, constraints or map design; no one remedy is universal.

## Segmentation and 3D objects

State whether the output is an axis-aligned box, oriented box, pose, mask,
cluster or track. Every result needs a timestamp and frame. Define center,
dimensions, yaw axis/convention, class mapping, confidence and covariance or
limitations.

The bundled evaluator matches same-class objects in one declared frame using:

- maximum center distance;
- maximum relative dimension error;
- maximum wrapped yaw error;
- minimum prediction score.

It reports TP/FP/FN and mean matched translation/yaw errors. This is an
engineering admission metric, not oriented 3D IoU. Use a dataset's authoritative
evaluator for mAP, IoU, tracking or leaderboard claims.

## Optional stacks

ROS 2 Humble `perception_pcl` and PCL are the primary open-source path. Open3D
is useful for offline inspection and registration, but version and coordinate
conventions must be recorded. NVIDIA Isaac/accelerated adapters are optional
and version-scoped; absence should be a visible skip, not a pass.

## Live acceptance

After offline checks, measure actual loss, timestamp monotonicity, field
distributions, TF-at-stamp availability, deskew residuals, latency, CPU/GPU
pressure and performance across representative static/dynamic scenes. Hardware
acceptance cannot be inferred from fixtures.
