# Statistics and regression gates

## Keep the denominator

The total count includes successes, failures and skips. Report failure and skip
rates independently. Do not compute performance only on a hand-selected
successful subset without also exposing its sample count and selection rule.

## Summaries

For numeric successful samples, the bundled aggregator reports:

- arithmetic mean;
- median;
- population standard deviation;
- nearest-rank percentiles requested by the manifest;
- numeric sample count.

These summaries do not replace raw values. Small or multimodal samples should
be inspected directly. For repeated measurements from the same scene/robot,
the samples may not be independent.

## Direction and thresholds

`higher_is_better` passes when the selected statistic is at least the
threshold. `lower_is_better` passes when it is at most the threshold.
`target` requires an explicit tolerance and is not inferred by the simple
runner. `informational` metrics cannot gate.

Choose the statistic before viewing candidate results. A mean gate can hide
tail regressions; a high percentile can be unstable with too few samples. The
nearest-rank method makes the finite-sample behavior explicit.

## Regression comparisons

Use paired scenarios and seeds when possible. Report absolute and relative
deltas with units. Separate:

- measurement noise;
- run-to-run stochastic variation;
- dataset/scenario changes;
- environment or dependency changes;
- algorithm changes.

Do not attribute a delta to the algorithm when more than one contract changed.
Store the baseline manifest and raw runs alongside the candidate.

## CI use

Keep ordinary CI deterministic and lightweight. Heavy simulators, GPUs, ROS
graphs and hardware belong in explicitly provisioned jobs. A missing optional
dependency is a visible `skip`; decide separately whether the CI policy should
treat that skip as unacceptable.

Avoid thresholds so tight that harmless scheduler noise causes flakiness.
Conversely, do not widen thresholds after a regression merely to make CI pass.
Re-establish the measurement distribution and document the decision.
