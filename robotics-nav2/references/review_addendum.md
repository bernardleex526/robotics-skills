# 目标跟随和语义目标接入

语义模型或 tracker 只提交经过 frame/time/可达性检查的目标，不能直接绕过 Nav2 与安全链发布无界底盘命令。动态目标需定义更新频率、抢占/取消、目标年龄与丢失处理。
核验 installed distro 的 action 接口和 BehaviorTree 节点，不能从当前 rolling 文档复制接口到 Humble。地图切换、定位跳变和旧 goal 清理需联调。
跟随距离不能只用目标直线距离验收；还要测试 footprint、障碍、目标遮挡和多次抢占后无旧命令残留。

## 上游核验入口

https://docs.nav2.org/

此补充是工程审查建议；涉及具体版本、参数或安全要求时核对目标实现与项目契约。
