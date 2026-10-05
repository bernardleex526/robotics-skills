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

## 按需扩展与复用边界

- 仅在明确相关的机器人任务中使用本技能；通用代码/网页/文案工作不加载机器人参考资料。
- 按当前故障读取单个参考文件，不预读整个知识库。脚本路径相对技能目录，运行时解析成绝对路径。
- 新架构、算法替换或明显重复实现前，使用可用的在线搜索核验论文及作者代码；若已安装可选的 `robotics-research-discovery`，可按需读取。小修复不强制联网。无网明确声明未核验，不能声称最新或无现成实现。
- 本模块的补充检查见 `references/review_addendum.md`，仅在涉及其中问题时读取。
