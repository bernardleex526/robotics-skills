# 数据采集与回放：工程参考

## 录包契约
记录 topic type、QoS、消息数量、clock domain、header stamp 与 receipt time、driver commit、标定 hash。核对瞬态静态 TF 与低频配置是否真正录入；订阅者观察到的频率不能证明驱动无丢失。
rosbag2 storage 和压缩选项依发行版确认，先在目标机器验证录制和读取。记录磁盘吞吐、CPU 与掉帧，禁止将 record 成功退出作为数据完整性证明。

## 时间审计工具
CSV 必含 topic,stamp，可选 received；单位秒，stamp 与 received 只有同一已对齐时钟才计算年龄。每行是同一 topic 的接收顺序，不要先排序抹掉乱序。
工具报告每话题重复/回退/间隔与可选年龄；--max-gap-s 是用户显式设定的门限，不内置所谓适用于所有传感器的频率。它不读取 bag、检测 TF 或证明物理同步，需从可信导出器生成 CSV。

## 回放与数据治理
use_sim_time、/clock、seek/reset 与 estimator buffer 一起检查。TF 缓存、启动顺序、DDS QoS、回放倍率会改变行为；原速度不等于完全确定性。
同一路线/建筑相邻帧不能随机拆分后宣称泛化。raw 与 derived 分目录，用 hash 记录转换版本、筛除原因和输出。人员图像、定位轨迹和现场布局默认不上传检索服务。

## 一手核验入口

以下是按任务选择的上游入口，不是“当前最新推荐”的保证；涉及版本/能力时重新读取并记录日期。

- https://github.com/ros2/rosbag2
- https://mcap.dev/spec

## 退出码与边界

退出 0 为已声明离线检查通过（status=pass），1 为检测到违反契约（fail），2 为无效输入或读取错误（invalid，输出 stderr）。单样本/短片段不能证明长期或实机行为；输入记录真实性由采集流程保证。
