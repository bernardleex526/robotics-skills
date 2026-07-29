# Robotics Engineering Skills Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add eight independently installable, engineering-grade robotics skills with deterministic tools, fixtures, tests, and an interoperable result contract.

**Architecture:** Each new `robotics-*` directory owns one bounded workflow and carries its own references, scripts, fixtures, schema, and license. Runtime code never imports another skill or repository-root tooling; root tests enforce a byte-identical result schema and exercise every valid and invalid fixture. ROS 2 Humble and open-source stacks are the executable baseline, while heavy dependencies are conditional and report `SKIP`.

**Tech Stack:** Python 3.10 standard library, PyYAML, ROS 2 Humble message/config conventions, XML/URDF/SRDF parsing, JSON Schema documents, `unittest`, Agent Skills validators, GitHub Actions.

---

## Worktree Safety

The repository already contains unrelated and previously approved uncommitted
changes. Execute this plan in `/home/lee/robotics-skills`, preserve those
changes, and stage only the exact files named by each task. Do not push.

## File Map

Create these skill roots:

```text
robotics-vision-perception/
robotics-3d-perception/
robotics-manipulation/
robotics-hand-eye-calibration/
robotics-force-control/
robotics-legged-wbc/
robotics-research-reproduction/
robotics-benchmarking/
```

Each root owns `SKILL.md`, `LICENSE.txt`, `references/`, `scripts/`, and
`assets/{fixtures,result.schema.json,run_manifest.example.yaml}`.

Create or modify these maintainer files:

```text
tests/test_engineering_skill_contract.py
tests/test_vision_perception.py
tests/test_3d_perception.py
tests/test_manipulation.py
tests/test_handeye_calibration.py
tests/test_force_control.py
tests/test_legged_wbc.py
tests/test_research_reproduction.py
tests/test_benchmarking.py
tools/engineering_skills_manifest.yaml
tools/check_engineering_skills.py
tests/test_repository_quality.py
tools/check_repository.py
README.md
.github/workflows/quality.yml
```

### Task 1: Lock the eight-skill repository contract

**Files:**
- Create: `tests/test_engineering_skill_contract.py`
- Create: `tools/engineering_skills_manifest.yaml`
- Modify: `tests/test_repository_quality.py`

- [ ] **Step 1: Write the failing expected-skill and layout test**

```python
ENGINEERING_SKILLS = {
    "robotics-vision-perception",
    "robotics-3d-perception",
    "robotics-manipulation",
    "robotics-hand-eye-calibration",
    "robotics-force-control",
    "robotics-legged-wbc",
    "robotics-research-reproduction",
    "robotics-benchmarking",
}

def test_engineering_skills_have_portable_runtime_assets(self):
    for skill in ENGINEERING_SKILLS:
        root = REPO / skill
        self.assertTrue((root / "SKILL.md").is_file(), skill)
        self.assertTrue((root / "LICENSE.txt").is_file(), skill)
        self.assertTrue((root / "scripts").is_dir(), skill)
        self.assertTrue((root / "assets/fixtures").is_dir(), skill)
        self.assertTrue((root / "assets/result.schema.json").is_file(), skill)
        self.assertTrue((root / "assets/run_manifest.example.yaml").is_file(), skill)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_engineering_skill_contract -v
```

Expected: `FAIL` naming the first missing engineering skill.

- [ ] **Step 3: Extend `EXPECTED_SKILLS` to the exact fourteen-skill set**

Replace the six-entry set in `tests/test_repository_quality.py` with all
fourteen names. Keep the existing portable frontmatter and license assertions.

- [ ] **Step 4: Add a machine-readable engineering manifest**

```yaml
schema_version: 1
skills:
  robotics-vision-perception:
    primary_scripts:
      - scripts/check_camera_contract.py
      - scripts/evaluate_vision_results.py
    valid_fixture: assets/fixtures/camera_valid.json
    invalid_fixture: assets/fixtures/camera_bad_stride.json
  robotics-3d-perception:
    primary_scripts:
      - scripts/check_pointcloud_contract.py
      - scripts/evaluate_3d_results.py
    valid_fixture: assets/fixtures/cloud_valid.json
    invalid_fixture: assets/fixtures/cloud_truncated.json
```

Complete the mapping with the exact primary scripts and fixtures defined by
Tasks 3–10.

- [ ] **Step 5: Run the test and keep the expected missing-file failure**

