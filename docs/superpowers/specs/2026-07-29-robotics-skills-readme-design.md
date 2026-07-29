# Robotics Skills README Design

Date: 2026-07-29  
Status: Approved

## Goal

Replace the repository-root README summary with a detailed, evidence-based
entry point for the complete fourteen-skill pack. The document must serve two
readers without duplicating the skill references:

1. a first-time robotics developer who needs to select, install, and invoke a
   skill quickly;
2. an algorithm or systems engineer who needs exact inputs, scripts, result
   semantics, optional dependencies, and verification boundaries.

The README documents the repository as it exists. It does not turn optional
software discovery into a compatibility claim or offline checks into
real-hardware acceptance.

## Information Architecture

Use a layered structure.

### Layer 1: Fast orientation

The first part answers, in order:

- What is this repository?
- What is it not?
- Which skill matches the current problem?
- How is one complete skill installed?
- How can a bundled fixture be checked without hardware?
- What do `pass`, `warn`, `fail`, and `skip` mean?

This layer includes a task-to-skill routing table, one Codex installation
example, one natural-language invocation example, and one executable offline
example. It warns users to copy a complete skill directory rather than only
`SKILL.md`.

### Layer 2: Engineering manual

The second part contains:

- a fourteen-skill catalog grouped by system layer;
- concise profiles for the six existing workflow/reference skills;
- detailed, consistently structured profiles for the eight engineering
  skills;
- a complete primary-script command index;
- the common JSON result and exit-code contract;
- core versus optional dependency and `skip` behavior;
- evidence levels from offline admission through real-hardware acceptance;
- repository layout, maintainer verification, contribution rules, FAQ, version
  baseline, and license.

## Skill Profile Contract

Each of the eight engineering profiles states:

1. when to use the skill;
2. required input artifacts;
3. primary scripts;
4. a minimal command;
5. key gates and metrics;
6. optional runtime dependencies;
7. what produces `skip`;
8. what a successful offline result does not prove.

The six existing skills use a shorter profile: trigger, owned scope, useful
entry points, and boundary. Their detailed workflows remain in their own
`SKILL.md` and `references/`.

## Accuracy and Safety Rules

- ROS 2 Humble is the executable baseline.
- Other ROS distributions and vendor stacks are named only as explicit,
  version-sensitive alternatives.
- Heavy packages such as MoveIt, Pinocchio, GPU stacks, simulators, and hardware
  drivers remain optional unless a specific command requires them.
- `skip` means an optional dependency or runtime condition was unavailable. It
  is not rewritten as `pass`.
- Exit `0` covers `pass`, `warn`, and deliberate optional-runtime `skip`; exit
  `1` is a domain gate failure; exit `2` is invalid required input.
- Force-control and WBC tools are described as read-only.
- No wording may imply that fixture success proves calibration accuracy,
  algorithm quality, real-time behavior, safe motion, or whole-robot
  acceptance.
- Installation paths must match the named client and must not claim that the
  repository is a native multi-skill plugin.

## Examples

Examples use repository-owned fixtures and commands that can run from a cloned
checkout. They do not require live sensors or actuators. At minimum the README
contains:

- one camera-contract check;
- one MoveIt configuration check;
- one force-log analysis;
- one WBC contract check;
- one reproduction-manifest check;
- one benchmark dry run and one explicit harmless execution example.

Long reference material stays in each skill. The README links to source files
instead of copying complete parameter tables or algorithms.

## Verification

README completion requires:

- all fourteen skill links resolve;
- all thirteen primary engineering scripts are indexed;
- example commands execute with their bundled fixtures and expected exit
  semantics;
- Markdown links, fences, and tables pass repository tests;
- the README states the Humble baseline, independent-install boundary, common
  result contract, optional-dependency semantics, and hardware limitations;
- the full repository test and maintenance checks remain green.

## Non-Goals

The README will not:

- reproduce every `SKILL.md` or reference document;
- provide production detector, SLAM, planner, force-controller, or WBC
  implementations;
- provide installation instructions for every possible robotics dependency;
- claim live MoveIt, contact, balance, or safety validation on the current
  machine;
- embed generated badges or status claims that have not been observed.
