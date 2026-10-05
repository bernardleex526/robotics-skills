# 配准与退化

配准前统一单位、frame、时间、体素采样和法向估计；初始位姿和重叠率要作为实验条件保存。ICP/GICP/NDT 的低残差不证明全局正确，重复结构与低重叠可产生错误收敛。
检查 Hessian/信息矩阵的数值尺度及弱方向，而不是将一个固定 eigenvalue 门限移植到所有算法。对照独立真值或 held-out 对应关系。
下采样、地面去除和动态滤除可能删除可定位结构；每次只改变一项，记录定位与计算量两个方向的影响。

## 上游核验入口

https://www.open3d.org/docs/release/tutorial/pipelines/registration_icp.html

此补充是工程审查建议；涉及具体版本、参数或安全要求时核对目标实现与项目契约。