Run the Step 2 command.

Expected: still `FAIL`, now proving the complete target set is enforced.

### Task 2: Scaffold skills and implement the result contract

**Files:**
- Create: all eight skill directory skeletons
- Create: `tools/result.schema.json`
- Create: `tools/result_contract_template.py`
- Create: `tools/check_engineering_skills.py`
- Create: each skill's `assets/result.schema.json`
- Create: each skill's `scripts/result_contract.py`
- Test: `tests/test_engineering_skill_contract.py`

- [ ] **Step 1: Initialize every new skill with the official scaffold helper**

Run `init_skill.py` once per skill with
`--resources scripts,references,assets` and human-facing interface strings.
For example:

```bash
python3 /home/lee/.codex/skills/.system/skill-creator/scripts/init_skill.py \
  robotics-vision-perception --path /home/lee/robotics-skills \
  --resources scripts,references,assets \
  --interface display_name="Robotics Vision Perception" \
  --interface short_description="Validate and diagnose ROS 2 vision pipelines" \
  --interface default_prompt="Use $robotics-vision-perception to validate this camera or vision pipeline."
```

Run the equivalent command for the other seven exact names. Remove generated
placeholder/example files that are not part of the design; retain
`agents/openai.yaml` only if it validates and remains optional.

- [ ] **Step 2: Copy the root MIT license into each new skill**

Use a mechanical copy and verify byte identity:

```bash
for skill in robotics-vision-perception robotics-3d-perception \
  robotics-manipulation robotics-hand-eye-calibration robotics-force-control \
  robotics-legged-wbc robotics-research-reproduction robotics-benchmarking
do
  cp LICENSE "$skill/LICENSE.txt"
  cmp LICENSE "$skill/LICENSE.txt"
done
```

Expected: every `cmp` exits `0`.

- [ ] **Step 3: Write the common JSON schema**

The schema must require:

```json
{
  "schema_version": "1.0.0",
  "skill": "robotics-example",
  "check": "example",
  "status": "pass",
  "summary": "completed",
  "inputs": [],
  "environment": {},
  "metrics": {},
  "gates": [],
  "findings": [],
  "evidence": [],
  "limitations": []
}
```

Use enums for `status` and finding/gate severity, disallow unknown top-level
keys, and define metric objects with `value`, `unit`, and optional `direction`.

- [ ] **Step 4: Write the lightweight result helper**

```python
STATUSES = {"pass", "warn", "fail", "skip"}

def overall_status(findings, requested="pass"):
    levels = {item["level"] for item in findings}
    if "fail" in levels:
        return "fail"
    if requested == "skip":
        return "skip"
    if "warn" in levels:
        return "warn"
    return requested

def make_result(*, skill, check, summary, findings=None, metrics=None,
                inputs=None, environment=None, gates=None, evidence=None,
                limitations=None, requested_status="pass"):
    findings = list(findings or [])
    return {
        "schema_version": "1.0.0",
        "skill": skill,
        "check": check,
        "status": overall_status(findings, requested_status),
        "summary": summary,
        "inputs": list(inputs or []),
        "environment": dict(environment or {}),
        "metrics": dict(metrics or {}),
        "gates": list(gates or []),
        "findings": findings,
        "evidence": list(evidence or []),
        "limitations": list(limitations or []),
    }
```

Add deterministic JSON writing with sorted keys and exit selection:
`fail -> 1`, invalid input -> `2`, otherwise `0`.

- [ ] **Step 5: Copy schema and helper into every skill**

Use mechanical copies. Runtime imports must resolve from the skill's own
`scripts/` directory.

- [ ] **Step 6: Implement the repository checker**

`tools/check_engineering_skills.py` loads the YAML manifest, verifies every
declared path, confirms schema/helper SHA-256 identity, checks fixture presence,
and rejects cross-skill imports or paths in runtime scripts.

- [ ] **Step 7: Add tests for status precedence and schema identity**

```python
def test_fail_finding_controls_overall_status(self):
    module = load_result_contract(VISION_ROOT)
    result = module.make_result(
        skill="robotics-vision-perception",
        check="camera",
        summary="bad",
        findings=[{"level": "fail", "code": "bad_stride", "message": "bad"}],
    )
    self.assertEqual(result["status"], "fail")

def test_result_schemas_are_byte_identical(self):
    payloads = {(REPO / skill / "assets/result.schema.json").read_bytes()
                for skill in ENGINEERING_SKILLS}
    self.assertEqual(len(payloads), 1)
```

