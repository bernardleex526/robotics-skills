---
name: robotics-research-discovery
description: Search current robotics papers and open-source implementations before architecture selection or substantial new algorithm work; compare reuse evidence, licenses and deployment fit. Not routine edits or unrelated research.
license: LICENSE.txt
---

# 论文与开源复用检索

## 使用边界

仅处理明确的机器人相关任务。只读取当前问题需要的参考文件；不因普通“导航、地图、跟随、标定”等词触发。路径相对本技能目录，执行脚本时使用已解析的绝对路径，不假定当前工作目录。

## 工作流

1. 将任务转为能力与约束：传感器、平台、许可证、实时性、评测数据、需替代的模块；不要上传私有代码、bag 或现场信息。
2. 原生浏览器/搜索可用时优先使用；否则运行 `scripts/search_robotics.py` 查询 arXiv 与 GitHub。无网时返回检索计划和明确的未核验状态，不把缓存当最新。
3. 同时检索近期成果与稳定基线。阅读 `references/diagnosis.md` 后打开论文、作者仓库、license、build/CI 与关键 issue，不能仅凭摘要推荐。
4. 用 `assets/reuse_decision.template.json` 记录证据，选择 reuse / adapt / implement / defer；没有找到不是不存在。
5. 输出查询、UTC 检索日期、覆盖范围、候选对照和验证实验。大规模自研前给出复用结论，不阻塞无关的小修复。

## 工程约束

区分项目事实、上游事实和待验证假设。记录版本与测量证据；示例和离线检查不构成真机安全验收。先核验现有实现再决定自研；相关检索技能未安装时直接使用可用搜索工具，禁止依赖其他技能必然存在。

## 脚本用法

```bash
python <skill-root>/scripts/search_robotics.py --query "visual language navigation" --days 365 --limit 10 --refresh
```

用户要求“最新”时重新联网（脚本使用 `--refresh`），不是仅接受 TTL 内缓存；另查不带日期窗口的成熟基线。
