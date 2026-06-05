# 模块 14：RepairAgent（自动修复）

> 根据 CriticAgent 的违规列表自动修复剧本问题。

## 子任务

- [x] `repair.py` — AgentBase 继承，`run()` 方法实现
- [x] `repair.py` — `validate()` 方法
- [x] 修复能力：时间线冲突 → 重排事件
- [x] 修复能力：重复场景 → 合并/删除
- [x] 修复能力：角色偏离 → 用角色圣经重写对话
- [x] 修复能力：Schema 违规 → 补全缺失字段
- [x] 修复能力：缺失视觉/音效 → 从上下文推断或插入 null
- [ ] 返回结构化为 `RepairOutput` 而非原始 `{"yaml_output": response}`
