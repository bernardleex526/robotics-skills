# 视觉建图与目标跟随输入

明确 RGB、depth、CameraInfo 是否来自匹配 frame 与时刻；letterbox、crop、resize 后框/关键点要正确逆变换，内参不能继续沿用原图尺度。
深度空洞、遮挡边缘和透明表面单独统计；目标深度不应直接取框中心单像素。相机运动与目标运动需使用同时间 TF 区分。
检测、跟踪和身份重识别分别评测；高检测置信度不证明目标身份。训练/权重许可和人物数据权限分别记录。

## 上游核验入口

https://docs.ros.org/en/humble/p/sensor_msgs/msg/CameraInfo.html

此补充是工程审查建议；涉及具体版本、参数或安全要求时核对目标实现与项目契约。