- [ ] **Step 8: Run foundation tests**

```bash
python3 -m unittest tests.test_engineering_skill_contract -v
python3 tools/check_engineering_skills.py
```

Expected: result-helper tests pass; path checks still name domain files not yet
implemented.

- [ ] **Step 9: Commit only foundation files**

```bash
git add tools/result.schema.json tools/result_contract_template.py \
  tools/check_engineering_skills.py tools/engineering_skills_manifest.yaml \
  tests/test_engineering_skill_contract.py \
  robotics-vision-perception robotics-3d-perception robotics-manipulation \
  robotics-hand-eye-calibration robotics-force-control robotics-legged-wbc \
  robotics-research-reproduction robotics-benchmarking
git commit -m "feat: scaffold engineering skill contracts"
```

### Task 3: Build `robotics-research-reproduction`

**Files:**
- Create: `robotics-research-reproduction/SKILL.md`
- Create: `robotics-research-reproduction/references/provenance_and_environment.md`
- Create: `robotics-research-reproduction/references/baselines_ablations_reporting.md`
- Create: `robotics-research-reproduction/scripts/validate_reproduction_manifest.py`
- Create: `robotics-research-reproduction/assets/run_manifest.example.yaml`
- Create: `robotics-research-reproduction/assets/fixtures/reproduction_valid.yaml`
- Create: `robotics-research-reproduction/assets/fixtures/reproduction_floating_ref.yaml`
- Test: `tests/test_research_reproduction.py`

- [ ] **Step 1: Write failing immutable-provenance tests**

```python
def test_valid_manifest_passes(self):
    result = run_script("reproduction_valid.yaml")
    self.assertEqual(result.returncode, 0)
    self.assertEqual(json.loads(result.stdout)["status"], "pass")

def test_floating_revision_fails(self):
    result = run_script("reproduction_floating_ref.yaml")
    self.assertEqual(result.returncode, 1)
    self.assertIn("immutable_revision", result.stdout)
```

- [ ] **Step 2: Run and verify failure**

```bash
python3 -m unittest tests.test_research_reproduction -v
```

Expected: `FAIL` because the validator does not exist.

- [ ] **Step 3: Implement manifest validation**

Require repository URL plus full commit SHA, environment inventory or locked
container digest, dataset source/license/split/SHA-256, nonempty seeds, repeat
policy, baseline command/config, metric unit/direction, isolated ablation
variables, evidence paths, and declared deviations. Reject `main`, `master`,
`latest`, branch-only references, and unhashed data.

- [ ] **Step 4: Write the references and concise workflow**

`SKILL.md` must route paper setup questions to provenance, comparison questions
to baseline parity, and experimental claims to the reporting checklist. State
that a matching command exit is not evidence that reported paper metrics were
reproduced.

- [ ] **Step 5: Run tests and standalone validation**

```bash
python3 -m unittest tests.test_research_reproduction -v
python3 robotics-research-reproduction/scripts/validate_reproduction_manifest.py \
  robotics-research-reproduction/assets/fixtures/reproduction_valid.yaml
```

Expected: all tests pass and CLI exits `0`.

- [ ] **Step 6: Commit exact files**

```bash
git add robotics-research-reproduction tests/test_research_reproduction.py
git commit -m "feat: add research reproduction skill"
```

### Task 4: Build `robotics-benchmarking`

**Files:**
- Create: `robotics-benchmarking/SKILL.md`
- Create: `robotics-benchmarking/references/benchmark_design.md`
- Create: `robotics-benchmarking/references/statistics_and_regression.md`
- Create: `robotics-benchmarking/scripts/validate_benchmark_manifest.py`
- Create: `robotics-benchmarking/scripts/run_benchmark.py`
- Create: `robotics-benchmarking/scripts/aggregate_results.py`
- Create: benchmark manifest/result fixtures
- Test: `tests/test_benchmarking.py`

- [ ] **Step 1: Write failing safety and aggregation tests**

```python
def test_scalar_shell_command_is_rejected(self):
    result = run_validator("benchmark_shell_string.yaml")
    self.assertEqual(result.returncode, 1)
    self.assertIn("argv_array_required", result.stdout)

def test_failures_remain_in_denominator(self):
    summary = aggregate("mixed_results")
    self.assertEqual(summary["metrics"]["failure_rate"]["value"], 1 / 3)
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python3 -m unittest tests.test_benchmarking -v
```

