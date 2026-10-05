# 地图表示与长期管理：工程参考

## 表示选择
占据栅格用于平面规划，TSDF 偏表面重建，ESDF 面向距离查询，稀疏特征/pose graph 面向特定定位后端。NeRF/3DGS 的渲染质量不是自由空间或碰撞几何保证；使用时另建可验证几何通路。
RGB 语义标签保存类别版本、置信度、来源帧和位姿不确定性。开放词汇检索命中不等于目标可达。

## 自由空间与动态场景
未观测不等于 free。记录射线清除、量程截断、遮挡、地面/坡面分类、悬空障碍及机器人高度。2D 投影前说明高度带和 footprint，不能将彩色点云直接当 costmap。
动态目标去除需要区分暂时遮挡与永久变化；更新策略在多会话数据上验证。

## 生命周期
产物清单包含 map_id、父版本、frame、resolution/voxel、sensor calibration hash、算法 commit、时间范围、存储格式/版本、许可和校验和。不要覆盖唯一的已验收地图。
地图切换测试 TF 发布权、旧 goal 清理、初始位姿、定位健康和回滚。地图文件成功打开不等于重定位成功。

## 一手核验入口

以下是按任务选择的上游入口，不是“当前最新推荐”的保证；涉及版本/能力时重新读取并记录日期。

- https://github.com/introlab/rtabmap
- https://github.com/nvidia-isaac/nvblox
- https://docs.nav2.org/configuration/packages/configuring-map-server.html
