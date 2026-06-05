# 模块 13：CriticAgent（质量评审）

> 对生成的剧本进行多维质量检查，返回违规列表和评分。

## 子任务

- [x] `critic.py` — AgentBase 继承，`run()` 方法实现
- [x] `critic.py` — `validate()` 方法
- [x] 检查项：continuity / pacing / character motivation / dialogue quality / shootability / line balance
- [x] 返回：`{"violations": [...], "score": int, "summary": str}`
- [x] 快速评审模式（`FAST_CRITIC`）