Expected: missing scripts/fixtures fail.

- [ ] **Step 3: Implement manifest validation**

Require command as a nonempty string array, bounded timeout/repeats/warmups,
working directory, explicit metric unit/direction, seed policy, and a fresh
output directory. Reject shell metacharacter strings as command substitutes.

- [ ] **Step 4: Implement safe execution**

Use `subprocess.run(argv, shell=False, timeout=..., cwd=..., capture_output=True,
text=True)`. Require `--execute`; without it only validate and report a
deliberate `skip`. Refuse an existing nonempty output directory.

- [ ] **Step 5: Implement aggregation**

Include every run in counts. Compute failure/skip rates and, for numeric
successful samples, mean, median, population standard deviation, and requested
nearest-rank percentiles. Evaluate thresholds according to explicit
`higher_is_better` or `lower_is_better`.

- [ ] **Step 6: Run tests and a harmless fixture command**

```bash
python3 -m unittest tests.test_benchmarking -v
python3 robotics-benchmarking/scripts/run_benchmark.py \
  robotics-benchmarking/assets/fixtures/benchmark_echo.yaml
```

Expected: tests pass; the second command returns a schema-valid `skip` because
`--execute` was omitted.

- [ ] **Step 7: Commit exact files**

```bash
git add robotics-benchmarking tests/test_benchmarking.py
git commit -m "feat: add safe robotics benchmarking skill"
```

### Task 5: Build `robotics-vision-perception`

**Files:**
- Create: `robotics-vision-perception/SKILL.md`
- Create: vision references, scripts, JSON fixtures and run manifest
- Test: `tests/test_vision_perception.py`

- [ ] **Step 1: Write failing contract and metric tests**

```python
def test_bad_row_stride_fails(self):
    result = run_camera("camera_bad_stride.json")
    self.assertEqual(result.returncode, 1)
    self.assertIn("image_data_length", result.stdout)

def test_known_detection_metrics(self):
    payload = run_eval("detections_known.json")
    self.assertEqual(payload["metrics"]["true_positive"]["value"], 1)
    self.assertEqual(payload["metrics"]["false_positive"]["value"], 1)
    self.assertEqual(payload["metrics"]["false_negative"]["value"], 1)
```

- [ ] **Step 2: Verify failure**

```bash
python3 -m unittest tests.test_vision_perception -v
```

- [ ] **Step 3: Implement camera contract analysis**

Validate legal positive dimensions, `step * height == data_length`, supported
encoding byte widths, Image/CameraInfo dimensions and frame equality, finite
K/R/P/D values, recognized distortion model, monotonic acquisition stamps,
and explicit pairing skew threshold.

- [ ] **Step 4: Implement deterministic 2D evaluation**

Validate `[x, y, width, height]`, class, score, image ID, and threshold. Match
same-class predictions to unmatched ground truth by descending score and
highest IoU. Emit TP/FP/FN, precision, recall, and mean matched IoU.

- [ ] **Step 5: Write Humble-scoped references and fixtures**

State optical frame axes, acquisition-time semantics, synchronization versus
latency, QoS admission, encoding/stride rules, calibration prerequisites,
pre/post-processing parity, and dataset leakage limits.

- [ ] **Step 6: Run tests and valid fixture**

```bash
python3 -m unittest tests.test_vision_perception -v
python3 robotics-vision-perception/scripts/check_camera_contract.py \
  robotics-vision-perception/assets/fixtures/camera_valid.json
```

Expected: pass.

- [ ] **Step 7: Commit exact files**

```bash
git add robotics-vision-perception tests/test_vision_perception.py
git commit -m "feat: add vision perception engineering skill"
```

### Task 6: Build `robotics-3d-perception`

**Files:**
- Create: `robotics-3d-perception/SKILL.md`
- Create: 3D references, scripts, fixtures and run manifest
- Test: `tests/test_3d_perception.py`

- [ ] **Step 1: Write failing endian/layout and matching tests**

```python
def test_truncated_cloud_fails(self):
    result = run_cloud("cloud_truncated.json")
    self.assertEqual(result.returncode, 1)
    self.assertIn("data_length", result.stdout)

def test_big_endian_xyz_is_decoded(self):
    result = run_cloud("cloud_big_endian.json")
    self.assertEqual(result.returncode, 0)
    self.assertEqual(result_json(result)["metrics"]["finite_ratio"]["value"], 1.0)
```

