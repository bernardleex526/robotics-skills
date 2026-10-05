---
name: robotics-benchmarking
description: Use when designing, executing, aggregating, or regression-gating a robotics benchmark, including latency, accuracy, success-rate, resource, planner, perception, manipulation, or controller experiments.
license: LICENSE.txt
---

# Robotics Benchmarking

## Scope

Use this skill for bounded, repeatable command execution and honest aggregation.
It does not decide whether a scientific claim, dataset, controller, or robot is
valid. Hardware motion requires a separately reviewed safety procedure.

## Workflow

1. Read `references/benchmark_design.md` and define the population, metric
   units/directions, seeds, repeats, warmups, failure handling, and threshold.
2. Copy `assets/run_manifest.example.yaml`. Keep `command` as an argv array.
3. Validate without executing:

   ```bash
   python3 scripts/validate_benchmark_manifest.py benchmark.yaml
   ```

4. Review the exact command, working directory and fresh output directory.
5. Execute only with explicit authorization:

   ```bash
   python3 scripts/run_benchmark.py benchmark.yaml --execute \
     --output-dir evidence/run-001
   ```

6. Aggregate all recorded runs:

   ```bash
   python3 scripts/aggregate_results.py evidence/run-001 \
     --output evidence/run-001/summary.json
   ```

7. Read `references/statistics_and_regression.md` before interpreting a delta
   or setting a CI gate.

## Hard Rules

- Never convert a scalar shell command into an executable command.
- Execution uses an argv array, `shell=False`, a bounded timeout and bounded
  repeats.
- Refuse nonempty output directories; do not overwrite prior evidence.
- Retain timeouts, crashes, skips and safety aborts in the denominator.
- Every gated metric has a unit and explicit direction.
- Missing optional runtime conditions are `skip`, never `pass`.

## Exit and Result Contract

Scripts emit `assets/result.schema.json`. Exit `0` is pass/warn/deliberate
skip, exit `1` is a metric or admission failure, and exit `2` is malformed
input or unsafe invocation. A dry-run skip proves only that execution was
deliberately withheld.

## Common Mistakes

- Reporting only successful trials.
- Using best-of-N when the declared statistic was mean or median.
- Mixing warmups into measured samples.
- Comparing latency with different batch, synchronization, or preprocessing.
- Treating statistical significance as engineering importance.

## 按需扩展与复用边界

- 仅在明确相关的机器人任务中使用本技能；通用代码/网页/文案工作不加载机器人参考资料。
- 按当前故障读取单个参考文件，不预读整个知识库。脚本路径相对技能目录，运行时解析成绝对路径。
- 新架构、算法替换或明显重复实现前，使用可用的在线搜索核验论文及作者代码；若已安装可选的 `robotics-research-discovery`，可按需读取。小修复不强制联网。无网明确声明未核验，不能声称最新或无现成实现。
- 本模块的补充检查见 `references/review_addendum.md`，仅在涉及其中问题时读取。
