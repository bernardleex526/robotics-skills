# 时空标定与同步：工程参考

## 时钟模型
先写清 t_reference = a*t_sensor+b，确定单位与原点；b 是 offset，a 是 drift。消息到达延迟不是采集偏移。PTP/PPS 锁定状态不证明驱动已经使用正确时钟。
交叉相关只能给候选偏移：周期运动、插值和未知轴向会造成歧义。保留偏移符号、有效时间段和温漂；跨设备 boot epoch 要显式映射。

## 空间与激励
统一 T_target_source 记号及右手坐标，明确相机 optical frame；四元数顺序与旋转作用方式一并记录。相机内参随焦距、对焦、resize/crop 变化核验。
激光-相机需要有效几何/视场重叠和可靠对应。IMU-相机估计依赖运动激励、IMU noise 模型与时间模型；刚体假设被柔性安装破坏时不能靠更多样本补救。

## 验证和发布
训练重投影/点面残差、未参与求解的目标误差、动态重影、重复采集稳定性分别报告。保存原始包 hash、求解器 commit、初值、异常值规则和输出。
外参只给一个发布者；不要同时修改 URDF、驱动和算法内部矩阵来“试到正确”。先推导组合后验证。安装变更、温度条件或驱动时间模型变化触发重新验收。

## 一手核验入口

以下是按任务选择的上游入口，不是“当前最新推荐”的保证；涉及版本/能力时重新读取并记录日期。

- https://github.com/ethz-asl/kalibr
- https://github.com/koide3/direct_visual_lidar_calibration
- https://github.com/hku-mars/LiDAR_IMU_Init
