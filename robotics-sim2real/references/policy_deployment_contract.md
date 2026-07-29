# 策略部署契约

这份契约是 checkpoint 与真机 adapter 之间的可执行接口。训练、离线回放、HIL 和真机必须读取
同一份版本化制品；字段缺失、顺序不同或 hash 不匹配时拒绝使能执行器。

从 `assets/policy_deployment_contract.yaml` 复制模板，与 checkpoint、normalization statistics、
训练配置和 golden vectors 一起归档。

## 必填内容

| 类别 | 必须冻结的字段 |
|---|---|
| 制品身份 | policy ID、模型格式/opset、checkpoint 与文件 `sha256`、导出器和 runtime 版本 |
| observation | **有序**名称、shape、dtype、单位、frame、scale/offset/clip、缺失/NaN 策略 |
| action | **有序**名称、shape、dtype、单位、frame、scale/offset/clip、驱动接口与 hold 语义 |
| normalization | mean/std 或其他统计量的版本/hash、epsilon、应用顺序；训练/部署只保留一个 owner |
| 时序 | 传感器采样率、policy/control 频率、decimation、history stack 顺序、时间戳与最大 age |
| recurrent | state 名称/shape/初值，以及 episode、故障、接管、失联和 mode switch 的 reset 条件 |
| reset | episode 起点分布、adapter buffer/history/action 的清理顺序，以及旧命令不可恢复的约束 |
| 权限边界 | actor 可用输入白名单；critic/teacher 的 privileged observation 必须列入排除清单 |

## 门禁流程

1. **导出时生成**：训练代码从实际 observation/action manager 和 wrapper 生成契约，不手抄顺序。
2. **加载时校验**：adapter 校验 schema version、shape/dtype、全部 hash、runtime compatibility 和
   safety envelope；不允许“缺字段就用默认值”。
3. **golden-vector 测试**：保存覆盖边界值、history warm-up、NaN/缺失、clip 和 recurrent reset 的
   输入/中间张量/输出；训练端与部署端逐项比较，并定义浮点容差。
4. **shadow/HIL**：用真机录包检查 observation age、normalization 后分布、action saturation、
   inference WCET/deadline miss 和 reset 事件；输出不接执行器。
5. **使能与回滚**：只有契约、模型和 normalization hash 全部匹配才允许进入受控执行器阶段。
   回滚必须恢复完整制品集合，不能只替换模型文件。

契约证明接口一致性，不证明策略安全或任务正确；安全监控、工作包络和独立停机链路仍按
`references/deployment_checklist.md` 验证。
