# 模块 15：ConsistencyAgent（双向一致性）

> 将原始小说与人编辑后的 YAML 剧本进行对比，生成一致性报告。（可选）

## 子任务

- [x] `consistency.py` — AgentBase 继承，`run()` 方法实现
- [x] `consistency.py` — `validate()` 方法
- [x] 输入：`original_novel_chunks` + `human_edited_yaml`
- [x] 输出：`{"alignment_score": float, "deviations": [...], "suggestions": [...]}`
