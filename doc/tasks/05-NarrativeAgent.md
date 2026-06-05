# 模块 05：NarrativeAgent（叙事提取）

> 抽取小说中的主要事件、子情节、转折点和主题。

## 子任务

- [x] `narrative.py` — AgentBase 继承，`run()` 方法实现
- [x] `narrative.py` — `validate()` 方法（major_events ≥ 1）
- [x] `narrative.py` — 默认重试机制（max_attempts=2）
- [x] 输入：`{"chunks": list[str]}`
- [x] 输出：`{"major_events": [...], "subplots": [...], "turning_points": [...], "theme": str}`
