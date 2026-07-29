---
name: robotics-vision-perception
description: Use when building or debugging ROS 2 camera pipelines, Image and CameraInfo contracts, synchronization, optical frames, 2D detection evaluation, inference preprocessing, or vision deployment regressions.
license: LICENSE.txt
---

# Robotics Vision Perception

## Scope

Use this skill to admit camera data and evaluate deterministic 2D detections
before blaming a model. It covers engineering contracts around an algorithm,
not model training code or a universal accuracy target.

## Route by Symptom

| Symptom or task | Read / run |
|---|---|
| Corrupt image, color mismatch, calibration or timestamp concern | `references/camera_pipeline.md` and `scripts/check_camera_contract.py` |
| Accuracy changed after deployment | `references/inference_and_evaluation.md` |
| Need TP/FP/FN, precision, recall or matched IoU | `scripts/evaluate_vision_results.py` |
| Live ROS graph/QoS/TF diagnosis | Inspect live evidence, then use this skill's offline snapshot format |

## Workflow

1. Record the real topic types, acquisition timestamps, frames, QoS, encoding,
   dimensions, `step`, payload length and paired CameraInfo.
2. Convert a bounded sample to the format in
   `assets/fixtures/camera_valid.json`.
3. Run:

   ```bash
   python3 scripts/check_camera_contract.py camera.json --output result.json
   ```

4. Fix data-contract failures before model tuning.
5. Freeze preprocessing, score and IoU thresholds, then evaluate:

   ```bash
   python3 scripts/evaluate_vision_results.py detections.json
   ```

6. Compare raw records and limitations; a passing fixture does not prove live
   QoS, transport latency, calibration quality, generalization, or safety.

## Hard Gates

- Frames and timestamps describe acquisition, not merely callback receipt.
- `step * height` equals payload length; padding is allowed only through
  `step`.
- Image and CameraInfo dimensions/frames agree.
- Calibration matrices are finite and the distortion model is declared.
- Pairing skew is checked against an explicit application threshold.
- Evaluation thresholds and box convention are fixed before comparison.

## Output Contract

Both scripts emit `assets/result.schema.json`. Exit `0` is pass/warn, exit `1`
is a domain gate failure, and exit `2` is unreadable or malformed input.
