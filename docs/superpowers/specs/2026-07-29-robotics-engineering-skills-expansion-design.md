# Robotics Engineering Skills Expansion Design

Date: 2026-07-29
Status: Approved

## Goal

Extend the repository with eight engineering-grade Agent Skills that help an
agent admit inputs, validate configuration, diagnose integration failures, and
produce reproducible evaluation evidence for:

1. vision perception;
2. 3D perception;
3. MoveIt manipulation;
4. hand-eye calibration;
5. force control;
6. legged whole-body control;
7. research reproduction;
8. benchmarking.

The extension must preserve the repository's existing quality bar: every
version-sensitive statement has an upstream source and a named version, every
new skill is independently installable, deterministic checks have executable
tests, and safety-critical areas do not claim hardware acceptance without
hardware evidence.

## Approved Decisions

- Use ROS 2 Humble as the only executable baseline.
- Describe Jazzy, Rolling, and vendor-specific stacks only as explicit,
  versioned alternatives.
- Prefer open-source ROS 2 paths: `sensor_msgs`, OpenCV/PCL/Open3D, MoveIt 2,
  ros2_control, and framework-neutral rigid-body/WBC contracts.
- Treat Isaac ROS, Isaac Sim/Lab, TensorRT, and similar vendor stacks as
  optional adapters, not core dependencies.
- Require offline fixtures, pure-logic regression tests, and conditional ROS 2
  smoke checks. Do not claim real-hardware validation.
- Keep ordinary CI lightweight. Heavy ROS, MoveIt, Open3D, and simulator checks
  are conditional and must report `SKIP` when their optional dependencies are
  unavailable.
- Build eight independent skills with a common, optional result contract.

## Non-Goals

This work does not:

- implement a production detector, segmenter, planner, calibration solver,
  force controller, state estimator, QP solver, or locomotion controller;
- train or distribute neural-network weights or third-party datasets;
- certify a manipulator or legged platform for safe operation;
- claim compatibility with every robot, camera, force sensor, simulator, or
  ROS distribution;
- make any skill depend at runtime on another skill or on repository-root
  tooling.

## Architecture

Add these self-contained directories:

| Skill | Owned responsibility |
|---|---|
| `robotics-vision-perception` | Camera/image admission, synchronization, vision result evaluation, inference-pipeline diagnosis |
| `robotics-3d-perception` | PointCloud2 admission, geometric pipeline diagnosis, 3D result evaluation |
| `robotics-manipulation` | MoveIt 2 robot/config/controller admission, planning and execution diagnosis |
| `robotics-hand-eye-calibration` | Eye-in-hand/eye-to-hand sample admission, observability and result validation |
| `robotics-force-control` | F/T admission, wrench analysis, force-control configuration and safety gates |
| `robotics-legged-wbc` | Floating-base, joint/contact, estimator, dynamics, task and safety contracts |
| `robotics-research-reproduction` | Provenance, environment, dataset, seed, baseline and ablation contracts |
| `robotics-benchmarking` | Safe repeated execution, metrics aggregation, regression gates and evidence layout |

Each skill follows this portable layout:

```text
<skill-name>/
├── SKILL.md
├── LICENSE.txt
├── references/
├── scripts/
└── assets/
    ├── fixtures/
    ├── result.schema.json
    └── run_manifest.example.yaml
```

`SKILL.md` contains the decision workflow and routes the agent directly to the
reference or script needed for the current task. Detailed framework knowledge
stays one level below it in `references/`. Runtime scripts import neither
repository-root modules nor files from another skill.

Repository-root `tests/` and `tools/` are maintainer assets. They may exercise
skill-local scripts and compare copied schemas, but installed skills do not
need them.

## Existing-Skill Boundaries

- `robotics-motion-control` continues to own generic ros2_control lifecycle,
  hardware-interface, PID, trajectory, and actuator troubleshooting.
  `robotics-force-control` includes only the minimum ros2_control context needed
  to validate F/T and Cartesian force-control chains.
- `robotics-slam` continues to own LiDAR/camera/IMU calibration used for
  localization and mapping. `robotics-hand-eye-calibration` owns manipulator
  camera calibration and AX=XB validation.
- `robotics-sim2real` continues to own dynamics alignment, domain
  randomization, and policy deployment. `robotics-legged-wbc` owns the online
  state/contact/task/control contract.
- `robotics-ros2-infra` continues to own generic topic, TF, QoS, executor,
  lifecycle, and deployment diagnosis. New skills reuse the ROS concepts in
  their own checks without requiring that skill to be installed.
