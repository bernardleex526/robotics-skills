# Benchmark design

## Start with the decision

State what decision the benchmark supports. Define the system boundary: sensor
timestamp to output, callback to output, planner request to response, or full
robot trial. A number without a boundary is not comparable.

## Population and scenario

Describe the dataset, maps, scenes, object sets, robot state, payload, contact
condition and exclusions. Keep training/tuning data separate from the held-out
evaluation population. For hardware trials, predeclare safety aborts and count
them as outcomes.

## Command contract

The manifest command is a YAML list:

```yaml
command: [python3, evaluate.py, --config, config.yaml]
```

It is passed directly to `subprocess.run(..., shell=False)`. Do not use a shell
pipeline, redirection, command substitution, or a scalar string. Put required
logic in a reviewed executable and call it by argv.

Declare a bounded timeout, repeats, warmups, working directory, fresh output
directory, and seed policy. The runner substitutes `{seed}` only inside
individual argv elements. It does not interpolate environment variables.

## Metric contract

Each metric declares:

- unique name and extraction field;
- unit;
- direction: `higher_is_better`, `lower_is_better`, `target`, or
  `informational`;
- requested percentiles;
- optional threshold whose meaning matches the direction.

For latency, state the clock, synchronization, warmup, batch size, sample
population and whether transport/pre/post-processing are included. Average
frequency is not worst-case execution time.

## Robotics-specific examples

- Perception: accuracy and latency must use the same image/cloud contract and
  preprocessing as deployment.
- Planning: retain planning failures and distinguish planning time from scene
  update and trajectory execution.
- Manipulation: define grasp attempts, replans, controller aborts and recovery.
- Force/WBC: offline log metrics are not authorization to command hardware.
- Navigation: define localization resets, safety stops, collisions, timeouts
  and path validity.

## Evidence

Preserve the validated manifest, one record per run, stdout/stderr, return code,
duration, seed and extracted metrics. Hash externally stored artifacts. Use a
new result directory for each benchmark campaign.

## Primary upstream references

- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html)
- [MoveIt 2 Humble benchmarking](https://moveit.picknik.ai/humble/doc/examples/benchmarking/benchmarking_tutorial.html)
