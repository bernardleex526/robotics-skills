---
name: robotics-visual-slam
description: "Build or debug robotic monocular, stereo, RGB-D and visual-inertial SLAM: initialization, scale, tracking, loop closure and RGB mapping. Not ordinary image editing."
license: LICENSE.txt
---

# 视觉与 RGB 建图

## 使用边界

仅处理明确的机器人相关任务。只读取当前问题需要的参考文件；不因普通“导航、地图、跟随、标定”等词触发。路径相对本技能目录，执行脚本时使用已解析的绝对路径，不假定当前工作目录。

## 工作流

1. 明确单目/双目/RGB-D/VIO 模式、快门、图像是否已矫正、曝光时间与 IMU 接口。
2. 先核对 CameraInfo、像素变换、深度单位与光学坐标，再看特征/直接法/学习式跟踪。
3. 按 `references/diagnosis.md` 分离初始化、跟踪、回环和稠密重建问题。
4. 固定数据划分与算力，比较轨迹、尺度、失败恢复、内存及地图可用性。
5. 提供经过验证的输入链路；不能从漂亮渲染推导定位精度或导航安全。

## 工程约束

区分项目事实、上游事实和待验证假设。记录版本与测量证据；示例和离线检查不构成真机安全验收。先核验现有实现再决定自研；相关检索技能未安装时直接使用可用搜索工具，禁止依赖其他技能必然存在。
