---
name: robotics-research-reproduction
description: Use when reproducing a robotics paper, auditing experiment provenance, comparing a claimed baseline, designing ablations, or deciding whether reported metrics are independently reproducible.
license: LICENSE.txt
---

# Robotics Research Reproduction

## Scope

Use this skill to turn a paper claim into an immutable, reviewable experiment
contract. It validates provenance and experiment design; it does not claim that
a paper result was reproduced merely because setup or commands succeeded.

## Workflow

1. State the exact claim, metric, dataset split, baseline, and acceptable
   deviation before running code.
2. Read `references/provenance_and_environment.md`; pin source, data, model
   artifacts, and environment.
3. Copy `assets/run_manifest.example.yaml` and replace every placeholder with
   evidence from the target work.
4. Validate it:

   ```bash
   python3 scripts/validate_reproduction_manifest.py manifest.yaml \
     --output validation.json
   ```

5. Read `references/baselines_ablations_reporting.md` before comparing a
   baseline, changing more than one variable, or writing a conclusion.
6. Run through `robotics-benchmarking` only if that skill is independently
   available. This skill has no runtime dependency on it.

## Decision Rules

| Situation | Required action |
|---|---|
| Repository uses a branch, tag alone, `main`, or `master` | Resolve and record the full commit SHA |
| Dataset bytes or split are not identified | Stop; results are not comparable |
| Baseline differs from the paper | Declare the difference before comparison |
| More than one factor changes in an ablation | Split the ablation or label it as a combined intervention |
| One seed or one successful run | Report it as a pilot, not stable evidence |
| Setup command exits zero | Record setup success only; do not infer metric reproduction |

## Output Contract

The validator emits `assets/result.schema.json`. Exit `0` means the manifest is
admissible, exit `1` means a reproducibility gate failed, and exit `2` means
the input could not be interpreted. A pass proves contract completeness, not
scientific truth, code correctness, or hardware equivalence.

## Common Mistakes

- Treating a container tag such as `latest` as immutable.
- Reusing validation/test data while tuning and then calling it held out.
- Dropping failed runs from the denominator.
- Selecting the best seed without publishing the seed policy.
- Comparing against a reimplemented baseline without a parity check.

## 按需扩展与复用边界

- 仅在明确相关的机器人任务中使用本技能；通用代码/网页/文案工作不加载机器人参考资料。
- 按当前故障读取单个参考文件，不预读整个知识库。脚本路径相对技能目录，运行时解析成绝对路径。
- 新架构、算法替换或明显重复实现前，使用可用的在线搜索核验论文及作者代码；若已安装可选的 `robotics-research-discovery`，可按需读取。小修复不强制联网。无网明确声明未核验，不能声称最新或无现成实现。
- 本模块的补充检查见 `references/review_addendum.md`，仅在涉及其中问题时读取。
