# Provenance and environment admission

## Claim first

Write one falsifiable claim before collecting artifacts. Identify the paper
table/figure, task, dataset split, metric definition and direction. Separate:

- implementation reproduction: the code path can be built and run;
- result reproduction: the declared metric agrees within a stated tolerance;
- robustness reproduction: the conclusion survives seeds, repeats and relevant
  environmental variation.

These are different evidence levels.

## Immutable source identity

Record the repository URL and the full 40-character Git commit SHA. A branch,
tag, release name, archive filename, `main`, or `master` is not sufficient
because its resolved content may change or be ambiguous. Record patches as
separate evidence and hash them.

For vendor binaries, models, calibration files and generated maps, record a
SHA-256 digest plus the authoritative source. A package version without the
resolved dependency lock is incomplete when transitive dependencies influence
the result.

## Environment inventory

Choose one of:

- immutable container image digest (`sha256:...`), with GPU driver and kernel
  recorded outside the image; or
- an explicit inventory containing OS, Python, ROS distribution, accelerator,
  driver/runtime versions and a dependency lock digest.

Do not treat an image tag as a digest. Record compiler flags, precision mode,
threading, deterministic-algorithm switches and relevant environment variables.
For ROS 2 Humble, also record the RMW implementation and QoS assumptions.

## Dataset identity

For each dataset record:

- authoritative source and license;
- exact version or snapshot;
- split name and construction procedure;
- content SHA-256 or a signed upstream checksum;
- preprocessing and filtering configuration;
- exclusions, corrupted samples and deviations.

If the entire dataset cannot be redistributed, preserve a sorted file manifest
with per-file hashes and the split membership. Never infer the split from a
directory name alone.

## Runtime evidence

Preserve the command as an argument array, configuration files, seeds, stdout,
stderr, process exit, wall-clock timestamps, hardware inventory and produced
metrics. Evidence paths should be relative to the run result directory or
explicit URIs. Avoid absolute workstation paths in portable manifests.

## Admission boundary

`scripts/validate_reproduction_manifest.py` checks whether these declarations
exist and are immutable. It cannot verify that a remote URL is truthful,
download a dataset, compare hardware, or establish that a claimed algorithm was
implemented faithfully. Those remain review and experiment obligations.

## Primary upstream reference

- [ACM Artifact Review and Badging](https://www.acm.org/publications/policies/artifact-review-badging)