- `robotics-benchmarking` owns execution and aggregation mechanics.
  `robotics-research-reproduction` owns whether the experimental claim,
  provenance, baseline, seed, and ablation design are reproducible.

## Common Result Contract

Every deterministic domain script can write a JSON result with
`--output <path>`. The copied schema has a repository-wide version and these
required top-level fields:

```json
{
  "schema_version": "1.0.0",
  "skill": "robotics-example",
  "check": "check_name",
  "status": "pass",
  "summary": "human-readable summary",
  "inputs": [],
  "environment": {},
  "metrics": {},
  "gates": [],
  "findings": [],
  "evidence": [],
  "limitations": []
}
```

Contract rules:

- `status` is one of `pass`, `warn`, `fail`, or `skip`.
- A result containing any `fail` gate or finding has overall status `fail`.
- `skip` names the unavailable optional dependency or runtime condition. It is
  never rewritten as `pass`.
- Metrics include a unit and direction when used in a gate.
- Evidence paths are relative to the result directory or use explicit URIs;
  local evidence can include SHA-256.
- Limitations state what the check did not establish, especially for
  calibration, force control, WBC, and hardware readiness.
- Domain-specific keys go below namespaced `metrics` or `environment`
  objects; they do not change common field meanings.

Each skill carries an identical `result.schema.json`. A root maintenance check
compares their SHA-256 digests and validates all bundled expected results.

## CLI and Error Contract

Deterministic scripts use:

- exit `0`: completed without a `fail` finding (`pass`, `warn`, or a deliberate
  optional-runtime `skip`);
- exit `1`: domain admission or configured gate failed;
- exit `2`: invalid CLI input, malformed configuration, unreadable required
  input, or internal contract error.

Scripts print a concise human report to stdout/stderr and optionally emit the
machine result. They must:

- reject ambiguous units, frames, joint order, metric direction, or dataset
  identity instead of guessing;
- bound file sizes, subprocess duration, and repeat count;
- avoid network access in default checks;
- avoid `shell=True`; benchmark commands are YAML argv arrays;
- create a fresh output directory per run and never overwrite evidence unless
  the caller explicitly selects a new empty target;
- normalize floating-point comparison with documented tolerances;
- distinguish unavailable optional dependencies from failed required checks.

## Skill Components

### `robotics-vision-perception`

References cover ROS image/CameraInfo contracts, optical frames, acquisition
timestamps, approximate/exact synchronization, image transport, camera models,
pre/post-processing, detection/segmentation/tracking outputs, inference
profiling, and evaluation leakage.

Scripts:

- `check_camera_contract.py` validates dimensions, encoding, endian/step/data
  length, CameraInfo matrices and distortion vector, image/CameraInfo frame
  agreement, stamp monotonicity, and pairing skew from an offline JSON
  snapshot.
- `evaluate_vision_results.py` validates class/score/box/mask records and
  computes deterministic IoU, precision, recall, and confusion counts at an
  explicit threshold.

Fixtures include valid calibrated streams, malformed row stride, frame
mismatch, timestamp regression, and known detection results.

### `robotics-3d-perception`

References cover PointCloud2 layout, field semantics, deskew/time/ring
requirements, TF and coordinate conventions, finite/range checks, voxel and
outlier filters, registration admission, segmentation/clustering, 3D
detection/pose outputs, and evaluation pitfalls.

Scripts:

- `check_pointcloud_contract.py` parses a compact metadata plus binary fixture
  and validates field datatype/count/offset, endian, `point_step`, `row_step`,
  organized padding, data length, finite XYZ ratio, optional time/ring fields,
  frame, and stamp monotonicity.
- `evaluate_3d_results.py` validates boxes/poses and computes deterministic
  center, size, yaw, and matching metrics under explicit coordinate and class
  rules.

Fixtures exercise little/big endian, row padding, truncated buffers, NaN-heavy
clouds, missing time fields, and known 3D matches.

### `robotics-manipulation`

References cover URDF/SRDF semantics, planning groups and end effectors,
collision matrices, kinematics, joint/cartesian limits, OMPL/Pilz/CHOMP
selection, PlanningScene, MoveIt Task Constructor, controller/action mapping,
trajectory time parameterization, execution monitoring, and planning versus
execution fault isolation.

`check_moveit_config.py` parses a MoveIt config snapshot and cross-checks:

