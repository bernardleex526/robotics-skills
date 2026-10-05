# 感知与任务迁移

仿真到真机不仅是动力学：RGB 渲染、曝光、rolling shutter、深度空洞、LiDAR 扫描模式、消息时序和 TF 都属于接口差异。
VLN/跟随策略不得在训练/评估中混用 GT pose、语义和真实可获得观测。记录 privileged inputs 并在部署契约中移除或替换。
随机化范围来自测量或明确假设，分开 ablation；仿真成功与离线 replay 都不能代替真机分阶段验收。

## 上游核验入口

https://github.com/facebookresearch/habitat-lab

此补充是工程审查建议；涉及具体版本、参数或安全要求时核对目标实现与项目契约。
