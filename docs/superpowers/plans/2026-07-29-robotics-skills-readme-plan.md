# Detailed Robotics Skills README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a detailed, layered repository README that lets a new user start quickly and lets an engineer understand every skill, executable checker, dependency, result, and acceptance boundary.

**Architecture:** Keep all repository-level orientation in `README.md`, while linking rather than duplicating skill-local references. Extend the repository quality test with an explicit README content contract, then implement the fast-orientation layer, engineering-manual layer, and executable examples against the current fourteen-skill tree.

**Tech Stack:** Markdown, Python 3.10 `unittest`, repository-owned Python/YAML/JSON fixtures, Agent Skills directory conventions, ROS 2 Humble terminology.

---

### Task 1: Define the README content contract

**Files:**
- Modify: `tests/test_repository_quality.py`
- Test: `tests/test_repository_quality.py`

- [ ] **Step 1: Add a failing detailed-README test**

Add a test that requires the approved information architecture, all primary
scripts, exact result states, exit semantics, optional dependencies, and
hardware limitations:

```python
def test_readme_is_a_detailed_user_and_engineering_guide(self) -> None:
    text = (REPO / "README.md").read_text(encoding="utf-8")
    for heading in (
        "## 30 秒选择技能",
        "## 快速开始",
        "## 十四个技能全景",
        "## 八个工程技能详解",
        "## 工程脚本索引",
        "## 依赖与 `skip`",
        "## 证据等级与实机边界",
        "## 常见问题",
    ):
        self.assertIn(heading, text)
    for script in (
        "check_camera_contract.py",
        "evaluate_vision_results.py",
        "check_pointcloud_contract.py",
        "evaluate_3d_results.py",
        "check_moveit_config.py",
        "validate_handeye.py",
        "analyze_wrench_log.py",
        "check_force_config.py",
        "check_wbc_contract.py",
        "validate_reproduction_manifest.py",
        "validate_benchmark_manifest.py",
        "run_benchmark.py",
        "aggregate_results.py",
    ):
        self.assertIn(script, text)
    for phrase in (
        "`pass`、`warn`、`fail`、`skip`",
        "退出码 `0`",
        "退出码 `1`",
        "退出码 `2`",
        "MoveIt",
        "Pinocchio",
        "只读",
        "不等于实机验收",
    ):
        self.assertIn(phrase, text)
```

- [ ] **Step 2: Run the new test and verify RED**

Run:

```bash
python3 -m unittest \
  tests.test_repository_quality.RepositoryQualityTests.test_readme_is_a_detailed_user_and_engineering_guide -v
```

Expected: `FAIL`, first reporting the missing `## 30 秒选择技能` heading.

- [ ] **Step 3: Commit the test only after observing the expected failure**

Do not commit the test separately because `tests/test_repository_quality.py`
already belongs to the wider uncommitted quality-work set. Preserve its current
working-tree ownership and include only the README in the dedicated README
commit.

### Task 2: Write the fast-orientation layer

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace the introductory summary**

State the Humble baseline, fourteen independently installable skills, eight
engineering skills, portable core, and explicit non-goals in the opening.

- [ ] **Step 2: Add task-to-skill routing**

Add `## 30 秒选择技能` with symptom-oriented rows covering control, SLAM, Nav2,
ROS infrastructure, sim-to-real, frontend, 2D/3D perception, MoveIt, hand-eye,
force, WBC, reproduction, and benchmarking.

- [ ] **Step 3: Add the runnable quick start**

Add `## 快速开始` with:

```bash
git clone https://github.com/bernardleex526-png/robotics-skills.git
cd robotics-skills
mkdir -p ~/.agents/skills
cp -R robotics-vision-perception ~/.agents/skills/
python3 robotics-vision-perception/scripts/check_camera_contract.py \
  robotics-vision-perception/assets/fixtures/camera_valid.json
```

Explain natural-language triggering, complete-directory copying, and the four
result states immediately after the command.

- [ ] **Step 4: Preserve multi-client installation guidance**

Keep accurate Codex, Claude Code, CodeBuddy, and WorkBuddy sections. Do not
claim that the repository root is a native plugin or that one fixed WorkBuddy
filesystem path is universal.