- URDF movable joints, mimic joints, limits, transmissions, and ros2_control
  interfaces;
- SRDF groups, chains, end effectors, virtual/passive joints, and referenced
  links/joints;
- `joint_limits.yaml`, kinematics, planning pipelines, and controller YAML;
- `FollowJointTrajectory`/`GripperCommand` namespaces, joint sets, and
  duplicate/default controller rules.

Fixtures include a minimal Panda-like valid configuration and failures for
missing joints, reversed chains, weaker limits, and action/joint mismatch.
Optional ROS smoke checks inspect installed packages and action availability.

### `robotics-hand-eye-calibration`

References cover frame equations for eye-in-hand and eye-to-hand, target and
intrinsic prerequisites, acquisition-time pairing, AX=XB conventions,
rotation-axis/translation excitation, solver comparison, residuals, held-out
validation, uncertainty, and safe static-TF deployment.

`validate_handeye_dataset.py`:

- validates frame labels and transform direction;
- checks pairing skew, duplicate samples, pose span, and multi-axis rotation
  diversity;
- evaluates a supplied candidate transform using translation and rotation
  closure residuals;
- separates fit samples from held-out validation samples;
- fails degenerate single-axis or insufficient-motion datasets.

Fixtures contain valid synthetic transforms with bounded noise, single-axis
degeneracy, inverted frames, time mismatch, and an overfit candidate.

### `robotics-force-control`

References cover F/T interfaces, `WrenchStamped`, sensor frames, bias/noise/
drift/saturation, payload CoG and gravity compensation, filtering, admittance,
impedance and hybrid force-position concepts, passivity/contact transitions,
watchdogs, rate/limit gates, staged commissioning, and hardware-only evidence
requirements.

Scripts:

- `analyze_wrench_log.py` computes per-axis bias, RMS/noise, drift, saturation,
  sample-rate and stamp properties from CSV with explicit units and frame.
- `check_force_config.py` validates six-axis mapping, frame chain, selected
  axes, mass/damping/stiffness arrays, positive/bounded parameters, CoG and
  payload force, command/state interfaces, filters, watchdogs, slew/force/
  torque limits, and safe timeout state.

Fixtures cover healthy stationary/contact logs, bias/drift/saturation,
incorrect units, missing frame, unstable/invalid parameters, and unsafe
timeout behavior. Tools are read-only and never publish commands.

### `robotics-legged-wbc`

References cover floating-base state conventions, quaternion order, estimator
and controller rates, contact state and timing, URDF/inertial admission,
Pinocchio-style joint/model order, centroidal and full rigid-body dynamics,
task hierarchy/weights, equality/inequality constraints, friction pyramids,
torque/joint/velocity limits, QP health, state-machine transitions, fallback,
and simulation-to-hardware admission.

`check_wbc_contract.py` validates:

- floating-base and generalized-coordinate dimensions;
- URDF actuated joint order, inertials and configured limits;
- contact frame existence, normals, friction coefficient and force bounds;
- estimator/controller/command rates and timeout relationships;
- task names, dimensions, nonnegative weights, priorities and required
  constraints;
- solver iteration/time/residual gates and safe degraded states.

Fixtures include a small floating-base biped-like model contract plus joint
order mismatch, missing contact frame, invalid inertia/friction, infeasible
limits, stale estimator, and absent fallback. The skill validates integration
contracts; it does not present a toy QP as a production WBC.

### `robotics-research-reproduction`

References cover claim decomposition, source provenance, licenses, immutable
revisions, environment and hardware capture, dataset identity and split
leakage, seed policy, baseline parity, metric parity, ablation isolation,
negative results, artifact disclosure, and reproduction reports.

`validate_reproduction_manifest.py` requires:

- immutable code/container revisions rather than floating branches/tags;
- environment lock or explicit package inventory;
- dataset source, license, split and checksums;
- seeds and repeat policy;
- baseline command/config and expected metric definition;
- one-variable-at-a-time ablation declarations;
- evidence paths and explicit deviations from the paper.

Fixtures cover a complete manifest and failures for floating revisions,
unhashed data, missing seeds, incomparable baselines, and confounded
ablations.

### `robotics-benchmarking`

References define benchmark questions, manifest/result schemas, warm-up and
repeat policy, metric units/direction, latency/throughput/resource metrics,
failure accounting, paired comparisons, summary statistics, regression gates,
artifact layout, and honest interpretation.

Scripts:

- `validate_benchmark_manifest.py` checks argv commands, working directories,
  timeouts, repeats, warm-ups, seeds, metric definitions, thresholds, and
  evidence paths.