- [ ] **Step 2: Verify failure**

```bash
python3 -m unittest tests.test_3d_perception -v
```

- [ ] **Step 3: Implement PointCloud2 fixture parsing**

Decode `data_hex`, map ROS PointField datatypes to `struct` formats, honor
endianness, validate count/offset bounds, `point_step`, organized `row_step`
padding, total data length, and finite XYZ ratio. Check frame/stamp and
algorithm-declared time/ring requirements.

- [ ] **Step 4: Implement deterministic 3D result evaluation**

Validate frame, class, center, size, yaw, and score. Match by class and explicit
center-distance/size/yaw gates; report TP/FP/FN and translation/yaw errors.
Do not label this simplified admission metric as oriented 3D IoU.

- [ ] **Step 5: Write references and fixtures**

Cover field semantics, deskew, TF, filtering, registration admission,
segmentation/clustering, 3D output frames, evaluation metrics, and corridor/
glass/dynamic-scene limitations without universal rankings.

- [ ] **Step 6: Run tests and commit**

```bash
python3 -m unittest tests.test_3d_perception -v
git add robotics-3d-perception tests/test_3d_perception.py
git commit -m "feat: add 3d perception engineering skill"
```

### Task 7: Build `robotics-manipulation`

**Files:**
- Create: `robotics-manipulation/SKILL.md`
- Create: manipulation references, config fixtures and run manifest
- Create: `robotics-manipulation/scripts/check_moveit_config.py`
- Test: `tests/test_manipulation.py`

- [ ] **Step 1: Write failing cross-file consistency tests**

```python
def test_valid_moveit_snapshot_passes(self):
    result = run_check("moveit_valid")
    self.assertEqual(result.returncode, 0)

def test_controller_joint_mismatch_fails(self):
    result = run_check("moveit_bad_controller")
    self.assertEqual(result.returncode, 1)
    self.assertIn("controller_joint_set", result.stdout)
```

- [ ] **Step 2: Verify failure**

```bash
python3 -m unittest tests.test_manipulation -v
```

- [ ] **Step 3: Implement URDF/SRDF/YAML parsing**

Use `xml.etree.ElementTree` and PyYAML. Build link/joint sets, movable and mimic
joints, limits, ros2_control interfaces, SRDF group chains/joints/end effectors
and virtual/passive joints. Cross-check kinematics groups, joint limit
overrides, planning pipelines, and MoveIt controller joint/action mappings.

- [ ] **Step 4: Add optional ROS discovery**

With `--ros-check`, look for MoveIt packages and configured action names.
Missing optional packages produce `skip`; malformed required config remains
exit `2`; discovered mismatches are exit `1`.

- [ ] **Step 5: Write references and fixtures**

Cover PlanningScene, planner selection, MTC, time parameterization, execution
monitoring, and planning-versus-controller failure isolation. Keep Humble API
examples separate from later distributions.

- [ ] **Step 6: Run tests and commit**

```bash
python3 -m unittest tests.test_manipulation -v
git add robotics-manipulation tests/test_manipulation.py
git commit -m "feat: add MoveIt manipulation skill"
```

### Task 8: Build `robotics-hand-eye-calibration`

**Files:**
- Create: `robotics-hand-eye-calibration/SKILL.md`
- Create: calibration references, scripts, fixtures and run manifest
- Test: `tests/test_handeye_calibration.py`

- [ ] **Step 1: Write failing observability and residual tests**

```python
def test_single_axis_dataset_fails(self):
    result = run_validator("handeye_single_axis.json")
    self.assertEqual(result.returncode, 1)
    self.assertIn("rotation_axis_diversity", result.stdout)

def test_valid_candidate_passes_holdout(self):
    result = result_json(run_validator("handeye_valid.json"))
    self.assertEqual(result["status"], "pass")
    self.assertIn("holdout_rotation_rmse_deg", result["metrics"])
```

- [ ] **Step 2: Verify failure**

```bash
python3 -m unittest tests.test_handeye_calibration -v
```

- [ ] **Step 3: Implement transform math and AX=XB validation**

Implement normalized XYZW quaternions, multiplication, inverse, vector
rotation, transform composition, and angular distance in standard-library
Python. Validate frame labels, pairing skew, sample uniqueness, translation
span, at least two materially distinct rotation axes, and candidate
`A X = X B` closure on fit and held-out samples.

