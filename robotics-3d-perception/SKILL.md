---
name: robotics-3d-perception
description: Use when building or debugging ROS 2 PointCloud2 pipelines, LiDAR or depth-cloud field layouts, deskew and TF contracts, filtering and registration, 3D object outputs, or deterministic 3D evaluation.
license: LICENSE.txt
---

# Robotics 3D Perception

## Scope

Use this skill to validate byte-level point cloud admission and bounded 3D
result matching before tuning an algorithm. It does not claim registration,
segmentation, detection, localization, or hardware readiness from schema alone.

## Route by Task

| Task or symptom | Read / run |
|---|---|
| PointCloud2 corruption, NaNs, field or endian concern | `references/pointcloud2_contract.md` and `scripts/check_pointcloud_contract.py` |
| Motion distortion, TF, filtering, registration or clustering | `references/three_d_pipeline.md` |
| Evaluate framed 3D objects | `references/three_d_pipeline.md` and `scripts/evaluate_3d_results.py` |

## Workflow

1. Capture the actual fields, offsets, datatypes, counts, endian flag,
   dimensions, `point_step`, `row_step`, payload, frame and acquisition stamp.
2. Declare algorithm-required per-point time and ring fields; never infer their
   name or unit.
3. Run the offline byte-layout check:

   ```bash
   python3 scripts/check_pointcloud_contract.py cloud.json
   ```

4. Fix layout, timestamp and frame failures before filtering or model tuning.
5. Freeze class, score, center-distance, size and yaw gates, then run:

   ```bash
   python3 scripts/evaluate_3d_results.py objects.json
   ```

6. Inspect raw evidence and limitations. Follow with live TF, clock, loss,
   deskew, latency and representative-scene validation.

## Hard Gates

- Organized-row padding is handled through `row_step`; payload length must
  equal `row_step * height`.
- Every field stays within `point_step`; count and datatype are explicit.
- Endianness controls byte decoding.
- XYZ values are decoded and their finite ratio is reported.
- Algorithm-required time/ring fields are present with separately reviewed
  units and semantics.
- 3D object frames match; thresholds are explicit.

## Metric Boundary

The bundled matcher uses center distance, relative size error and wrapped yaw
error. It deliberately does **not** call this oriented 3D IoU. Use the
authoritative dataset evaluator for publication metrics.

## 按需扩展与复用边界

- 仅在明确相关的机器人任务中使用本技能；通用代码/网页/文案工作不加载机器人参考资料。
- 按当前故障读取单个参考文件，不预读整个知识库。脚本路径相对技能目录，运行时解析成绝对路径。
- 新架构、算法替换或明显重复实现前，使用可用的在线搜索核验论文及作者代码；若已安装可选的 `robotics-research-discovery`，可按需读取。小修复不强制联网。无网明确声明未核验，不能声称最新或无现成实现。
- 本模块的补充检查见 `references/review_addendum.md`，仅在涉及其中问题时读取。