- `run_benchmark.py` executes argv without a shell, applies timeout and repeat
  bounds, captures stdout/stderr and return codes, hashes inputs/evidence, and
  writes one result per run. Actual execution requires explicit `--execute`.
- `aggregate_results.py` reports count, failure/skip rate, mean, median,
  standard deviation and requested percentiles; it evaluates gates with
  explicit metric direction and never drops failures from denominators.

Fixtures cover successful and failing commands, timeouts, malformed metrics,
mixed pass/fail/skip runs, and known aggregate values.

## Data Flow

```text
source/config/log/fixture
        │
        ▼
domain admission or evaluation script
        │
        ├── human report
        └── result.json ───────────────┐
                                      │ optional
reproduction manifest ── validate ────┤
benchmark manifest ────── run ────────┤
                                      ▼
                              aggregate_results.py
                                      │
                                      ├── summary result.json
                                      └── evidence directory
```

A domain skill remains useful without the research or benchmark skills.
Interoperability is additive: the latter consume common results when present.

## Safety and Security

- All default tools are offline and read-only.
- No force-control or WBC tool publishes a ROS command or activates a
  controller.
- Manipulation runtime checks inspect configuration, packages, topics, actions,
  and lifecycle state; any motion trial remains a documented hardware
  acceptance step outside automated verification.
- Benchmark execution requires `--execute`, rejects scalar shell commands,
  bounds repeats and timeout, and writes only under a caller-selected empty
  output directory.
- Fixtures contain no proprietary logs, model weights, credentials, or
  third-party datasets.
- Documentation distinguishes simulation proof, controlled integration, and
  hardware acceptance.

## Validation Strategy

### Always-on CI

1. Validate all fourteen Agent Skills and portable frontmatter.
2. Resolve every skill-local link.
3. Verify each skill includes `LICENSE.txt`, scripts, fixtures, a run-manifest
   example, and the common result schema.
4. Confirm all eight schema copies are byte-identical.
5. Run valid fixtures and assert exit `0` plus schema-valid results.
6. Run invalid fixtures and assert the documented exit `1` or `2`.
7. Unit-test pure analysis functions and known metric/aggregate values.
8. Compile all Python and run `git diff --check`.
9. Scan documentation for known invalid parameters, unsafe claims, floating
   version examples, and cross-skill runtime paths.

### Conditional local/ROS checks

- ROS 2 Humble message/topic checks for Image, CameraInfo, PointCloud2 and
  WrenchStamped.
- MoveIt package/config/action discovery when MoveIt 2 Humble is installed.
- ros2_control F/T broadcaster and admittance parameter discovery when present.
- optional OpenCV, PCL/Open3D, Pinocchio, and simulator examples with explicit
  version reporting.

Unavailable optional stacks produce `SKIP`. CI success does not convert those
skips into compatibility claims.

### Forward Tests

After implementation, run each skill on at least one realistic request without
giving the evaluator the intended answer. Review whether it selects the right
reference/tool, preserves scope, produces evidence, and refuses unsupported
hardware or algorithm claims.

## Implementation Order

1. Add failing repository tests for the eight expected skills, assets, result
   contract, script behavior, and README scope.
2. Add the common result schema and lightweight result helpers copied into
   each skill without cross-skill imports.
3. Implement research-reproduction and benchmarking first so later domain
   results have a stable evidence contract.
4. Implement vision and 3D perception.
5. Implement manipulation and hand-eye calibration.
6. Implement force control and WBC, preserving the read-only safety boundary.
7. Update README, version manifest, repository quality tools and CI.
8. Run structure, unit, fixture, compile, official skill-validator, conditional
   ROS smoke, and forward-test gates.

## Completion Criteria

The expansion is complete only when:

- all eight named skills exist and are independently installable;
- every new skill has scoped frontmatter, concise workflow guidance, primary
  Humble references, deterministic scripts, valid/invalid fixtures, schema and
  run-manifest examples, and `LICENSE.txt`;
- every scripted gate emits the common result contract and has regression
  coverage for success and failure;
- benchmark execution meets the subprocess and output-safety rules;
- force and WBC tools are demonstrably read-only;
- all repository and skill validators pass;
- conditional dependencies and hardware gaps are reported as `SKIP` or
  limitations, never as passed evidence;
- README accurately describes fourteen skills and retains the distinction
  between engineering support and production algorithm/hardware acceptance.
