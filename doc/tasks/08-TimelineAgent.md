# 模块 08：TimelineAgent（时间线组织）

> 将事件按时间线组织，Short 模式线性输出，Long 模式图结构+冲突检测。

## 子任务

- [x] `timeline.py` — AgentBase 继承，`run()` 方法实现
- [x] `timeline.py` — `validate()` 方法（events ≥ 1）
- [x] Short 模式：`{"events": [{"chapter": int, "description": str}]}`
- [x] Long 模式：`{"graph": {"nodes": [], "edges": []}, "conflicts": []}`
- [ ] 解决完整流水线中 TimelineAgent 输出未被下游使用的问题