- [ ] **Step 4: Write references and fixtures**

Explain eye-in-hand/eye-to-hand frame equations, target/intrinsic admission,
sampling geometry, solver comparison, residual versus independent validation,
and TF deployment rollback. Do not select a solver from training residual
alone.

- [ ] **Step 5: Run tests and commit**

```bash
python3 -m unittest tests.test_handeye_calibration -v
git add robotics-hand-eye-calibration tests/test_handeye_calibration.py
git commit -m "feat: add hand-eye calibration skill"
```

### Task 9: Build `robotics-force-control`

**Files:**
- Create: `robotics-force-control/SKILL.md`
- Create: force references, scripts, CSV/YAML fixtures and run manifest
- Test: `tests/test_force_control.py`

- [ ] **Step 1: Write failing log and safety-config tests**

```python
def test_saturated_wrench_log_fails(self):
    result = run_log("wrench_saturated.csv")
    self.assertEqual(result.returncode, 1)
    self.assertIn("saturation_fraction", result.stdout)

def test_missing_timeout_safe_state_fails(self):
    result = run_config("force_config_unsafe.yaml")
    self.assertEqual(result.returncode, 1)
    self.assertIn("timeout_safe_state", result.stdout)
```

- [ ] **Step 2: Verify failure**

```bash
python3 -m unittest tests.test_force_control -v
```

- [ ] **Step 3: Implement wrench-log analysis**

Require time plus six wrench axes, explicit SI units and frame. Compute sample
rate, monotonic stamps, mean bias, RMS about mean, linear drift slope,
saturation count/fraction, and configured gates without inferring contact from
one threshold.

- [ ] **Step 4: Implement force configuration checks**

Validate six-axis interface mapping, F/T/control/world/gravity frames,
kinematics package/plugin, selected axes, array lengths, finite positive mass/
damping and nonnegative stiffness, CoG/payload force, filters, watchdog,
command slew/force/torque limits, and a gravity-aware safe timeout state.

- [ ] **Step 5: Write references and fixtures**

Separate sensor admission, gravity compensation, control laws, contact
transitions, passivity/latency, staged commissioning, and hardware acceptance.
Never call a software stop safety-rated.

- [ ] **Step 6: Prove scripts are read-only**

Add a source test rejecting `rclpy.create_publisher`, `ros2 topic pub`,
controller activation, and subprocess calls in force runtime scripts.

- [ ] **Step 7: Run tests and commit**

```bash
python3 -m unittest tests.test_force_control -v
git add robotics-force-control tests/test_force_control.py
git commit -m "feat: add force-control engineering skill"
```

### Task 10: Build `robotics-legged-wbc`

**Files:**
- Create: `robotics-legged-wbc/SKILL.md`
- Create: WBC references, URDF/YAML fixtures and run manifest
- Create: `robotics-legged-wbc/scripts/check_wbc_contract.py`
- Test: `tests/test_legged_wbc.py`

- [ ] **Step 1: Write failing joint/contact/fallback tests**

```python
def test_joint_order_mismatch_fails(self):
    result = run_check("wbc_bad_joint_order.yaml")
    self.assertEqual(result.returncode, 1)
    self.assertIn("actuated_joint_order", result.stdout)

def test_missing_fallback_fails(self):
    result = run_check("wbc_missing_fallback.yaml")
    self.assertEqual(result.returncode, 1)
    self.assertIn("degraded_state", result.stdout)
```

- [ ] **Step 2: Verify failure**

```bash
python3 -m unittest tests.test_legged_wbc -v
```

- [ ] **Step 3: Implement URDF and contract checks**

Parse links, joints, limits, inertials and contact frames. Validate base
representation and dimensions, exact actuated joint order, quaternion order,
positive finite mass/inertias, friction and force bounds, task dimensions/
weights/priorities, solver time/iteration/residual gates, controller-estimator
rate relationships, command timeout, and safe degraded states.

- [ ] **Step 4: Add optional Pinocchio admission**

With `--pinocchio-check`, import Pinocchio and compare model joint order and
dimensions. Missing Pinocchio is `skip`; a loaded model mismatch is `fail`.

- [ ] **Step 5: Write references and fixtures**