### Task 3: Write the engineering-manual layer

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add the fourteen-skill system view**

Add `## 十四个技能全景`, group the skills into infrastructure/control,
localization/navigation, perception/manipulation, and research/evaluation, and
link every skill directory.

- [ ] **Step 2: Add short profiles for the six workflow/reference skills**

For motion control, SLAM, Nav2, ROS 2 infrastructure, sim-to-real, and frontend,
state the trigger, owned scope, useful entry points, and boundary.

- [ ] **Step 3: Add detailed profiles for all eight engineering skills**

Add `## 八个工程技能详解`. Each profile must contain inputs, scripts, example
command, key gates, optional dependencies or `skip`, and explicit limitations.
All commands must use paths that exist in the repository.

- [ ] **Step 4: Add the complete script index**

Add `## 工程脚本索引` and list all thirteen primary scripts with their input,
purpose, output, and whether they can execute an external command. State that
only `run_benchmark.py --execute` executes the declared bounded argv command.

- [ ] **Step 5: Document the common result contract**

Include the required JSON fields:

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

Define `pass`, `warn`, `fail`, `skip`, and exits `0`, `1`, `2` without implying
that `skip` is a pass.

- [ ] **Step 6: Add dependency and evidence-level sections**

Add `## 依赖与 \`skip\`` and `## 证据等级与实机边界`. Separate the portable
Python core from ROS messages/PCL, MoveIt, ros2_control force plugins,
Pinocchio, GPU/simulator stacks, and hardware. Describe offline fixture,
configuration snapshot, live ROS smoke, simulation, controlled hardware, and
whole-system acceptance as distinct evidence levels.

### Task 4: Complete maintainer and FAQ guidance

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add repository layout and development commands**

Document skill-local versus root-maintainer assets, `requirements-dev.txt`,
unit tests, repository checker, engineering checker, parameter checker,
`compileall`, `git diff --check`, and the Python 3.11+ Agent Skills reference
validator.

- [ ] **Step 2: Add contribution rules**

Require Humble/version labels, upstream primary sources for version-sensitive
facts, valid/invalid fixtures for deterministic checks, unchanged result
semantics, no cross-skill runtime imports, and explicit hardware limitations.

- [ ] **Step 3: Add FAQ**

Answer at least:

- whether all fourteen skills must be installed;
- why a check can exit `0` with `skip`;
- why MoveIt or Pinocchio may be absent;
- whether offline fixture success proves algorithm or hardware readiness;
- how another ROS distribution should be handled;
- where detailed parameter and workflow content lives.

### Task 5: Verify content and runnable examples

**Files:**
- Verify: `README.md`
- Verify: `tests/test_repository_quality.py`

- [ ] **Step 1: Run the focused README test and verify GREEN**

Run:

```bash
python3 -m unittest \
  tests.test_repository_quality.RepositoryQualityTests.test_readme_is_a_detailed_user_and_engineering_guide -v
```

Expected: `OK`.

- [ ] **Step 2: Run representative README commands**

Run the camera, MoveIt fixture, wrench log, WBC, reproduction, benchmark
validation, benchmark dry-run, and harmless explicit benchmark examples.
Expected: valid fixture checks exit `0`; optional runtime probes may emit
`skip`; benchmark dry-run does not execute the declared command.

- [ ] **Step 3: Run repository verification**

```bash
python3 -m unittest discover -s tests -v
python3 tools/check_repository.py
python3 tools/check_engineering_skills.py
python3 tools/check_doc_params.py
python3 -m compileall -q robotics-*/scripts tools tests
git diff --check
```

Expected: all commands exit `0`, with 102 or more unit tests, fourteen skills,
eight engineering skills, and no Markdown or Python errors.

- [ ] **Step 4: Inspect the final README diff**

Confirm that only accurate current paths and commands were added, no existing
user changes were removed unintentionally, and the README does not claim
hardware or algorithm acceptance.

- [ ] **Step 5: Commit only the README**

```bash
git add README.md
git commit -m "docs: add detailed robotics skills guide"
```

Leave the pre-existing uncommitted quality tests, tools, skill corrections, and
support files in the working tree.
