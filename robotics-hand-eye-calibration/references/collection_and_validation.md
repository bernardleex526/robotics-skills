# Sampling, observability and independent validation

## Pairing

Robot and camera poses must describe the same physical instant or a modeled
interpolation. Record acquisition timestamps in one clock domain and inspect
the full skew distribution. Callback receipt time is not a substitute.
Stationary dwell can reduce motion-induced pairing error but does not correct
clock offset or pose latency.

## Motion geometry

Collect rotations about at least two materially different axes and translations
spanning the working volume. Include positive/negative motion and a range of
target depths and image locations while keeping detection quality. Many images
from nearly the same pose do not improve observability.

Avoid relying only on:

- pure translation;
- rotation about one axis;
- tiny motions near detector/encoder noise;
- poses concentrated at one depth or image region;
- near-singular robot configurations.

Use conditioning/observability diagnostics from the chosen solver when
available. The bundled validator uses axis diversity and translation span as
admission gates, not a full Fisher-information analysis.

## Fit versus holdout

Reserve motion pairs that are not used to select or fit the candidate. Report
fit and holdout AX=XB translation/rotation RMSE separately. Choosing the solver
with the smallest fit residual can overfit biased/noisy pairs.

Also validate in physical task space:

- transform detected target points and compare against surveyed geometry;
- approach the same object from varied robot poses;
- check reprojection/overlay without reusing fit observations;
- repeat after remounting, payload and thermal conditions relevant to use.

## Outliers

Define detector quality and pose/skew admission before solving. Investigate
outliers rather than deleting them solely because they increase residual.
Preserve rejected sample IDs and reasons. Robust solvers do not make bad frame
semantics or time offsets correct.

## Comparing solvers

Use solver families appropriate to the motion/noise model and library
conventions. Compare on the same admitted pairs, same transform direction and
same holdout/physical tests. Report translation and rotation separately.

## Recalibration triggers

Revalidate after camera/tool remounting, lens/focus change, target replacement,
kinematic-model change, collision, structural repair, or residual/physical-check
drift. A static transform is a versioned calibration artifact, not timeless
ground truth.