Cover state/contact estimation contracts, centroidal/full dynamics, QP
constraints, task hierarchy, contact transitions, solver health, real-time
budgets, fall/estimator/communication fallback, and simulation-to-hardware
admission. Do not include a toy controller presented as deployment-ready.

- [ ] **Step 6: Prove the runtime script is read-only**

Reject publisher creation, motor/controller activation and arbitrary
subprocess execution in source tests.

- [ ] **Step 7: Run tests and commit**

```bash
python3 -m unittest tests.test_legged_wbc -v
git add robotics-legged-wbc tests/test_legged_wbc.py
git commit -m "feat: add legged WBC engineering skill"
```

### Task 11: Integrate documentation, quality tools and CI

**Files:**
- Modify: `README.md`
- Modify: `tests/test_repository_quality.py`
- Modify: `tools/check_repository.py`
- Modify: `.github/workflows/quality.yml`
- Modify: `requirements-dev.txt` only if a new lightweight validator is needed

- [ ] **Step 1: Write failing README and release-contract tests**

Require all fourteen skills, the engineering-versus-algorithm boundary, Humble
baseline, optional vendor adapters, common result contract, and hardware
acceptance limitation.

- [ ] **Step 2: Update README**

Replace six-skill counts and the old "not covered" list. State that the new
skills provide admission, diagnosis, configuration validation and evaluation,
not production algorithms or real-hardware proof.

- [ ] **Step 3: Extend repository checker**

Call `tools/check_engineering_skills.py`, validate all manifest-declared
scripts/fixtures, scan new markdown, and reject cross-skill runtime paths,
unsafe actuation claims, floating version examples, or a `SKIP`-as-pass phrase.

- [ ] **Step 4: Extend CI**

Run:

```yaml
- run: python tools/check_engineering_skills.py
- run: python -m unittest discover -s tests -v
- run: python -m compileall -q robotics-*/scripts tools tests
```

Keep official `agentskills validate` on Python 3.12 and do not install heavy
ROS/perception/simulator stacks in ordinary CI.

- [ ] **Step 5: Run integration checks**

```bash
python3 tools/check_repository.py
python3 tools/check_engineering_skills.py
python3 tools/check_doc_params.py
python3 -m unittest discover -s tests -v
```

Expected: all pass.

- [ ] **Step 6: Commit only integration files**

Some of these files contain prior uncommitted work. Inspect the exact diff and
do not commit unrelated hunks. If clean separation is not possible, leave the
overlapping files uncommitted and report that boundary rather than staging
someone else's work.

### Task 12: Full verification and forward-use audit

**Files:**
- Modify only files implicated by observed failures

- [ ] **Step 1: Run every deterministic valid/invalid fixture**

Use the engineering manifest to execute the declared primary script on both
fixtures. Confirm valid exits `0`, invalid exits `1` or `2`, and every emitted
JSON conforms to the required common fields.

- [ ] **Step 2: Run all repository gates**

```bash
python3 -m unittest discover -s tests -v
python3 tools/check_repository.py
python3 tools/check_engineering_skills.py
python3 tools/check_doc_params.py
python3 tools/check_doc_params.py --selftest
python3 -m compileall -q robotics-*/scripts tools tests
git diff --check
```

- [ ] **Step 3: Validate all fourteen skills**

```bash
for skill in robotics-*/SKILL.md; do
  python3 /home/lee/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
    "$(dirname "$skill")"
done
```

On Python 3.11+, also run:

```bash
for skill in robotics-*/SKILL.md; do
  agentskills validate "$(dirname "$skill")"
done
```

- [ ] **Step 4: Run conditional Humble smoke checks**

Inspect installed packages first. Run only read-only discovery or subscription
checks for available Image/CameraInfo/PointCloud2/Wrench, MoveIt and
ros2_control interfaces. Record unavailable heavy dependencies as `SKIP`.

- [ ] **Step 5: Forward-use each skill**

For each skill, issue one realistic user-style request with only the skill
artifact and raw fixture/config available. Verify that the workflow chooses
the correct script/reference, emits evidence, and does not claim algorithm or
hardware completion.

- [ ] **Step 6: Audit completion against the design**

Create a requirement-to-evidence checklist for every item under the design's
Completion Criteria. Treat missing or indirect evidence as incomplete and fix
it before reporting success.

- [ ] **Step 7: Inspect final repository state**

```bash
git status --short
git log --oneline --decorate -12
```

Report exact committed and uncommitted boundaries. Do not push.
