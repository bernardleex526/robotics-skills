# Robotics Skills Quality Release Design

Date: 2026-07-29

Status: Approved

## Goal

Turn this repository into a reliable ROS 2 robot-system engineering skill pack:

- correct the confirmed technical and safety errors;
- make version assumptions and cross-version differences explicit;
- make every skill independently installable under the Agent Skills layout;
- provide executable diagnostics where they materially improve troubleshooting;
- add automated checks that prevent the known errors from returning.

The pack is intentionally positioned as system integration, diagnostics, and
deployment guidance. It does not claim to be a complete robotics-algorithm
library or a substitute for hardware validation and safety certification.

## Supported Scope

The release contains six skills:

1. `robotics-motion-control`
2. `robotics-slam`
3. `robotics-frontend`
4. `robotics-sim2real`
5. `robotics-nav2`
6. `robotics-ros2-infra`

ROS 2 Humble is the documented baseline. Where APIs or parameter names differ
in later distributions, the skill must identify the distribution rather than
mixing variants in one example.

Perception algorithms, manipulation planning, hand-eye calibration, force
control, whole-body control, and algorithm research workflows remain explicit
roadmap items. They will not be represented by shallow placeholder skills.

## Repository Structure

Each skill is self-contained:

```text
<skill-name>/
├── SKILL.md
├── references/
└── scripts/        # only when the skill itself uses executable helpers
```

Runtime ROS diagnostics belong to `robotics-ros2-infra/scripts/`, because they
are part of that skill's operational workflow. Repository-maintenance tooling
belongs to `tools/`; it is not presented as a runtime dependency of an
individually installed skill.

Tests live under `tests/`, and CI runs the same commands documented in the
contributor section.

## Content Rules

- Prefer canonical ROS 2 interface names such as
  `geometry_msgs/msg/Twist`.
- Bind concrete parameters and CLI behavior to a named ROS distribution.
- Link primary upstream documentation or source for version-sensitive claims.
- Present thresholds and tuning ranges as measured examples unless they are
  protocol or API requirements.
- Separate symptom evidence from conclusions. A diagnostic tool may report
  timestamp age, but must not claim that low age proves a driver overwrote the
  sensor timestamp.
- Do not call a browser or software command a safety-rated emergency stop.
- Do not prescribe hazardous commissioning methods or fixed low-power
  percentages across unrelated robots.
- Standards references are risk-assessment pointers, not certification claims.

## Diagnostics Design

`check_tf_tree.py`:

- uses wall-clock monotonic time for bounded sampling;
- reports multiple roots, missing roots, cycles, disconnected frames, and
  stale dynamic transforms without crashing;
- treats ROS-time and wall-time mismatch as uncertainty, not a false failure.

`check_topic_health.py`:

- uses monotonic time for duration and arrival-rate measurements;
- reports frequency, monotonicity, duplicate stamps, and observable stamp age;
- labels clock-domain and source-vs-receipt-time conclusions as unknown unless
  independently established;
- defaults to broadly compatible live-data QoS and exposes deliberate
  durability selection.

Both scripts separate pure analysis from ROS adapters so their logic can be
unit-tested without a running ROS graph.

## Validation Design

The release gate consists of:

1. Agent Skills structure and frontmatter checks.
2. Resolution of every local file reference.
3. Regression checks for known-invalid package names, parameters, message
   types, unsafe wording, and broken command examples.
4. Version-aware parameter manifest checks.
5. Unit tests for TF and topic-health analysis.
6. Python syntax checks.
7. CI execution on a clean checkout.

Passing these checks means no known P0/P1 defect remains inside the documented
scope. It does not prove compatibility with every robot, ROS distribution,
DDS vendor, browser, or safety architecture.

## Client Portability

Frontmatter uses the portable Agent Skills core fields. The README documents
the current project/user locations for Codex, Claude Code, and CodeBuddy, plus
the supported WorkBuddy import flow. Client-specific metadata is optional and
must not be required for the skill content to work.

## Change Safety

The existing uncommitted files are treated as prior work. Corrections are
applied surgically on top of them. No commit, push, release, or marketplace
publication is included in this implementation.
