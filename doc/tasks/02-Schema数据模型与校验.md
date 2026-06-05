# 模块 02：Schema / 数据模型与校验

> 定义所有 Agent 输入/输出 Pydantic 模型，YAML 序列化与校验逻辑。

## 子任务

- [x] `models.py` — BeatType / Transition / Emotion / CharacterRole 枚举
- [x] `models.py` — Character / Beat / Scene / Episode / Screenplay 核心 Pydantic 模型
- [x] `models.py` — NarrativeOutput / CharacterOutput / WorldOutput / TimelineOutput 等 Agent 输出模型
- [x] `models.py` — CriticOutput / RepairOutput / ConsistencyOutput 质检与修复模型
- [x] `validator.py` — `screenplay_to_yaml()` / `yaml_to_screenplay()` 序列化
- [x] `validator.py` — `validate_screenplay_yaml()` YAML 校验
- [ ] 修复 `_DEMO_SCREENPLAY_YAML` 与当前 Pydantic schema 的兼容性问题
- [ ] 补充完整 JSON Schema 参考（设计方案 §14 附录）对应的代码验证
