# Inference and 2D evaluation

## Deployment parity

Freeze and compare:

- decode and color order;
- resize, crop, letterbox and interpolation;
- value range, mean/std and channel layout;
- camera rectification;
- model weights and runtime precision;
- score filtering, NMS and class mapping;
- coordinate unscaling and clipping.

Capture examples immediately before and after the model. A model regression
cannot be inferred until preprocessing and post-processing parity are known.

## Detection record

The bundled evaluator uses `[x, y, width, height]` in image pixels with positive
width/height. Every item has an image ID and class; predictions also have a
score in `[0, 1]`. State whether boxes use original, cropped or network-input
coordinates.

Predictions below the declared score threshold are excluded. Remaining
predictions are processed by descending score and matched only to an unmatched
ground truth with the same image and class. The highest IoU above the explicit
threshold wins. This deterministic rule prevents one truth from being counted
twice.

## Metrics and limitations

The tool reports TP, FP, FN, precision, recall and mean IoU of matched pairs.
It is a small admission evaluator, not COCO mAP, mask IoU, tracking MOTA/HOTA,
calibration error, or safety performance. Use the authoritative benchmark
implementation for publication claims.

When there are no predicted positives, precision is reported as zero. When
there are no ground truths, recall is zero. Always preserve the raw record and
thresholds so this convention remains reviewable.

## Dataset integrity

Keep training, tuning/validation and held-out test identities explicit. Avoid
near-duplicate frames from the same trajectory crossing splits. Report class,
scene, lighting, distance and occlusion coverage. A high aggregate metric can
hide failure on a safety-relevant subgroup.

## Runtime profiling

Define the boundary and clock. Separate queue wait, host preprocessing, device
transfer, inference, post-processing and publication. Synchronize asynchronous
accelerators before measuring completion. Report warmup, batch, precision,
hardware, sample distribution and tail latency—not only an average FPS.
