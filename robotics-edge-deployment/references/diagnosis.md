# 端侧部署与性能：工程参考

## 性能预算
采集→传输→预处理→推理/估计→后处理→规划→命令的时间戳必须在可比较时钟域。记录排队时间与数据年龄，不只记录 GPU kernel 时间；GPU 异步调用需正确同步或事件计时。
报告 warmup、p50/p95/p99、最大观测值、失败率、峰值内存和长时间稳态；percentile 不是 WCET 保证。并发录包和可视化属于负载条件。

## 导出与量化
检查算子支持、动态 shape、batch、布局、通道顺序、归一化、插值和坐标恢复。INT8 校准数据应覆盖部署域；不能只检查模型输出维度相同。
保存模型/engine hash、构建 GPU 与 runtime 版本；engine 可移植范围按上游规定验证，不能假定跨架构通用。训练代码许可与权重许可分别检查。

## 部署边界
配置、地图、模型和软件组成一个版本集合；启动健康探测应含输入新鲜度、TF 与输出合理性。进程 alive 不代表估计有效。
实时性取决于调度、内存、锁、I/O 与优先级，不因语言或节点频率自动成立。失效时走项目审核的安全状态，远程升级不得自行绕过急停或现场权限。

## 一手核验入口

以下是按任务选择的上游入口，不是“当前最新推荐”的保证；涉及版本/能力时重新读取并记录日期。

- https://docs.nvidia.com/deeplearning/tensorrt/latest/
- https://onnxruntime.ai/docs/performance/
- https://docs.ros.org/en/rolling/Tutorials/Demos/Real-Time-Programming.html
