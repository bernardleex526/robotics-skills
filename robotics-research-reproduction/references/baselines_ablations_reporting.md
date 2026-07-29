# Baselines, ablations and reporting

## Baseline parity

Before interpreting a delta, compare the candidate and baseline contracts:

- identical dataset bytes and split;
- identical evaluation implementation and post-processing;
- comparable input modalities, training budget and pretrained data;
- identical metric units, direction and aggregation;
- equivalent hardware/resource constraints when latency or throughput matters.

If the original baseline cannot run, label a reimplementation clearly and
report a parity experiment against at least one published checkpoint or
reference output. A weaker baseline cannot support a superiority claim.

## Seeds and repeats

Declare seeds before execution. Use the same seed set for paired comparisons
when appropriate. Distinguish algorithmic randomness from nondeterministic GPU,
middleware, simulator or sensor behavior. A repeat policy states:

- number of independent runs;
- failed-run handling;
- stopping rule;
- warmup policy;
- summary statistic and uncertainty interval.

Never omit failed runs from the denominator. If a run is excluded because of
infrastructure failure, retain it with the exclusion rule and evidence.

## Ablation design

An isolated ablation changes exactly one declared experimental variable while
holding the baseline contract fixed. Examples include one loss term, one sensor
modality, or one planner component. Changing optimizer, compute budget and
architecture together is a combined intervention, not an isolated ablation.

Predeclare the question, changed variable, expected direction, seeds and
analysis. Do not choose an ablation after viewing the test set and present it as
confirmatory evidence.

## Metric integrity

Every metric needs:

- definition and implementation/version;
- unit;
- `higher_is_better`, `lower_is_better`, `target`, or `informational`;
- aggregation population and treatment of missing/failed runs;
- threshold or equivalence margin when used for a gate.

For time metrics, state clock, warmup, synchronization, batch size and included
pre/post-processing. For navigation, manipulation or legged trials, state
whether resets and safety aborts count as failures.

## Reporting checklist

Report all declared runs, not only the best seed. Include raw per-run values,
central tendency, dispersion/interval, failure rate, deviations, source/data
hashes, environment identity and the exact evaluation command. Separate facts
from interpretation and distinguish:

- reproduced within the predeclared tolerance;
- directionally consistent but outside tolerance;
- inconclusive due to variance or contract mismatch;
- not reproduced.

A statistically significant delta can still be operationally irrelevant.
Conversely, small sample counts can make an important effect inconclusive.
